"""Position manager: break-even + trailing-stop engine for signal-relay trades.

Run standalone:  C:/Users/voidk/miniconda3/python.exe manage.py

Every interval it scans open positions opened by the relay (magic 20261014):
  - BREAK-EVEN: once price has moved +be_at_r * R in favor (R = entry->original SL
    distance), moves SL to entry +/- a small buffer. Never widens a stop.
  - TRAIL: once price is beyond +trail_from_r * R, trails the SL at
    trail_dist_r * R behind price, stepping only in the favorable direction.

Original SL (R basis) is preserved in manage-state.json per ticket, so moving
the stop never corrupts the math. HALT pauses new trades in executor.py but
this manager KEEPS RUNNING (protecting open trades is always allowed).
The STOP file next to daemon.py stops this manager too.
"""
import json
import os
import sqlite3
import sys
import time

import MetaTrader5 as mt5
from broker_lifecycle import initialize_existing
from datetime import datetime, timezone

from event_bus import bus
from loss_halt import LossHalt, SafetyError
from stop_legality import plan_position_stop, confirm_stop_change
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from manager_connection import ensure_demo_connection

# Authorization: this deployment is restricted to demo account 5057394166 only.
# A terminal account switch must never silently adopt trades on another account.
EXPECTED_DEMO_LOGIN = 5057394166

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.json")
STATE = os.path.join(BASE, "manage-state.json")
DB = os.path.join(BASE, "signals.db")
LOSS_HALT_PATH = os.path.join(BASE, "loss_state.sqlite3")
STOP_FILE = os.path.join(BASE, "STOP")
MAGIC = 20261014
ALGO_MAGIC = 20261015  # strategy.py trades - managed identically
LOCK_FILE = os.path.join(BASE, "manage.lock")


# ---- single-instance lock ---------------------------------------------------
def _pid_is_live_python(pid, script_marker=None):
    """True when `pid` names a running process whose executable is python(.exe)."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    if os.name != "nt":
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.OpenProcess.restype = ctypes.c_void_p
        k32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
        k32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        k32.QueryFullProcessImageNameW.argtypes = [ctypes.c_void_p, ctypes.c_uint32,
                                                   ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_uint32)]
        k32.CloseHandle.argtypes = [ctypes.c_void_p]
        h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        try:
            code = ctypes.c_ulong()
            if not k32.GetExitCodeProcess(h, ctypes.byref(code)) or code.value != 259:
                return False  # 259 = STILL_ACTIVE
            buf = ctypes.create_unicode_buffer(1024)
            n = ctypes.c_ulong(1024)
            if not k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(n)):
                return True  # alive; image name unavailable
            if "python" not in os.path.basename(buf.value).lower():
                return False
            if script_marker:
                import subprocess as _sp
                try:
                    cl = _sp.run(["powershell", "-NoProfile", "-Command",
                                  f"(Get-CimInstance Win32_Process -Filter \"ProcessId={int(pid)}\").CommandLine"],
                                 capture_output=True, text=True, timeout=30).stdout.strip()
                    return bool(cl) and script_marker in cl
                except Exception:  # noqa: BLE001
                    return True
            return True
        finally:
            k32.CloseHandle(h)
    except Exception:  # noqa: BLE001
        return False


def _acquire_single_instance():
    """Refuse to run alongside another live python holding LOCK_FILE: print a
    note and sys.exit(0). A stale lock (dead/non-python PID) is overwritten."""
    old = ""
    try:
        with open(LOCK_FILE, "r", encoding="utf-8") as f:
            old = (f.read() or "").strip()
    except OSError:
        pass
    if old and _pid_is_live_python(old, os.path.basename(__file__)):
        print(f"manage.py: another instance is already running (pid {old}) - exiting")
        sys.exit(0)
    try:
        with open(LOCK_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except OSError as e:  # noqa: BLE001
        print("manage.py: could not write lock file:", e)


def _release_lock():
    try:
        os.remove(LOCK_FILE)
    except OSError:
        pass


def _load(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


def _save(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)


def _trace_for_ticket(ticket) -> str:
    """End-to-end chain id for a position ticket: the msg_id of the execution
    row in signals.db, so position_closed links back to its signal. Falls back
    to a deterministic ticket id when no ledger row exists (algo engines)."""
    try:
        con = sqlite3.connect(DB, timeout=10)
        try:
            row = con.execute(
                "SELECT msg_id FROM trades WHERE ticket=? "
                "ORDER BY id DESC LIMIT 1", (int(ticket),)).fetchone()
        finally:
            con.close()
        if row and row[0]:
            return str(row[0])
    except Exception:  # noqa: BLE001
        pass
    return f"pos:{ticket}"


def _stop_on_grid(price, info, is_buy):
    """Choose an explicit valid grid price, away from the current market.

    Planning remains strict: it never silently rounds a submitted stop.
    Decimal avoids binary-float artifacts; a tighter concurrent broker stop
    is still rejected by the subsequent position-bound preflight.
    """
    grid = Decimal(str(getattr(info, "trade_tick_size", 0) or info.point))
    price = Decimal(str(price))
    if not grid.is_finite() or not price.is_finite() or grid <= 0:
        raise ValueError("invalid stop price/grid")
    mode = ROUND_FLOOR if is_buy else ROUND_CEILING
    return float((price / grid).to_integral_value(rounding=mode) * grid)


def _modify_sltp(position, new_sl, keep_tp, *, broker_utc_offset_s=0,
                 allow_stale_for_protection=False):
    is_buy = position.type == mt5.POSITION_TYPE_BUY
    side = "BUY" if is_buy else "SELL"
    # Stop-legality preflight: validate tick freshness, grid alignment, and
    # distance from market before touching the broker. Fail closed on any
    # rejection so an illegal stop is never submitted.
    try:
        sd = plan_position_stop(
            mt5, position.ticket, float(new_sl),
            now=datetime.now(timezone.utc),
            broker_utc_offset_s=broker_utc_offset_s,
            allow_stale_for_protection=allow_stale_for_protection,
        )
        if sd.symbol != position.symbol or sd.side != side:
            return False, "broker position identity changed or unavailable"
        if not sd.allowed:
            return False, f"stop legality rejected: {sd.reason}"
        if sd.requires_widen_opt_in:
            return False, f"stop legality: WIDEN requires opt-in ({sd.reason})"
    except Exception as e:  # noqa: BLE001 - fail closed on guard error
        return False, f"stop guard unavailable: {type(e).__name__}: {e}"
    req = {"action": mt5.TRADE_ACTION_SLTP, "symbol": position.symbol,
           "position": position.ticket, "sl": new_sl, "tp": keep_tp}
    res = mt5.order_send(req)
    if not res or res.retcode != mt5.TRADE_RETCODE_DONE:
        return False, (res.comment if res else "no result")
    # An acknowledgement is not proof that the broker retained protection.
    # Record BE/trail success only after exact ticket/side/symbol/SL readback.
    return confirm_stop_change(mt5, sd)


def send_partial_close(position, volume, comment, digits, deviation):
    """Close part of a position with an opposite deal tagged to the position ticket.

    Returns (ok, detail_string).
    """
    is_buy = position.type == mt5.POSITION_TYPE_BUY
    close_type = mt5.ORDER_TYPE_SELL if is_buy else mt5.ORDER_TYPE_BUY
    tick = mt5.symbol_info_tick(position.symbol)
    if tick is None:
        return False, "no tick"
    price_val = tick.ask if close_type == mt5.ORDER_TYPE_BUY else tick.bid

    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": round(volume, digits),
        "type": close_type,
        "position": position.ticket,
        "price": float(price_val),
        "deviation": deviation,
        "magic": MAGIC,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
    }
    res = mt5.order_send(req)
    if not res or res.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_PLACED):
        return False, f"partial close failed: {getattr(res, 'retcode', None)} {getattr(res, 'comment', '')}"
    return True, f"partial close {volume} @ {price_val}"


_loss_halt_singleton = None

def _loss_halt_instance(cfg):
    global _loss_halt_singleton
    if _loss_halt_singleton is None:
        limit = float((cfg.get("risk") or {}).get("daily_loss_limit", 0))
        if limit > 0:
            try:
                _loss_halt_singleton = LossHalt(LOSS_HALT_PATH, mt5, limit)
            except (ValueError, SafetyError):
                pass  # loss halt not configured or unavailable
    return _loss_halt_singleton

def manage_once(cfg):
    """One management pass. Returns list of action strings for logging/notify."""
    actions = []
    m = (cfg.get("manage") or {})
    # Ensure broker_utc_offset_s defaults to 0 when missing from config
    if m.get("broker_utc_offset_s") is None:
        m["broker_utc_offset_s"] = 0
    # Ensure adopt_tickets defaults to [] when missing from config
    if m.get("adopt_tickets") is None:
        m["adopt_tickets"] = []
    # Daily loss latch: observe broker history before any stop modification.
    # Observing keeps P&L state current; we never block stop modifications
    # here because protecting open trades is always allowed (manage.py docstring).
    try:
        lh = _loss_halt_instance(cfg)
        if lh is not None:
            lh.observe(datetime.now(timezone.utc))
    except SafetyError:
        pass  # broker history unavailable; continue managing open trades
    be_at_r = float(m.get("be_at_r", 1.0))
    trail_from_r = float(m.get("trail_from_r", 1.5))
    trail_dist_r = float(m.get("trail_dist_r", 0.5))
    be_buffer_pts = int(m.get("be_buffer_points", 10))
    # --- NEW: profit securing ---
    secure_at_r = float(m.get("secure_at_r", 2.0))
    secure_lock_at_r = float(m.get("secure_lock_at_r", 1.0))
    # --- NEW: TP partial close levels ---
    tp_levels = m.get("tp_levels", [])
    state = _load(STATE, {})
    positions = mt5.positions_get()
    if positions is None:
        # API error (terminal disconnected / IPC failure) is NOT an empty
        # account - `or []` used to conflate the two and prune per-ticket
        # state (original SL / R basis) for positions that were still open.
        # Skip the entire cycle and touch nothing: no state pruning, no SL
        # modifies, no state save.
        bus.publish({"type": "alert", "source": "manage",
                     "payload": {"kind": "positions_get_error",
                                 "detail": "positions_get() returned None (API error) - cycle skipped"},
                     "trace_id": None})
        print("manage_once: positions_get() returned None (API error) - cycle skipped, state untouched")
        return ["SKIP positions_get()=None (API error) - cycle skipped, state untouched"]
    live = {p.ticket for p in positions}
    # forget closed tickets (only when the snapshot is a confirmed list)
    for t in [k for k in state if int(k) not in live]:
        rec = state.pop(t, None)
        bus.publish({"type": "position_closed", "source": "manage",
                     "payload": {"ticket": int(t), "state": rec or {}},
                     "trace_id": _trace_for_ticket(t)})
    for p in positions:
        # adopt_tickets (config manage.adopt_tickets): manual/other tickets the
        # owner moved under system management - same BE/trail discipline.
        adopt = {int(t) for t in m.get("adopt_tickets", [])}
        if p.magic not in (MAGIC, ALGO_MAGIC) and p.ticket not in adopt:
            continue
        rec = state.get(str(p.ticket))
        if rec is None:
            rec = state[str(p.ticket)] = {"entry": p.price_open, "orig_sl": p.sl,
                                          "be_done": False, "secured_at": None,
                                          "tp_hits": [], "r": None}
            if p.sl and p.sl > 0:
                rec["r"] = abs(p.price_open - p.sl)
            _save(STATE, state)
        r = rec.get("r")
        if not r:
            # Position has no protective stop (sl=0 or no orig SL recorded).
            # Apply a default protective stop per user policy: never unprotected.
            default_dist = float(m.get("default_sl_distance", 30.0))
            is_buy = p.type == mt5.POSITION_TYPE_BUY
            new_sl = (rec["entry"] - default_dist) if is_buy else (rec["entry"] + default_dist)
            ok, why = _modify_sltp(p, new_sl, p.tp, broker_utc_offset_s=m.get("broker_utc_offset_s", 0),
                                   allow_stale_for_protection=True)
            if ok:
                r = abs(rec["entry"] - new_sl)
                rec["r"] = r
                rec["orig_sl"] = new_sl
                info = mt5.symbol_info(p.symbol)
                digits = info.digits if info else 5
                actions.append(f"PROTECT {p.symbol} #{p.ticket}: SL set at {new_sl:.{digits}f} ({default_dist} units)")
            else:
                actions.append(f"PROTECT {p.symbol} #{p.ticket} FAILED: {why}")
                continue
        is_buy = p.type == mt5.POSITION_TYPE_BUY
        tick = mt5.symbol_info_tick(p.symbol)
        if tick is None:
            continue
        price = tick.bid if is_buy else tick.ask
        moved = (price - rec["entry"]) if is_buy else (rec["entry"] - price)
        bus.publish({"type": "pnl_update", "source": "manage",
                     "payload": {"ticket": p.ticket, "symbol": p.symbol,
                                 "side": "BUY" if is_buy else "SELL",
                                 "pl": round(p.profit + p.swap, 2),
                                 "r_multiple": round(moved / r, 2) if r else None,
                                 "r_multiple_basis": "directional price movement / original price risk; excludes costs",
                                 "sl": p.sl, "tp": p.tp},
                     "trace_id": _trace_for_ticket(p.ticket)})
        info = mt5.symbol_info(p.symbol)
        if info is None:
            continue
        buf = be_buffer_pts * info.point
        # 1) break-even
        if not rec["be_done"] and moved >= be_at_r * r:
            new_sl = _stop_on_grid(rec["entry"] + buf if is_buy else rec["entry"] - buf, info, is_buy)
            if (is_buy and new_sl > p.sl) or ((not is_buy) and (new_sl < p.sl or p.sl == 0)):
                ok, why = _modify_sltp(p, new_sl, p.tp, broker_utc_offset_s=m.get("broker_utc_offset_s", 0),
                                   allow_stale_for_protection=True)
                if ok:
                    rec["be_done"] = True
                    actions.append(f"BE  {p.symbol} #{p.ticket}: SL -> {new_sl}")
                else:
                    actions.append(f"BE  {p.symbol} #{p.ticket} FAILED: {why}")
                    bus.publish({"type": "alert", "source": "manage",
                                 "payload": {"ticket": p.ticket, "symbol": p.symbol,
                                             "kind": "breakeven_failed", "why": why},
                                 "trace_id": _trace_for_ticket(p.ticket)})
        # 2) PROFIT SECURING: lock profit beyond break-even
        if rec.get("secured_at") is None and moved >= secure_at_r * r:
            risk = r
            lock_distance = secure_lock_at_r * risk
            new_sl = (rec["entry"] + lock_distance) if is_buy else (rec["entry"] - lock_distance)
            # Only apply if it actually tightens the stop (never widen)
            if (is_buy and new_sl > p.sl) or ((not is_buy) and (new_sl < p.sl or p.sl == 0)):
                ok, why = _modify_sltp(p, new_sl, p.tp, broker_utc_offset_s=m.get("broker_utc_offset_s", 0),
                                   allow_stale_for_protection=True)
                if ok:
                    rec["secured_at"] = secure_at_r
                    rec["secured_sl"] = new_sl
                    actions.append(f"SEC {p.symbol} #{p.ticket}: SL locked at +{secure_lock_at_r}R (moved={moved/r:.2f}R)")
                else:
                    actions.append(f"SEC {p.symbol} #{p.ticket} FAILED: {why}")
                    bus.publish({"type": "alert", "source": "manage",
                                 "payload": {"ticket": p.ticket, "symbol": p.symbol,
                                             "kind": "profit_secure_failed", "why": why},
                                 "trace_id": _trace_for_ticket(p.ticket)})
        # 3) TP PARTIAL CLOSES
        current_volume = float(p.volume)
        min_vol = float(getattr(info, "volume_min", 0.01))
        for level in tp_levels:
            level_id = level.get("id", f"tp{level.get('r', 0)}")
            if level_id in rec.get("tp_hits", []):
                continue
            level_r = float(level.get("r", 0))
            close_pct = float(level.get("close_pct", 0))
            if close_pct <= 0 or moved < level_r * r:
                continue
            close_volume = current_volume * (close_pct / 100.0)
            if close_volume < min_vol:
                continue
            deviation = int(m.get("slippage_points", 10))
            ok, detail = send_partial_close(p, close_volume,
                                            f"TP partial {close_pct}% at {level_r}R",
                                            int(getattr(info, "digits", 5)), deviation)
            if ok:
                rec.setdefault("tp_hits", []).append(level_id)
                actions.append(f"TP{level_id} {p.symbol} #{p.ticket}: closed {close_pct}% at {level_r}R ({detail})")
                bus.publish({"type": "position_managed", "source": "manage",
                             "payload": {"ticket": p.ticket, "symbol": p.symbol,
                                         "action": f"TP{level_id}",
                                         "close_pct": close_pct,
                                         "r_multiple": round(moved / r, 2)},
                             "trace_id": _trace_for_ticket(p.ticket)}),
                # After a partial close, the position volume shrinks; re-read
                # so subsequent levels in this cycle use the updated volume.
                p = mt5.positions_get(ticket=p.ticket)
                if p is None or len(p) == 0:
                    break  # position fully closed
                p = p[0]
                current_volume = float(p.volume)
            else:
                actions.append(f"TP{level_id} {p.symbol} #{p.ticket} FAILED: {detail}")
        # 4) trail
        if moved >= trail_from_r * r:
            cand = _stop_on_grid(price - trail_dist_r * r if is_buy else price + trail_dist_r * r, info, is_buy)
            if (is_buy and cand > p.sl) or ((not is_buy) and (cand < p.sl or p.sl == 0)):
                ok, why = _modify_sltp(p, cand, p.tp, broker_utc_offset_s=m.get("broker_utc_offset_s", 0),
                                   allow_stale_for_protection=True)
                if ok:
                    actions.append(f"TRL {p.symbol} #{p.ticket}: SL -> {cand:.{info.digits}f}")
    _save(STATE, state)
    return actions


def position_summary() -> str:
    """Human-readable one-line per position for logs / dashboard."""
    positions = mt5.positions_get()
    if positions is None:
        return "MT5 not attached"
    if not positions:
        return "No managed positions"
    lines = []
    state = _load(STATE, {})
    for p in positions:
        ticket = int(p.ticket)
        side = "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL"
        entry = float(p.price_open)
        sl = float(p.sl)
        tp = float(p.tp)
        profit = float(p.profit)
        rec = state.get(str(ticket), {})
        r = rec.get("r")
        r_mult = None
        if r:
            info = mt5.symbol_info(p.symbol)
            tick = mt5.symbol_info_tick(p.symbol)
            if info and tick:
                price = tick.bid if side == "BUY" else tick.ask
                moved = (price - entry) if side == "BUY" else (entry - price)
                r_mult = round(moved / r, 2)
        lines.append(f"#{ticket} {side} {p.symbol} vol={p.volume} entry={entry} SL={sl} TP={tp} "
                     f"profit={profit:.2f} R={r_mult}")
    return "\n".join(lines)


def main():
    _acquire_single_instance()
    try:
        while not os.path.exists(STOP_FILE):
            if initialize_existing(mt5):
                break
            print("MT5 not ready, retrying in 15s (is the terminal running?)")
            time.sleep(15)
        if os.path.exists(STOP_FILE):
            return
        print("manage.py running - BE/trailing active for magic", MAGIC)
        while not os.path.exists(STOP_FILE):
            try:
                cfg = _load(CONFIG, {})
                connection = ensure_demo_connection(mt5, EXPECTED_DEMO_LOGIN)
                if not connection.ready:
                    bus.publish({"type": "alert", "source": "manage",
                                 "payload": {"kind": "connection_blocked",
                                             "reason": connection.reason},
                                 "trace_id": None})
                    print("manage: connection blocked:", connection.reason)
                    time.sleep(float((cfg.get("manage") or {}).get("interval_s", 10)))
                    continue
                if connection.reconnected:
                    bus.publish({"type": "engine_status", "source": "manage",
                                 "payload": {"kind": "connection_restored",
                                             "account": None},
                                 "trace_id": None})
                    print("manage: broker IPC restored for authorized demo account")
                acts = manage_once(cfg)
                for a in acts:
                    print(time.strftime("%H:%M:%S"), a)
            except Exception as e:  # noqa: BLE001
                print("pass error:", e)
                if not initialize_existing(mt5):
                    time.sleep(10)
            time.sleep(float((cfg.get("manage") or {}).get("interval_s", 10)))
    finally:
        _release_lock()
        mt5.shutdown()
    print("manage.py stopped (STOP file).")


if __name__ == "__main__":
    main()

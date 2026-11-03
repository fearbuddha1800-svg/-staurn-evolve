"""Strategy 2 LIVE engine: London-open breakout on H1 - XAUUSD ONLY.

Implements EXACTLY the verified backtest (strategy2_backtest.py, selected
variant r2-cut15-buf010-cap150 in strategy2_results.json; XAUUSD 2023-2026:
1052 trades, PF 1.113, +64.0R). EURUSD failed acceptance (PF 1.045) and is
deliberately NOT traded here.

Rules (per UTC day; MT5 bar times are EET/EEST server time, converted via the
EU DST calendar - last Sunday of March/October - exactly as
strategy2_backtest.py does):
  - range  = H1 bars opening 00:00..06:59 UTC; the day is valid only when
             all 7 bars are present (and hi > lo)
  - signal = bars opening 07:00..14:59 UTC: the first H1 CLOSE beyond
             range_high + 0.10*ATR14 = BUY, below range_low - 0.10*ATR14 =
             SELL. ATR14 (Wilder, H1) is taken through the signal bar close.
             ONE entry per UTC day.
  - fill   = at market IMMEDIATELY on the closed bar that triggers (live,
             not next-bar). A bar that closed while the engine was down is
             never chased (warm-up rule, mirrors strategy.py).
  - SL     = opposite range edge, distance capped at 1.50*ATR14 from the
             actual entry price. NO TP: manage.py owns exits via magic
             20261015 (shared with strategy.py so manage trails us; our
             orders carry comment "strat2" to mark them as ours).
  - size   = config strategy2.risk_pct (default 0.5%) of balance risked on
             the SL distance, lot capped by risk.max_lot_per_trade.

Risk controls:
  - ONE entry per UTC day (persisted per symbol in strategy2_state.json,
    survives restarts) and at most strategy2.max_positions (1) open
    strategy2 positions (magic 20261015 + comment "strat2")
  - DAILY LOSS CAP: realized P/L today on magic 20261015 from history_deals
    <= -2% of balance -> write ALGO-HALT-<date> (the same file strategy.py
    uses; shared magic = shared daily budget) and stop entries for the day
  - HALT (executor), PAUSE (daemon) and STOP files are respected for NEW
    entries; open positions and manage.py exits are never touched
  - single-instance lock (strategy2.lock), same scheme as strategy.py

Orders are sent directly via mt5.order_send exactly like strategy.py:
executor.execute() hardcodes the relay magic 20261014, while this engine
must carry 20261015 so manage.py trails it.

Run:   C:/Users/voidk/miniconda3/python.exe strategy2_live.py   (persistent loop)
Stop:  create the STOP file next to daemon.py, or set strategy2.enabled=false.
"""
import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone

import MetaTrader5 as mt5
from broker_lifecycle import initialize_existing

from event_bus import bus

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.json")
STOP_FILE = os.path.join(BASE, "STOP")
HALT_FILE = os.path.join(BASE, "HALT")      # executor's new-entry gate
PAUSE_FILE = os.path.join(BASE, "PAUSE")     # daemon console new-entry gate
STATE_FILE = os.path.join(BASE, "strategy2_state.json")
LOCK_FILE = os.path.join(BASE, "strategy2.lock")
SCRIPT = os.path.basename(__file__)

ALGO_MAGIC = 20261015   # shared with strategy.py -> manage.py trails us
COMMENT = "strat2"       # our marker within the shared magic

# Frozen parameters = the verified backtest variant (r2-cut15-buf010-cap150).
ATR_P = 14
RANGE_HOURS = 7    # range = H1 bars opening 00:00..06:59 UTC
SIG_START = 7      # first eligible signal bar opens 07:00 UTC
SIG_END = 15       # bars opening >= 15:00 UTC never signal (window 07..14)
BUFFER_ATR = 0.10  # close must clear the range edge by 0.10*ATR14
CAP_ATR = 1.50     # SL capped at 1.50*ATR14 from entry
DAILY_LOSS_CAP_PCT = 2.0
BARS_FETCH = 260
MIN_BARS = 40
LOOP_S = 45


# ---- single-instance lock (same scheme as strategy.py) -----------------------
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
    if old and _pid_is_live_python(old, SCRIPT):
        print(f"{SCRIPT}: another instance is already running (pid {old}) - exiting")
        sys.exit(0)
    try:
        with open(LOCK_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except OSError as e:  # noqa: BLE001
        print(f"{SCRIPT}: could not write lock file:", e)


def _release_lock():
    try:
        os.remove(LOCK_FILE)
    except OSError:
        pass


# ---- EU DST calendar (server EET/EEST) - verbatim from strategy2_backtest ----
def last_sunday(y, m):
    nxt = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
    last = nxt - timedelta(days=1)
    return last - timedelta(days=(last.weekday() + 1) % 7)  # Mon=0..Sun=6


def server_offset_hours(d):
    """EEST (UTC+3) between the last Sundays of March/October, else EET (UTC+2).
    Transitions happen on barless Sundays; every bar date maps exactly."""
    return 3 if last_sunday(d.year, 3) <= d < last_sunday(d.year, 10) else 2


# ---- pure strategy logic (testable without MT5) ------------------------------
def bars_from_rates(rows):
    """MT5 rates rows (server-time epochs) -> bar dicts with UTC datetimes.
    Same per-bar-date EU-DST offset evaluation as strategy2_backtest.load_bars."""
    bars = []
    for r in rows:
        sdt = datetime.fromtimestamp(int(r["time"]), tz=timezone.utc)
        off = server_offset_hours(sdt.date())
        bars.append({"srv": sdt, "utc": sdt - timedelta(hours=off),
                     "o": float(r["open"]), "h": float(r["high"]),
                     "l": float(r["low"]), "c": float(r["close"])})
    return bars


def atr_series(bars):
    """Wilder ATR(14), identical math to strategy2_backtest.atr_series.
    atrs[i] = ATR through bar i's close (None until 14 TRs have accumulated)."""
    atrs = [None] * len(bars)
    prev_close = None
    atr = None
    trs = []
    for i, b in enumerate(bars):
        pc = prev_close
        if pc is not None:
            tr = max(b["h"] - b["l"], abs(b["h"] - pc), abs(b["l"] - pc))
            if atr is None:
                trs.append(tr)
                if len(trs) == ATR_P:
                    atr = sum(trs) / ATR_P
            else:
                atr = (atr * (ATR_P - 1) + tr) / ATR_P
        atrs[i] = atr
        prev_close = b["c"]
    return atrs


def range_for_day(bars, day, range_hours=RANGE_HOURS):
    """High/low over bars opening 00:00..range_hours-1 UTC on `day`.
    Valid only when ALL range_hours bars are present and hi > lo
    (strategy2_backtest.daily_ranges semantics)."""
    hi, lo, n = -1e300, 1e300, 0
    for b in bars:
        u = b["utc"]
        if u.date() == day and u.hour < range_hours:
            if b["h"] > hi:
                hi = b["h"]
            if b["l"] < lo:
                lo = b["l"]
            n += 1
    if n == range_hours and hi > lo:
        return {"hi": hi, "lo": lo, "n": n}
    return None


def signal_on_bar(bar, rng, atr, sig_start=SIG_START, sig_end=SIG_END,
                  buffer_atr=BUFFER_ATR):
    """+1/-1 if this CLOSED bar's close is beyond a buffered range edge inside
    the signal window - exact backtest _sig for the verified variant (skip_hours
    and min_range_atr are OFF there). 0 otherwise."""
    if not rng or atr is None:
        return 0
    h = bar["utc"].hour
    if h < sig_start or h >= sig_end:
        return 0
    if bar["c"] > rng["hi"] + buffer_atr * atr:
        return 1
    if bar["c"] < rng["lo"] - buffer_atr * atr:
        return -1
    return 0


def decide_newest_closed(bars):
    """One live decision pass over a fetched CLOSED-bar window: evaluate the
    NEWEST closed bar only (the engine sees every bar as it closes, so the
    first trigger it observes is the day's first close beyond). Returns
    (dirn, rng, atr, bar); dirn 0 = no signal."""
    if not bars:
        return 0, None, None, None
    bar = bars[-1]
    atr = atr_series(bars)[-1]
    rng = range_for_day(bars, bar["utc"].date())
    d = signal_on_bar(bar, rng, atr)
    return d, rng, atr, bar


def sl_for(dirn, price, rng, atr, cap_atr=CAP_ATR):
    """SL = opposite range edge, distance capped at cap_atr*ATR14 from the
    entry price (backtest: sl = max(lo, fill-cap*atr) for buys,
    min(hi, fill+cap*atr) for sells)."""
    if dirn == 1:
        return max(rng["lo"], price - cap_atr * atr)
    return min(rng["hi"], price + cap_atr * atr)


# ---- state (one entry per UTC day, survives restarts) -------------------------
def _load_state():
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def _save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=1)
    except OSError as e:  # noqa: BLE001
        print(f"{SCRIPT}: could not write state file:", e)


# ---- MT5 helpers -------------------------------------------------------------
def _halt_file():
    # same file convention as strategy.py (shared magic -> shared daily halt)
    return os.path.join(BASE, f"ALGO-HALT-{time.strftime('%Y%m%d')}")


def _halt_today():
    return os.path.exists(_halt_file())


def _algo_pl_today_realized():
    """Realized P/L for ALGO_MAGIC since local midnight, from history_deals
    (mirrors strategy.py's daily-loss window; floating P/L is intentionally
    excluded - open trades are protected by their SL / manage.py)."""
    day0 = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    deals = mt5.history_deals_get(day0, datetime.now() + timedelta(days=1))
    pl = 0.0
    for d in deals or []:
        if d.magic == ALGO_MAGIC:
            pl += (d.profit + d.commission + d.swap + getattr(d, "fee", 0.0)) or 0.0
    return pl


def _own_positions():
    """Open positions that belong to THIS engine (shared magic, our comment)."""
    n = 0
    positions = mt5.positions_get()
    if positions is None:
        return None
    for p in positions:
        if p.magic == ALGO_MAGIC and COMMENT in (getattr(p, "comment", "") or ""):
            n += 1
    return n


def _volume_for(sym, sl_dist, risk_pct, cap):
    """Lot so an SL hit costs ~risk_pct% of balance (identical to
    strategy.py _volume_for, incl. the volume_min floor and step rounding)."""
    acct = mt5.account_info()
    info = mt5.symbol_info(sym)
    if not (acct and info):
        return None
    tick_size = info.trade_tick_size or info.point
    tick_value = info.trade_tick_value
    if not (tick_size and tick_value) or sl_dist <= 0:
        return None
    loss_per_lot = sl_dist / tick_size * tick_value
    if loss_per_lot <= 0:
        return None
    lot = (acct.balance * risk_pct / 100.0) / loss_per_lot
    lot = max(info.volume_min, min(lot, cap))
    step = info.volume_step or 0.01
    return round(round(lot / step) * step, 8)


def _fill(sym):
    info = mt5.symbol_info(sym)
    fm = getattr(info, "filling_mode", 1)
    if fm & 2:
        return mt5.ORDER_FILLING_IOC
    if fm & 1:
        return mt5.ORDER_FILLING_FOK
    return mt5.ORDER_FILLING_RETURN


# ---- entry -------------------------------------------------------------------
def try_trade(sym, dirn, rng, atr, bar, cfg2, lot_cap):
    """Guards -> size -> market order for the day's single entry.
    The day is CONSUMED (state file) on every actual attempt - signal skip,
    sizing failure, broker reject or fill - so the day never gets a second
    entry. Pure guard skips (STOP/HALT/PAUSE, loss cap, position gate, no
    market data) leave the day open: a later bar can still trigger once the
    guard clears. Mirrors strategy.py try_trade's structure."""
    import notify
    today = bar["utc"].date().isoformat()
    action = "buy" if dirn == 1 else "sell"
    state = _load_state()
    if (state.get(sym) or {}).get("entry_date") == today:
        return                      # one entry per UTC day, already spent
    if os.path.exists(STOP_FILE) or os.path.exists(HALT_FILE) or os.path.exists(PAUSE_FILE):
        return                      # global new-entry gates, respected
    if _halt_today():
        return                      # daily loss cap file (ours or strategy.py's)
    acct = mt5.account_info()
    if not acct:
        return
    pl = _algo_pl_today_realized()
    if pl <= -abs(acct.balance) * DAILY_LOSS_CAP_PCT / 100.0:
        try:
            with open(_halt_file(), "w", encoding="utf-8") as f:
                f.write("halt")
        except OSError as e:  # noqa: BLE001
            print(f"{SCRIPT}: could not write halt file:", e)
        notify._send_sync(f"🛑 strat2: daily loss cap hit ({pl:.2f}); "
                          f"algo entries paused until tomorrow")
        return
    own_positions = _own_positions()
    if own_positions is None or own_positions >= int(cfg2.get("max_positions", 1)):
        return                      # one strategy2 position max
    if not mt5.symbol_select(sym, True):
        return
    tick = mt5.symbol_info_tick(sym)
    info = mt5.symbol_info(sym)
    if not (tick and info):
        return                      # no market data: transient, day not consumed
    price = tick.ask if dirn == 1 else tick.bid
    sl = round(price - 2.0 * atr if dirn == 1 else price + 2.0 * atr, info.digits)
    bad = None
    if (dirn == 1 and sl >= price) or (dirn == -1 and sl <= price):
        bad = "entry gapped through the range (R<=0, backtest invalid_r)"
    else:
        stops_dist = max(getattr(info, "trade_stops_level", 0) * info.point, 10 * info.point)
        if abs(price - sl) < stops_dist:
            bad = f"SL too close to price ({abs(price - sl):.5f} < {stops_dist:.5f})"
    if bad is None:
        lot = _volume_for(sym, abs(price - sl), float(cfg2.get("risk_pct", 0.5)), lot_cap)
        if not lot:
            bad = "could not size a lot from the SL distance"
    if bad is not None:
        state[sym] = {"entry_date": today, "side": action, "status": "skipped",
                      "detail": bad, "bar_utc": bar["utc"].isoformat()}
        _save_state(state)
        notify._send_sync(f"⚙️ strat2 {action.upper()} {sym} signal skipped: {bad}")
        return
    # the day's single entry is spent from here on - record BEFORE sending so
    # a crash between send and save can never double-enter the day
    state[sym] = {"entry_date": today, "side": action, "status": "sending",
                  "bar_utc": bar["utc"].isoformat(), "price": price, "sl": sl,
                  "lot": lot}
    _save_state(state)
    # SINGLE ENTRY AUTHORITY (masterbook section 4): route through
    # executor.execute_algo for the same guards as every other entry origin.
    # Configuration cannot bypass this authority while execution is offline.
    if True:
        import executor
        res = executor.execute_algo(sym, action, lot, sl, 0.0,
                                    msg_id=f"strat2:{sym}:{today}", magic=ALGO_MAGIC,
                                    comment=COMMENT, strategy_name="london-breakout")
        if res.get("status") == "executed":
            state[sym].update({"status": "executed", "ticket": res.get("ticket"),
                               "fill": res.get("fill_price")})
            _save_state(state)
            notify._send_sync(f"⚙️ STRAT2 {action.upper()} {sym} {res.get('lot')} @ "
                              f"{res.get('fill_price')} | SL {sl} | no TP "
                              f"(manage.py trails magic {ALGO_MAGIC})")
        else:
            why = f"{res.get('status')}: {res.get('detail', '')}"
            state[sym].update({"status": "rejected", "detail": why})
            _save_state(state)
            notify._send_sync(f"⚙️ strat2 {action} {sym} not filled: {why}")
        return



# ---- live loop (mirrors strategy.py main) -------------------------------------
def main():
    _acquire_single_instance()
    try:
        while not os.path.exists(STOP_FILE):
            if initialize_existing(mt5):
                break
            print("strategy2_live: MT5 not ready, retrying in 15s")
            time.sleep(15)
        if os.path.exists(STOP_FILE):
            return
        print(f"strategy2_live.py running (magic {ALGO_MAGIC}, comment {COMMENT!r})")
        last_bar = {}
        while not os.path.exists(STOP_FILE):
            try:
                with open(CONFIG, "r", encoding="utf-8") as f:
                    cfg_all = json.load(f)
                cfg2 = cfg_all.get("strategy2") or {}
                symbols = cfg2.get("symbols") or ["XAUUSD"]
                lot_cap = float((cfg_all.get("risk") or {}).get("max_lot_per_trade", 0.10))
                enabled = bool(cfg2.get("enabled", True))
                for sym in symbols:
                    rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, BARS_FETCH)
                    if rates is None or len(rates) < MIN_BARS:
                        continue
                    closed = rates[:-1]      # drop the still-forming bar
                    bt = int(closed[-1]["time"])
                    if last_bar.get(sym) == bt:
                        continue              # no new closed bar yet
                    first = last_bar.get(sym) is None
                    last_bar[sym] = bt
                    if first:
                        continue              # warm-up pass: no decisions on catch-up
                    if not enabled:
                        continue              # soft off: keep polling, no decisions
                    bars = bars_from_rates(closed)
                    dirn, rng, atr, bar = decide_newest_closed(bars)
                    if dirn:
                        try_trade(sym, dirn, rng, atr, bar, cfg2, lot_cap)
            except Exception as e:  # noqa: BLE001
                print("strategy2 loop error:", e)
                if not initialize_existing(mt5):
                    time.sleep(15)
            time.sleep(LOOP_S)
        print("strategy2_live.py stopped (STOP file)")
    finally:
        _release_lock()
        mt5.shutdown()


if __name__ == "__main__":
    main()

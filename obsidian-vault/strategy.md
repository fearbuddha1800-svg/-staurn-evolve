---
slug: strategy
type: note
graph: gitnexus
---

"""Algo strategy engine: multi-factor trend-pullback on closed H1 bars.

Rules (per symbol, long+short):
  TREND    EMA50 vs EMA200 on H1
  ENTRY    pullback: RSI(14) crosses back UP through rsi_buy in an uptrend
           (buy), crosses back DOWN through rsi_sell in a downtrend (sell)
  RISK     SL = atr_sl_mult * ATR(14), TP = atr_tp_mult * ATR(14)
  SIZE     risk_pct of balance based on SL distance (capped by max lot)
  FILTERS  skip dead hours; one position per symbol; max N algo positions;
           daily loss cap halts the algo for the rest of the day.

Orders carry magic 20261015 (signal-relay uses 20261014; manage.py trails both).
Run:  C:/Users/voidk/miniconda3/python.exe strategy.py   (persistent loop)
Backtest WITHOUT live trading: backtest.py imports Indicators/decide from here.
"""
import json
import os
import sys
import time

import MetaTrader5 as mt5
from broker_lifecycle import initialize_existing

from event_bus import bus
from loss_halt import LossHalt, SafetyError as _LHError

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.json")
STOP_FILE = os.path.join(BASE, "STOP")
ALGO_MAGIC = 20261015
LOCK_FILE = os.path.join(BASE, "strategy.lock")


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
        print(f"strategy.py: another instance is already running (pid {old}) - exiting")
        sys.exit(0)
    try:
        with open(LOCK_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except OSError as e:  # noqa: BLE001
        print("strategy.py: could not write lock file:", e)


def _release_lock():
    try:
        os.remove(LOCK_FILE)
    except OSError:
        pass


def load_algo_cfg():
    with open(CONFIG, "r", encoding="utf-8") as f:
        return json.load(f).get("algo", {})


class Indicators:
    """Incremental EMA50/EMA200, Wilder RSI(14), Wilder ATR(14) - identical math
    used by both the live engine and the backtester."""

    def __init__(self, period=14, fast=50, slow=200):
        self.p = period
        self.kf = 2.0 / (fast + 1)
        self.ks = 2.0 / (slow + 1)
        self.prev_close = None
        self.ef = self.es = None
        self._sf, self._ss = [], []
        self.ag = self.al = None
        self._gsum = self._lsum = self._dc = 0
        self.rsi = self.last_rsi = None
        self.atr = None
        self._trs = []
        self.n = 0

    def update(self, h, l, c):
        pc = self.prev_close
        if pc is not None:
            tr = max(h - l, abs(h - pc), abs(l - pc))
            if self.atr is None:
                self._trs.append(tr)
                if len(self._trs) == self.p:
                    self.atr = sum(self._trs) / self.p
            else:
                self.atr = (self.atr * (self.p - 1) + tr) / self.p
            d = c - pc
            if self.ag is None:
                self._gsum += max(d, 0)
                self._lsum += max(-d, 0)
                self._dc += 1
                if self._dc == self.p:
                    self.ag, self.al = self._gsum / self.p, self._lsum / self.p
            else:
                self.ag = (self.ag * (self.p - 1) + max(d, 0)) / self.p
                self.al = (self.al * (self.p - 1) + max(-d, 0)) / self.p
        if self.ag is not None:
            self.last_rsi = self.rsi
            self.rsi = 100.0 if self.al == 0 else 100.0 - 100.0 / (1.0 + self.ag / self.al)
        if self.ef is None:
            self._sf.append(c)
            if len(self._sf) == 50:
                self.ef = sum(self._sf) / 50.0
        else:
            self.ef = c * self.kf + self.ef * (1 - self.kf)
        if self.es is None:
            self._ss.append(c)
            if len(self._ss) == 200:
                self.es = sum(self._ss) / 200.0
        else:
            self.es = c * self.ks + self.es * (1 - self.ks)
        self.prev_close = c
        self.n += 1

    @property
    def ready(self):
        return self.ef is not None and self.es is not None and self.atr and self.rsi is not None


def decide(ind, rsi_buy=40.0, rsi_sell=60.0, strength=0.0):
    """Entry decision on a CLOSED bar. Returns ('buy'|'sell', atr) or (None, None).
    strength: require |EMA50-EMA200| > strength*ATR (skips chop when > 0)."""
    if not ind.ready:
        return None, None
    r, pr = ind.rsi, ind.last_rsi
    if pr is None:
        return None, None
    if strength > 0 and abs(ind.ef - ind.es) < strength * ind.atr:
        return None, None
    if ind.ef > ind.es and pr < rsi_buy <= r:
        return "buy", ind.atr
    if ind.ef < ind.es and pr > rsi_sell >= r:
        return "sell", ind.atr
    return None, None


# ---- live engine -----------------------------------------------------------
def _halt_today():
    return os.path.exists(os.path.join(BASE, f"ALGO-HALT-{time.strftime('%Y%m%d')}"))


def _algo_pl_today():
    """Realized + floating P/L for ALGO_MAGIC since local midnight."""
    from datetime import datetime

    day0 = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    pl = 0.0
    deals = mt5.history_deals_get(day0, datetime.now() + __import__("datetime").timedelta(days=1))
    for d in deals or []:
        if d.magic == ALGO_MAGIC:
            pl += d.profit + d.commission + d.swap + getattr(d, "fee", 0.0) or 0.0
    for p in mt5.positions_get() or []:
        if p.magic == ALGO_MAGIC:
            pl += p.profit + p.swap
    return pl


def _volume_for(sym, sl_dist, risk_pct, cap):
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


def _has_position(sym):
    positions = mt5.positions_get()
    return positions is None or any(p.magic == ALGO_MAGIC and p.symbol == sym for p in positions)


def try_trade(sym, action, atr, cfg):
    import notify
    if _halt_today() or os.path.exists(STOP_FILE):
        return
    if _has_position(sym):
        return
    positions = mt5.positions_get()
    if positions is None:
        return
    if sum(1 for p in positions if p.magic == ALGO_MAGIC) >= cfg.get("max_positions_total", 3):
        notify._send_sync(f"⚙️ algo: {action.upper()} {sym} signal skipped (max algo positions)")
        return
    acct = mt5.account_info()
    cap_pct = float(cfg.get("daily_loss_cap_pct", 2.0))
    if acct is None:
        return
    pl = _algo_pl_today()
    if pl <= -abs(acct.balance) * cap_pct / 100.0:
        open(os.path.join(BASE, f"ALGO-HALT-{time.strftime('%Y%m%d')}"), "w").write("halt")
        notify._send_sync(f"🛑 algo: daily loss cap hit ({pl:.2f}); algo paused until tomorrow")
        return
    if not mt5.symbol_select(sym, True):
        return
    tick = mt5.symbol_info_tick(sym)
    if not tick:
        return
    sl_d = 2.0 * atr  # fixed protection policy; no configurable TP
    price = tick.ask if action == "buy" else tick.bid
    sl = round(price - sl_d if action == "buy" else price + sl_d, mt5.symbol_info(sym).digits)
    tp = 0.0  # exit via manage.py trailing
    lot = _volume_for(sym, sl_d, float(cfg.get("risk_pct", 1.0)), 0.10)
    if not lot:
        return
    # SINGLE ENTRY AUTHORITY (masterbook section 4): route through
    # executor.execute_algo so algo entries get the SAME guards as the Telegram
    # path. The offline executor blocks all new entries; configuration cannot
    # bypass this authority via a legacy direct order_send path.
    if True:  # mandatory authority; offline executor blocks all new orders
        import executor
        msg_id = f"algo:{sym}:{time.strftime('%Y%m%d%H')}"
        res = executor.execute_algo(sym, action, lot, sl, tp, msg_id=msg_id,
                                    magic=ALGO_MAGIC, comment="algo",
                                    strategy_name="rsi-pullback")
        if res.get("status") == "executed":
            notify._send_sync(f"⚙️ ALGO {action.upper()} {sym} {res.get('lot')} @ "
                              f"{res.get('fill_price')} | SL {sl} TP {tp}")
        else:
            notify._send_sync(f"⚙️ algo {action} {sym} not filled: "
                              f"{res.get('status')} {res.get('detail', '')}")
        return



def main():
    _acquire_single_instance()
    try:
        while not os.path.exists(STOP_FILE):
            if initialize_existing(mt5):
                break
            print("MT5 not ready, retrying in 15s")
            time.sleep(15)
        if os.path.exists(STOP_FILE):
            return
        print("strategy.py running (magic", ALGO_MAGIC, ")")
        import notify
        cfg = load_algo_cfg()
        symbols = cfg.get("symbols", ["XAUUSD", "EURUSD", "GBPUSD"])
        skip_hours = set(cfg.get("skip_hours_utc", [22, 23]))
        rsi_buy = float(cfg.get("rsi_buy", 40))
        rsi_sell = float(cfg.get("rsi_sell", 60))
        strength = float(cfg.get("strength", 1.0))
        inds, last_bar = {s: Indicators() for s in symbols}, {}
        while not os.path.exists(STOP_FILE):
            try:
                cfg = load_algo_cfg()
                for sym in symbols:
                    rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 260)
                    if rates is None or len(rates) < 210:
                        continue
                    closed = rates[:-1]  # drop the still-forming bar
                    bt = int(closed[-1]["time"])
                    if last_bar.get(sym) == bt:
                        continue
                    first = last_bar.get(sym) is None
                    last_bar[sym] = bt
                    ind = inds[sym]
                    for b in closed:
                        ind.update(b["high"], b["low"], b["close"])
                    if first:
                        continue  # warm-up pass, no decisions on historical catch-up
                    if time.gmtime().tm_hour in skip_hours:
                        continue
                    action, atr = decide(ind, rsi_buy, rsi_sell, strength)
                    if action:
                        try_trade(sym, action, atr, cfg)
            except Exception as e:  # noqa: BLE001
                print("algo loop error:", e)
                if not initialize_existing(mt5):
                    time.sleep(15)
            time.sleep(45)
        print("strategy.py stopped (STOP file)")
    finally:
        _release_lock()


if __name__ == "__main__":
    main()

## Links from
- [[backtest]]

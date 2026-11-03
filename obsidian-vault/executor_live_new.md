---
slug: executor_live_new
type: note
graph: gitnexus
---

"""MT5 executor: takes a parsed signal dict from parser.py and trades it on the
MetaTrader 5 terminal running on this machine, with a hard risk guard.

Uses the official MetaTrader5 Python package. Requires the MT5 terminal to be
running and logged in (it attaches to the running terminal).
"""
import hashlib
import json
import math
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import MetaTrader5 as mt5

from event_bus import make_event, publish, bus, new_trace_id
from broker_lifecycle import initialize_existing

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "signals.db")
HALT_FILE = os.path.join(BASE, "HALT")
CONFIG = os.path.join(BASE, "config.json")
LEDGER_DIR = Path(__file__).resolve().parent / "audit_ledger"
LEDGER_FILE = LEDGER_DIR / "ledger.jsonl"

MAGIC = 20261014
ALGO_MAGIC = 20261015

_symbol_cache: Dict[str, Any] = {}

os.makedirs(LEDGER_DIR, exist_ok=True)


def load_config() -> dict:
    try:
        with open(CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def halted() -> bool:
    return os.path.exists(HALT_FILE)


# ---------------------------------------------------------------------------
# MT5 attachment
# ---------------------------------------------------------------------------

def _mt5_ensure() -> bool:
    """Ensure MT5 is attached. Returns True when connected."""
    if mt5.terminal_info() is not None:
        return True
    return initialize_existing(mt5)


def resolve_symbol(raw: str) -> Optional[str]:
    """Resolve a raw symbol string to a broker symbol name via MT5."""
    if not raw or not isinstance(raw, str):
        return None
    raw = raw.strip().upper()
    if raw in _symbol_cache:
        return _symbol_cache[raw]
    if not _mt5_ensure():
        return None
    info = mt5.symbol_info(raw)
    if info is not None:
        _symbol_cache[raw] = raw
        return raw
    for suffix in ("", ".pro", ".ecn", ".raw", ".micro"):
        cand = raw + suffix
        info = mt5.symbol_info(cand)
        if info is not None:
            _symbol_cache[raw] = cand
            return cand
    if mt5.symbol_select(raw, True):
        info = mt5.symbol_info(raw)
        if info is not None:
            _symbol_cache[raw] = raw
            return raw
    return None


def tick_price(sym: str, side: str) -> float:
    t = mt5.symbol_info_tick(sym)
    if t is None:
        return 0.0
    return t.ask if side == "buy" else t.bid


def _fill_type(sym: str) -> int:
    info = mt5.symbol_info(sym)
    if info is None:
        return mt5.ORDER_FILLING_RETURN
    fills = info.filling_mode
    if fills & mt5.ORDER_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    if fills & mt5.ORDER_FILLING_IOC:
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN


def _norm_volume(sym: str, volume: float) -> float:
    info = mt5.symbol_info(sym)
    if info is None:
        return round(volume, 2)
    step = info.volume_step
    min_vol = info.volume_min
    max_vol = info.volume_max
    v = max(min_vol, min(max_vol, round(volume / step) * step))
    return round(v, 2)


def _atr14(sym: str) -> Optional[float]:
    """Compute ATR(14) from the last 15 H1 bars."""
    if not _mt5_ensure():
        return None
    rates = mt5.copy_rates_from_pos(sym, mt5.TIMEFRAME_H1, 0, 16)
    if rates is None or len(rates) < 15:
        return None
    trs = []
    for i in range(1, len(rates)):
        r = rates[i]
        prev = rates[i - 1]
        tr = max(
            r["high"] - r["low"],
            abs(r["high"] - prev["close"]),
            abs(r["low"] - prev["close"]),
        )
        trs.append(tr)
    if len(trs) < 14:
        return None
    a = sum(trs[:14]) / 14.0
    for tr in trs[14:]:
        a = (a * 13 + tr) / 14.0
    return a


def _validate_stops(sym: str, action: str, entry: Optional[float],
                    sl: Optional[float], tp: Optional[float]) -> Optional[str]:
    info = mt5.symbol_info(sym)
    if info is None:
        return "symbol_info unavailable"
    digits = info.digits
    point = info.point
    stops_level = info.stops_level
    tick = mt5.symbol_info_tick(sym)
    if tick is None:
        return "no tick data"
    ref = tick.ask if action == "buy" else tick.bid
    min_dist = stops_level * point
    if sl is not None:
        dist = abs(ref - sl)
        if dist < min_dist:
            return f"SL too close to market (min {min_dist:.{digits}f})"
    if tp is not None:
        dist = abs(ref - tp)
        if dist < min_dist:
            return f"TP too close to market (min {min_dist:.{digits}f})"
    return None


def _pick_tp(parsed: dict) -> Optional[float]:
    tps = parsed.get("tps") or parsed.get("tp")
    if tps is None:
        return None
    if isinstance(tps, list):
        return tps[0] if tps else None
    return float(tps)


def _compute_lot(cfg: dict, sym: str, parsed: dict) -> float:
    risk = cfg.get("risk", {})
    risk_pct = float(risk.get("risk_pct", 1.0)) / 100.0
    fallback = float(risk.get("fallback_lot", 0.1))
    max_lot = float(risk.get("max_lot_per_trade", 0.1))
    ai = mt5.account_info()
    balance = ai.balance if ai else 10000.0
    risk_amount = balance * risk_pct
    sl = parsed.get("sl")
    entry = parsed.get("entry")
    tick = mt5.symbol_info_tick(sym)
    if tick is None:
        return fallback
    ref = tick.ask if parsed.get("action") == "buy" else tick.bid
    entry_price = float(entry) if entry is not None else ref
    if sl is None:
        return min(fallback, max_lot)
    sl_price = float(sl)
    dist = abs(entry_price - sl_price)
    if dist <= 0:
        return min(fallback, max_lot)
    info = mt5.symbol_info(sym)
    if info is None:
        return min(fallback, max_lot)
    tick_value = info.trade_tick_value
    tick_size = info.trade_tick_size
    if tick_value <= 0 or tick_size <= 0:
        return min(fallback, max_lot)
    money_per_point_per_lot = tick_value / tick_size
    lots = risk_amount / (dist * money_per_point_per_lot / tick_size)
    lots = _norm_volume(sym, lots)
    return min(lots, max_lot)


def _guards(cfg: dict, sym: str, lot: float, msg_id: Any) -> Tuple[bool, str]:
    if halted():
        return False, "HALT active - new entries blocked"
    ai = mt5.account_info()
    if ai is None:
        return False, "account_info unavailable"
    risk = cfg.get("risk", {})
    max_positions = int(risk.get("max_open_positions", 5))
    positions = mt5.positions_get(symbol=sym) or []
    if len(positions) >= max_positions:
        return False, f"max open positions ({max_positions}) reached"
    max_trades_day = int(risk.get("max_trades_per_day", 20))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        con = sqlite3.connect(DB)
        try:
            count = con.execute(
                "SELECT COUNT(*) FROM trades WHERE date(ts) = ? AND status = 'executed'",
                (today,),
            ).fetchone()[0]
        finally:
            con.close()
    except Exception:
        count = 0
    if count >= max_trades_day:
        return False, f"max trades per day ({max_trades_day}) reached"
    min_free_pct = float(risk.get("min_free_margin_pct", 30))
    if ai.margin > 0 and ai.margin_free / ai.margin * 100 < min_free_pct:
        return False, f"free margin below {min_free_pct}%"
    allowed = risk.get("allowed_symbols", [])
    if allowed and sym not in allowed:
        return False, f"symbol {sym} not in allowed_symbols"
    if lot <= 0:
        return False, "lot size is zero"
    return True, "ok"


def _record(result: dict, parsed: dict, ticket: int):
    try:
        con = sqlite3.connect(DB)
        try:
            con.execute(
                """CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    msg_id TEXT,
                    ts TEXT,
                    symbol TEXT,
                    side TEXT,
                    entry REAL,
                    sl REAL,
                    tp TEXT,
                    volume REAL,
                    status TEXT,
                    detail TEXT,
                    ticket INTEGER,
                    fill_price REAL,
                    recorded_at TEXT
                )""",
            )
            con.execute(
                """INSERT INTO trades
                (msg_id, ts, symbol, side, entry, sl, tp, volume, status,
                 detail, ticket, fill_price, recorded_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    result.get("msg_id"),
                    result.get("recorded_at") or datetime.now(timezone.utc).isoformat(),
                    parsed.get("symbol"),
                    parsed.get("action"),
                    parsed.get("entry"),
                    parsed.get("sl"),
                    json.dumps(parsed.get("tps") or parsed.get("tp")) if (parsed.get("tps") or parsed.get("tp")) else None,
                    result.get("lot") or 0.0,
                    result.get("status"),
                    result.get("detail"),
                    ticket,
                    result.get("fill_price"),
                    result.get("recorded_at") or datetime.now(timezone.utc).isoformat(),
                ),
            )
            con.commit()
        finally:
            con.close()
    except Exception as e:
        print(f"trade record write failed: {e}")


def _log_to_ledger(strategy: str, symbol: str, signal_type: str, price: float,
                   confidence: Optional[float], sl: Optional[float],
                   tp: Optional[float], metadata: dict, trace_id: str) -> str:
    entry = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "strategy": strategy,
        "symbol": symbol,
        "signal_type": signal_type,
        "price": price,
        "confidence": confidence,
        "sl": sl,
        "tp": tp,
        "metadata": metadata or {},
        "trace_id": trace_id,
    }
    if os.path.exists(LEDGER_FILE):
        try:
            last_line = open(LEDGER_FILE, encoding="utf-8").read().strip().split("\n")[-1]
            if last_line:
                prev = json.loads(last_line)
                entry["previous_hash"] = prev.get("hash", "")
        except Exception:
            entry["previous_hash"] = ""
    snapshot = {k: v for k, v in sorted(entry.items()) if k != "id"}
    raw = json.dumps(snapshot, sort_keys=True, separators=(",", ":"))
    entry["hash"] = hashlib.sha256(raw.encode()).hexdigest()
    with open(LEDGER_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry["id"]


def _emit_order_events(result: dict, parsed: dict, trace_id: str):
    publish(
        make_event(
            type="order_placed",
            source="executor",
            payload=dict(
                ticket=result.get("ticket"),
                symbol=parsed.get("symbol"),
                side=parsed.get("action"),
                lot=result.get("lot"),
                price=result.get("fill_price"),
                sl=parsed.get("sl"),
                tp=parsed.get("tps"),
                trace_id=trace_id,
            ),
            trace_id=trace_id,
        )
    )


# ---------------------------------------------------------------------------
# execute — daemon-compatible signal execution
# ---------------------------------------------------------------------------

def execute(parsed, msg_id=None, lot=None, dry_run=False, channel_id=None,
            magic=None, *, trace_id=None) -> dict:
    """Execute one parsed signal on MT5. Returns a result dict."""
    trace_id = str(trace_id or msg_id or uuid.uuid4().hex)
    cfg = load_config()
    result: dict = {
        "msg_id": str(msg_id or ""),
        "symbol": parsed.get("symbol"),
        "resolved": None,
        "side": parsed.get("action"),
        "entry": str(parsed.get("entry")) if parsed.get("entry") is not None else None,
        "sl": parsed.get("sl"),
        "tp": parsed.get("tps"),
        "status": "skipped",
    }
    if not _mt5_ensure():
        result["detail"] = "MT5 not attached (executor)"
        _record(result, parsed, 0)
        return result

    sym = resolve_symbol(parsed.get("symbol") or "")
    result["resolved"] = sym
    pol = (cfg.get("signal_policy") or {}).get(
        str(channel_id) if channel_id is not None else "",
        cfg.get("signal_policy", {}).get("_default", {}),
    )
    if pol.get("mode") == "shadow":
        result["status"] = "skipped"
        result["detail"] = "shadow policy - recorded, not traded"
        _record(result, parsed, 0)
        return result
    if pol.get("sl_mode") == "atr" and sym:
        atr = _atr14(sym)
        tick = mt5.symbol_info_tick(sym)
        if atr and tick:
            d = float(pol.get("atr_mult", 2.0)) * atr
            ref = tick.ask if parsed.get("action") == "buy" else tick.bid
            parsed = dict(parsed)
            parsed["sl"] = round(
                ref - d if parsed.get("action") == "buy" else ref + d,
                mt5.symbol_info(sym).digits,
            )
    if pol.get("tp_mode") == "none":
        parsed = dict(parsed)
        parsed["tps"] = []
    result["sl"] = parsed.get("sl")
    result["tp"] = parsed.get("tps")
    if not sym:
        result["detail"] = "symbol not found on this broker"
        _record(result, parsed, 0)
        return result
    use_lot = float(lot) if lot else _compute_lot(cfg, sym, parsed)
    ok, reason = _guards(cfg, sym, use_lot, msg_id)
    if not ok:
        result["detail"] = reason
        _record(result, parsed, 0)
        return result
    try:
        import news_fetcher
        news_reason = news_fetcher.block_reason(cfg)
    except Exception as e:
        news_reason = None
        print(f"news filter unavailable (fail-open): {type(e).__name__}: {e}")
    if news_reason:
        result["status"] = "skipped_news_window"
        result["detail"] = news_reason
        _record(result, parsed, 0)
        return result
    if not mt5.symbol_select(sym, True):
        result["detail"] = f"could not select {sym} in Market Watch"
        _record(result, parsed, 0)
        return result
    sl = parsed.get("sl")
    if not sl and cfg.get("risk", {}).get("require_sl", True):
        result["detail"] = "signal has no stop-loss (require_sl) - skipped"
        _record(result, parsed, 0)
        return result
    tp = _pick_tp(parsed)
    entry = parsed.get("entry")
    order_type = parsed.get("order_type", "market")
    bad = _validate_stops(sym, parsed.get("action"),
                          entry if isinstance(entry, float) else None, sl, tp)
    if bad:
        result["detail"] = f"stop validation failed: {bad}"
        _record(result, parsed, 0)
        return result
    if dry_run:
        result["status"] = "dry_run_ok"
        return result
    use_lot = _norm_volume(sym, use_lot)
    side = mt5.ORDER_TYPE_BUY if parsed["action"] == "buy" else mt5.ORDER_TYPE_SELL
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": sym,
        "volume": use_lot,
        "type": side,
        "price": tick_price(sym, parsed["action"]),
        "sl": sl or 0.0,
        "tp": tp or 0.0,
        "deviation": 30,
        "magic": magic or MAGIC,
        "comment": f"sigrelay {msg_id or ''}"[:31],
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _fill_type(sym),
    }
    if order_type in ("limit", "stop") and isinstance(entry, float):
        req["action"] = mt5.TRADE_ACTION_PENDING
        req["price"] = entry
        pend = {
            "limit": (mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_SELL_LIMIT),
            "stop": (mt5.ORDER_TYPE_BUY_STOP, mt5.ORDER_TYPE_SELL_STOP),
        }
        req["type"] = pend[order_type][0 if parsed["action"] == "buy" else 1]

    res = mt5.order_send(req)
    if res is None:
        result["detail"] = f"order_send returned None: {mt5.last_error()}"
        _record(result, parsed, 0)
        return result
    result["ticket"] = res.order
    if res.retcode == mt5.TRADE_RETCODE_DONE:
        result["status"] = "executed"
        result["fill_price"] = res.price
        result["lot"] = use_lot
    else:
        result["status"] = "broker_rejected"
        result["detail"] = f"retcode {res.retcode}: {res.comment}"
    result["recorded_at"] = datetime.now(timezone.utc).isoformat()
    _record(result, parsed, res.order)
    if res.retcode == mt5.TRADE_RETCODE_DONE:
        _emit_order_events(result, parsed, trace_id)
    return result


# ---------------------------------------------------------------------------
# execute_algo — single algo entry authority
# ---------------------------------------------------------------------------

def execute_algo(symbol, side, lot, sl, tp, msg_id=None, magic=ALGO_MAGIC,
                 comment="algo", dry_run=False, strategy_name=None,
                 *, trace_id=None) -> dict:
    """Single algo entry authority: all algo entries submit through here."""
    trace_id = str(trace_id or msg_id or uuid.uuid4().hex)
    cfg = load_config()
    result: dict = {
        "msg_id": str(msg_id or ""),
        "symbol": symbol,
        "resolved": None,
        "side": side,
        "entry": None,
        "sl": sl,
        "tp": tp,
        "status": "skipped",
    }
    if not _mt5_ensure():
        result["detail"] = "MT5 not attached (executor_algo)"
        _record(result, {"symbol": symbol, "action": side, "sl": sl, "tp": tp}, 0)
        return result

    sym = resolve_symbol(symbol)
    result["resolved"] = sym
    if not sym:
        result["detail"] = "symbol not found on this broker"
        _record(result, {"symbol": symbol, "action": side, "sl": sl, "tp": tp}, 0)
        return result
    ok, reason = _guards(cfg, sym, float(lot) if lot else 0.1, msg_id)
    if not ok:
        result["detail"] = reason
        _record(result, {"symbol": symbol, "action": side, "sl": sl, "tp": tp}, 0)
        return result
    if not mt5.symbol_select(sym, True):
        result["detail"] = f"could not select {sym} in Market Watch"
        _record(result, {"symbol": symbol, "action": side, "sl": sl, "tp": tp}, 0)
        return result
    bad = _validate_stops(sym, side, None, sl, tp)
    if bad:
        result["detail"] = f"stop validation failed: {bad}"
        _record(result, {"symbol": symbol, "action": side, "sl": sl, "tp": tp}, 0)
        return result
    if dry_run:
        result["status"] = "dry_run_ok"
        return result
    use_lot = _norm_volume(sym, float(lot) if lot else 0.1)
    side_mt5 = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": sym,
        "volume": use_lot,
        "type": side_mt5,
        "price": tick_price(sym, side),
        "sl": sl or 0.0,
        "tp": tp or 0.0,
        "deviation": 30,
        "magic": magic,
        "comment": comment[:31],
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _fill_type(sym),
    }
    res = mt5.order_send(req)
    if res is None:
        result["detail"] = f"order_send returned None: {mt5.last_error()}"
        _record(result, {"symbol": symbol, "action": side, "sl": sl, "tp": tp}, 0)
        return result
    result["ticket"] = res.order
    if res.retcode == mt5.TRADE_RETCODE_DONE:
        result["status"] = "executed"
        result["fill_price"] = res.price
        result["lot"] = use_lot
    else:
        result["status"] = "broker_rejected"
        result["detail"] = f"retcode {res.retcode}: {res.comment}"
    result["recorded_at"] = datetime.now(timezone.utc).isoformat()
    _record(result, {"symbol": symbol, "action": side, "sl": sl, "tp": tp}, res.order)
    if res.retcode == mt5.TRADE_RETCODE_DONE:
        _emit_order_events(result, {"symbol": symbol, "action": side, "sl": sl, "tp": tp}, trace_id)
    return result


# ---------------------------------------------------------------------------
# place_order — generic order placement
# ---------------------------------------------------------------------------

def place_order(ticket: str, symbol: str, side: str, volume: float,
                sl: Optional[float], tp: Optional[float],
                entry: Optional[float] = None) -> dict:
    """Place a real MT5 order. Returns a result dict."""
    if not _mt5_ensure():
        return {"status": "blocked", "reason": "mt5_not_attached", "ticket": None}
    sym = resolve_symbol(symbol)
    if not sym:
        return {"status": "blocked", "reason": "symbol_not_found", "ticket": None}
    use_lot = _norm_volume(sym, volume)
    side_mt5 = mt5.ORDER_TYPE_BUY if side == "buy" else mt5.ORDER_TYPE_SELL
    req = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": sym,
        "volume": use_lot,
        "type": side_mt5,
        "price": tick_price(sym, side),
        "sl": sl or 0.0,
        "tp": tp or 0.0,
        "deviation": 30,
        "magic": MAGIC,
        "comment": f"place_order {ticket or ''}"[:31],
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _fill_type(sym),
    }
    if entry is not None:
        req["action"] = mt5.TRADE_ACTION_PENDING
        req["price"] = float(entry)
        pend = {
            "limit": (mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_SELL_LIMIT),
            "stop": (mt5.ORDER_TYPE_BUY_STOP, mt5.ORDER_TYPE_SELL_STOP),
        }
        req["type"] = pend[req["type"]][0 if side == "buy" else 1]
    res = mt5.order_send(req)
    if res is None:
        return {"status": "error", "detail": f"order_send None: {mt5.last_error()}", "ticket": None}
    if res.retcode == mt5.TRADE_RETCODE_DONE:
        return {"status": "executed", "ticket": res.order,
                "fill_price": res.price, "lot": use_lot}
    return {"status": "rejected", "detail": f"retcode {res.retcode}: {res.comment}", "ticket": None}


def close_all_positions() -> int:
    """Close every open position. Returns number closed."""
    if not _mt5_ensure():
        return 0
    positions = mt5.positions_get()
    if not positions:
        return 0
    n = 0
    for p in positions:
        tick = mt5.symbol_info_tick(p.symbol)
        if tick is None:
            continue
        side = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        req = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": p.ticket,
            "symbol": p.symbol,
            "volume": p.volume,
            "type": side,
            "price": tick.ask if p.type == mt5.POSITION_TYPE_BUY else tick.bid,
            "deviation": 50,
            "magic": MAGIC,
            "comment": "close_all_positions",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": _fill_type(p.symbol),
        }
        res = mt5.order_send(req)
        if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
            n += 1
    return n


# Keep run_once for backward compatibility with any callers that used it.
def run_once(signal: dict) -> dict:
    """Validate a parsed signal and return a log entry (live-mode compatible)."""
    side = signal.get("action", "buy")
    sym = signal.get("symbol", "XAUUSD")
    entry = signal.get("entry", 0.0)
    sl = signal.get("sl")
    tp = signal.get("tp", signal.get("tps"))
    volume = signal.get("volume", 0.1)
    result = execute(
        {
            "symbol": sym,
            "action": side,
            "entry": entry,
            "sl": sl,
            "tps": tp if isinstance(tp, list) else ([tp] if tp else None),
            "volume": volume,
        },
        msg_id=signal.get("msg_id"),
        lot=volume,
        channel_id=signal.get("channel_id"),
        trace_id=signal.get("trace_id"),
    )
    return {
        "msg_id": result.get("msg_id", uuid.uuid4().hex),
        "symbol": sym,
        "side": side,
        "entry": entry,
        "sl": sl,
        "tp": tp,
        "volume": volume,
        "status": result.get("status", "blocked"),
        "detail": result.get("detail", ""),
        "recorded_at": result.get("recorded_at", datetime.now(timezone.utc).isoformat()),
        "ticket": result.get("ticket"),
        "fill_price": result.get("fill_price"),
    }


if __name__ == "__main__":
    print("executor.py live module loaded")
    if _mt5_ensure():
        ti = mt5.terminal_info()
        ai = mt5.account_info()
        print(f"MT5 connected: {ti.connected if ti else False}")
        print(f"Account: {ai.login if ai else 'N/A'}, trade_allowed: {ai.trade_allowed if ai else False}")
    else:
        print("MT5 not attached")


"""neural_label_collector.py — neural training-label pipeline for the LIVE
signal-relay trade flow.

Reads/writes ONLY the data layer (signals.db) and attaches to MT5 strictly
READ-ONLY (copy_rates_*, symbol_info*, positions_get, history_deals_get,
history_orders_get). It never calls order_send/TRADE_ACTION_* — no order is
ever placed, modified or closed by this module. daemon.py / executor.py /
manage.py are NOT touched; the collector hooks the live flow as a sidecar:

  * entries  — executor.execute() already writes every filled trade to the
    `trades` table (status='executed', broker ticket). record_entry() captures
    the decision-time feature snapshot (RSI14/ATR14/session/spread/...) into
    the bridge's `neural_labels` table with outcome still NULL.
  * closes   — manage.py/MT5 close the position in their own way (SL, TP,
    BE, trail, manual). record_close() is called when the close is detected;
    it sets outcome=1 when profit_r>0 else 0.

Wiring (zero edits to the running files):
  C:/Users/voidk/miniconda3/python.exe neural_label_collector.py watch
  — polls trades+MT5, records entries, detects closes from deal history and
  computes profit_r against the ORIGINAL channel SL (R basis preserved even
  after manage.py moves the stop). Or call the two functions directly from
  any future code:

    import neural_label_collector as nlc
    nlc.record_entry(res["ticket"], sym, side, res["fill_price"], sl, tp,
                     channel_id, 20261014)
    ... when manage/MT5 report the close ...
    nlc.record_close(ticket, profit_r)

Tables (created here, additive only):
  neural_labels     — BYTE-COMPATIBLE with scalp360_bridge._ensure_schema()
                      (id, ts, symbol, side, entry, sl, tp, outcome, features)
  neural_label_map  — ticket -> label_id side table (the bridge schema has no
                      ticket column; the map is owned by this module only)

FEATURE VECTOR (25 dims, _feature_vector(), chronological rows):
   0 rsi14_norm     RSI(14) on closed M15 bars at entry /100   (0.5 unknown)
   1 atr_pct        ATR(14) M15 / entry *100                    (0.0 unknown)
   2 spread_r       spread/ATR clipped [0,2]                    (0.0 unknown)
   3 spread_missing 1.0 when spread unavailable (backfill)
   4 sl_dist_r      |entry-sl| / ATR                            (0.0 unknown)
   5 hour_norm      UTC hour / 24
   6-8   session one-hot: asia, london, ny   (UTC hour: london 07-11,
         ny 12-20, else asia)
   9-15  day-of-week one-hot Mon..Sun (gmtime)
   16-21 symbol one-hot: XAUUSD EURUSD GBPUSD USDJPY BTCUSD OTHER
   22-24 channel-policy one-hot: atr channel shadow (config signal_policy)

Protocol: scalp360/neural.evaluate() needs >=300 complete labels, trains
with purged chronological splits + embargo, calibrates on validation, and
only PROMOTEs if holdout AUC >= 0.58 AND after-cost net beats baseline.
run_evaluation() prints that honest EvalReport via the bridge.

Usage:
  python neural_label_collector.py            status: label counts (+eval at >=300)
  python neural_label_collector.py backfill   one pass over trades + MT5 history
  python neural_label_collector.py watch [s]  live sidecar loop (STOP file exits)
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

DB_PATH = os.environ.get("NEURAL_LABEL_DB", os.path.join(BASE, "signals.db"))
CONFIG_PATH = os.path.join(BASE, "config.json")
STOP_FILE = os.path.join(BASE, "STOP")

MIN_LABELS = 300           # == scalp360_bridge.BridgeConfig.neural_min_labels
HOLDOUT_AUC_MIN = 0.58     # == BridgeConfig.neural_holdout_auc_min
MAGIC_RELAY = 20261014     # executor stamps relay trades with this magic

SYMBOLS = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "BTCUSD"]
POLICY_TYPES = ["atr", "channel", "shadow"]
SESSIONS = ["asia", "london", "ny"]
FEATURE_DIM = 6 + len(SESSIONS) + 7 + (len(SYMBOLS) + 1) + len(POLICY_TYPES)  # 25

# exactly the DDL scalp360_bridge._ensure_schema() uses for this table
NEURAL_LABELS_DDL = """CREATE TABLE IF NOT EXISTS neural_labels(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, symbol TEXT,
            side TEXT, entry REAL, sl REAL, tp REAL, outcome INTEGER,
            features TEXT)"""
MAP_DDL = """CREATE TABLE IF NOT EXISTS neural_label_map(
            ticket INTEGER PRIMARY KEY, label_id INTEGER NOT NULL,
            symbol TEXT, side TEXT, opened_at REAL)"""

_mt5 = None  # lazy module handle; never imported unless market data is needed


# --------------------------------------------------------------------------
# DB helpers
# --------------------------------------------------------------------------
def _conn(db: Optional[str] = None) -> sqlite3.Connection:
    con = sqlite3.connect(db or DB_PATH, timeout=15)
    con.execute(NEURAL_LABELS_DDL)
    con.execute(MAP_DDL)
    con.commit()
    return con


def _load_config() -> Dict[str, Any]:
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def policy_type(channel_id: Optional[int]) -> str:
    """Classify a channel under config.json signal_policy: 'shadow' when its
    mode is shadow (also the _default/unknown policy), 'atr' when sl_mode=atr,
    'channel' when sl_mode=channel."""
    pol = _load_config().get("signal_policy") or {}
    p = (pol.get(str(channel_id)) if channel_id is not None else None) \
        or pol.get("_default") or {}
    if p.get("mode") == "shadow":
        return "shadow"
    if p.get("sl_mode") == "atr":
        return "atr"
    if p.get("sl_mode") == "channel":
        return "channel"
    return "shadow"


def normalize_symbol(raw: Optional[str]) -> str:
    """'xauusd', '.XAUUSD', 'XAUUSD.r', 'XAUUSDr' -> 'XAUUSD'."""
    s = (raw or "").upper().lstrip(".").split(".")[0]
    if s and s[-1] in ("R", "M") and s[:-1] in SYMBOLS:
        s = s[:-1]
    return s or "OTHER"


def session_from_hour(h_utc: int) -> str:
    """London 07-11 UTC, New York 12-20 UTC, Asia otherwise (21-06)."""
    if 7 <= h_utc < 12:
        return "london"
    if 12 <= h_utc < 21:
        return "ny"
    return "asia"


def label_counts(db: Optional[str] = None) -> Dict[str, int]:
    con = _conn(db)
    try:
        total = con.execute("SELECT COUNT(*) FROM neural_labels").fetchone()[0]
        complete = con.execute(
            "SELECT COUNT(*) FROM neural_labels WHERE outcome IS NOT NULL"
        ).fetchone()[0]
    finally:
        con.close()
    return {"total": total, "complete": complete, "pending": total - complete}


# --------------------------------------------------------------------------
# MT5 (READ-ONLY) market data
# --------------------------------------------------------------------------
def _mt5_mod():
    """Lazily import MetaTrader5; None when unavailable (tests, offline)."""
    global _mt5
    if _mt5 is None:
        try:
            import MetaTrader5 as m  # noqa: PLC0415
            from broker_lifecycle import initialize_existing
            if m.terminal_info() is None and not initialize_existing(m):
                return None
            _mt5 = m
        except Exception:  # noqa: BLE001
            return None
    return _mt5


def _rsi14(closes: Sequence[float]) -> Optional[float]:
    """Wilder RSI(14) over >=15 closes."""
    if len(closes) < 15:
        return None
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [d if d > 0 else 0.0 for d in deltas[:14]]
    losses = [-d if d < 0 else 0.0 for d in deltas[:14]]
    ag, al = sum(gains) / 14.0, sum(losses) / 14.0
    for d in deltas[14:]:
        ag = (ag * 13 + (d if d > 0 else 0.0)) / 14.0
        al = (al * 13 + (-d if d < 0 else 0.0)) / 14.0
    if al == 0:
        return 100.0 if ag > 0 else 50.0
    return 100.0 - 100.0 / (1.0 + ag / al)


def _atr14(bars) -> Optional[float]:
    """Wilder ATR(14) on CLOSED M15 bars — same math as executor._atr14."""
    if bars is None or len(bars) < 16:
        return None
    trs = []
    for i in range(1, len(bars)):
        trs.append(max(bars[i]["high"] - bars[i]["low"],
                       abs(bars[i]["high"] - bars[i - 1]["close"]),
                       abs(bars[i]["low"] - bars[i - 1]["close"])))
    a = sum(trs[:14]) / 14.0
    for tr in trs[14:]:
        a = (a * 13 + tr) / 14.0
    return a


def _bars_live(sym: str, count: int = 80):
    """Newest CLOSED M15 bars (positional fetch — immune to clock skew)."""
    m = _mt5_mod()
    if m is None:
        return None
    rates = m.copy_rates_from_pos(sym, m.TIMEFRAME_M15, 0, count + 1)
    if rates is None or len(rates) < 2:
        return None
    return list(rates[:-1])  # drop the still-forming bar


def _bars_at(sym: str, t_epoch: float, count: int = 80):
    """M15 bars whose close boundary is at or before t_epoch.
    Bar/deal epochs share one basis (verified on MetaQuotes-Demo), so the
    entry deal time selects the right bars."""
    m = _mt5_mod()
    if m is None or not t_epoch:
        return None
    # MT5 copy_rates_from returns bars opening AT OR BEFORE the anchor.
    # One extra bar covers the bar that was still forming at entry.
    rates = m.copy_rates_from(sym, m.TIMEFRAME_M15,
                              int(t_epoch), count + 1)
    if rates is None or len(rates) < 16:
        return None
    closed = [b for b in rates if b["time"] + 900 <= t_epoch]
    if len(closed) < 16:
        return None
    return closed[-count:]


def _spread_now(sym: str):
    """(spread_price, spread_points) from the live tick, or (None, None)."""
    m = _mt5_mod()
    if m is None:
        return None, None
    tick = m.symbol_info_tick(sym)
    if tick is None:
        return None, None
    sp = float(tick.ask) - float(tick.bid)
    info = m.symbol_info(sym)
    point = float(info.point) if info else 0.0
    pts = round(sp / point, 2) if point else None
    return sp, pts


def _capture_market_features(sym: str, entry_ts: Optional[float],
                            source: str = "live") -> Dict[str, Any]:
    """Single MT5 boundary of record_entry (tests patch this). Live captures
    use the newest closed bars + live spread; backfilled rows use bars frozen
    at the entry timestamp (spread honestly NULL — it is not in history)."""
    out: Dict[str, Any] = {"rsi14": None, "atr14": None, "spread": None,
                           "spread_points": None, "bars_used": 0, "basis": source}
    try:
        if source == "live":
            bars = _bars_live(sym)
            sp, pts = _spread_now(sym)
            out["spread"], out["spread_points"] = sp, pts
        else:
            bars = _bars_at(sym, entry_ts)
        if bars:
            closes = [float(b["close"]) for b in bars]
            out["rsi14"] = round(_rsi14(closes), 4) if _rsi14(closes) is not None else None
            atr = _atr14(bars)
            out["atr14"] = round(float(atr), 8) if atr is not None else None
            out["bars_used"] = len(bars)
    except Exception as e:  # noqa: BLE001 — features must never break a trade path
        out["error"] = f"{type(e).__name__}: {e}"
    return out


# --------------------------------------------------------------------------
# (1) record_entry — feature snapshot at entry time
# --------------------------------------------------------------------------
def record_entry(ticket, symbol, side, entry_price, sl, tp, channel_id, magic,
                 entry_ts: Optional[float] = None, source: str = "live",
                 db: Optional[str] = None) -> Optional[int]:
    """Capture entry-time features for `ticket` into neural_labels
    (outcome stays NULL until record_close). Idempotent per ticket.
    Returns the neural_labels row id (existing id when already recorded)."""
    try:
        ticket = int(ticket)
    except (TypeError, ValueError):
        return None
    con = _conn(db)
    try:
        row = con.execute(
            "SELECT label_id FROM neural_label_map WHERE ticket=?",
            (ticket,)).fetchone()
        if row:
            return int(row[0])
        ts = float(entry_ts) if entry_ts else time.time()
        g = time.gmtime(ts)
        mkt = _capture_market_features(symbol, ts, source)
        features = {
            "v": 1, "ticket": ticket, "magic": int(magic or 0),
            "channel_id": int(channel_id) if channel_id is not None else None,
            "policy": policy_type(channel_id),
            "symbol": symbol, "symbol_norm": normalize_symbol(symbol),
            "side": (side or "").lower(),
            "entry": float(entry_price) if entry_price is not None else None,
            "sl": float(sl) if sl else None,
            "tp": float(tp) if tp else None,
            "entry_ts": ts,
            "hour_utc": g.tm_hour, "session": session_from_hour(g.tm_hour),
            "dow": g.tm_wday,  # 0=Monday
            "rsi14": mkt["rsi14"], "atr14": mkt["atr14"],
            "spread": mkt["spread"], "spread_points": mkt["spread_points"],
            "bars_used": mkt.get("bars_used", 0), "source": source,
        }
        if "error" in mkt:
            features["capture_error"] = mkt["error"]
        with con:
            cur = con.execute(
                "INSERT INTO neural_labels(ts,symbol,side,entry,sl,tp,outcome,features)"
                " VALUES(?,?,?,?,?,?,NULL,?)",
                (ts, symbol, (side or "").lower(),
                 features["entry"], features["sl"], features["tp"],
                 json.dumps(features, sort_keys=True)))
            label_id = int(cur.lastrowid)
            con.execute(
                "INSERT INTO neural_label_map(ticket,label_id,symbol,side,opened_at)"
                " VALUES(?,?,?,?,?)", (ticket, label_id, symbol,
                                       (side or "").lower(), ts))
        # Observe only fresh entries, before any outcome can be known. Historical
        # backfills are deliberately ineligible for prospective shadow evidence.
        from neural_pipeline import shadow_observe
        shadow_observe(db or DB_PATH, label_id, _feature_vector(features))
        return label_id
    finally:
        con.close()


# --------------------------------------------------------------------------
# (2) record_close — outcome from realized R multiple
# --------------------------------------------------------------------------
def record_close(ticket, profit_r, closed_ts: Optional[float] = None,
                 db: Optional[str] = None) -> Optional[int]:
    """Called when manage.py or MT5 detects the position closed. Sets
    outcome=1 if profit_r>0 else 0. Idempotent: the first close wins, later
    calls return the recorded outcome unchanged. Returns the outcome or None
    when the ticket has no entry label."""
    try:
        ticket = int(ticket)
    except (TypeError, ValueError):
        return None
    profit_r = float(profit_r)
    if not math.isfinite(profit_r):
        raise ValueError("profit_r must be finite")
    con = _conn(db)
    try:
        # Serialize the read/update so simultaneous closes preserve first writer.
        con.execute("BEGIN IMMEDIATE")
        row = con.execute("SELECT label_id FROM neural_label_map WHERE ticket=?",
                          (ticket,)).fetchone()
        if not row:
            print(f"record_close: unknown ticket {ticket} - no entry label", flush=True)
            return None
        label_id = int(row[0])
        row = con.execute("SELECT outcome, features FROM neural_labels WHERE id=?",
                          (label_id,)).fetchone()
        if row is None:
            return None
        if row[0] is not None:  # already closed -> first close is final
            return int(row[0])
        outcome = 1 if float(profit_r) > 0 else 0
        try:
            d = json.loads(row[1] or "{}")
            if not isinstance(d, dict):
                d = {}
        except Exception:  # noqa: BLE001
            d = {}
        d["profit_r"] = round(float(profit_r), 6)
        d["closed_at"] = float(closed_ts) if closed_ts else time.time()
        with con:
            con.execute("UPDATE neural_labels SET outcome=?, features=? WHERE id=?",
                        (outcome, json.dumps(d, sort_keys=True), label_id))
        return outcome
    finally:
        con.close()


# --------------------------------------------------------------------------
# (3) get_training_data — (X, y) for scalp360/neural.evaluate()
# --------------------------------------------------------------------------
def _feature_vector(f: Dict[str, Any]) -> Tuple[float, ...]:
    """features JSON -> fixed 25-dim float row (layout in module docstring)."""
    rsi, atr = f.get("rsi14"), f.get("atr14")
    entry, sl, spread = f.get("entry"), f.get("sl"), f.get("spread")
    num = lambda x: isinstance(x, (int, float))  # noqa: E731
    rsi_norm = rsi / 100.0 if num(rsi) else 0.5
    atr_pct = (float(atr) / float(entry) * 100.0) if (num(atr) and num(entry) and entry > 0) else 0.0
    if num(spread) and num(atr) and atr > 0:
        spread_r = min(max(float(spread) / float(atr), 0.0), 2.0)
        spread_missing = 0.0
    else:
        spread_r, spread_missing = 0.0, 1.0
    sl_dist_r = (abs(float(entry) - float(sl)) / float(atr)
                 if (num(entry) and num(sl) and num(atr) and atr > 0) else 0.0)
    hour = f.get("hour_utc")
    hour_norm = float(hour) / 24.0 if num(hour) else 0.0
    sess = f.get("session") or "asia"
    v = [rsi_norm, atr_pct, spread_r, spread_missing, sl_dist_r, hour_norm]
    v += [1.0 if sess == s else 0.0 for s in SESSIONS]
    dow = f.get("dow")
    v += [1.0 if (num(dow) and int(dow) == i) else 0.0 for i in range(7)]
    sn = f.get("symbol_norm") or "OTHER"
    v += [1.0 if sn == s else 0.0 for s in SYMBOLS]
    v += [0.0] if sn in SYMBOLS else [1.0]          # OTHER bucket
    pt = f.get("policy") or "shadow"
    v += [1.0 if pt == p else 0.0 for p in POLICY_TYPES]
    return tuple(v)


def get_training_data(db: Optional[str] = None
                      ) -> Tuple[List[Tuple[float, ...]], List[int]]:
    """Only fresh broker-verified, unchanged, independent executed outcomes."""
    from neural_pipeline import connect, verified_rows
    with connect(db or DB_PATH) as con:
        rows = verified_rows(con)
    return [r['x'] for r in rows], [r['y'] for r in rows]


# --------------------------------------------------------------------------
# (4) run_evaluation — honest protocol via the bridge
# --------------------------------------------------------------------------
def run_evaluation(db_path: Optional[str] = None):
    """make_bridge().neural_evaluate(X, y) and print the EvalReport.
    The harness itself refuses to train below MIN_LABELS (300)."""
    dbp = db_path or DB_PATH
    from scalp360_bridge import make_bridge  # lazy: heavy import, MT5-free
    X, y = get_training_data(dbp)
    print(f"training rows with outcome: {len(X)} (gate {MIN_LABELS})", flush=True)
    if len(X) < MIN_LABELS:
        print(f"REJECT: insufficient labels ({len(X)} < {MIN_LABELS}) "
              f"- evaluation refused", flush=True)
    bridge = make_bridge(dbp)
    rep = bridge.neural_evaluate(X, y)
    print("== neural EvalReport (scalp360 honest protocol) ==", flush=True)
    print(f"  n_train={rep.n_train}  n_val={rep.n_val}  n_test={rep.n_test}", flush=True)
    print(f"  holdout_auc={rep.holdout_auc}  (PROMOTE gate >= {HOLDOUT_AUC_MIN})",
          flush=True)
    print(f"  baseline_winrate={rep.baseline_winrate}  model_winrate={rep.model_winrate}",
          flush=True)
    print(f"  net_after_cost  baseline={rep.net_after_cost_baseline}  "
          f"model={rep.net_after_cost_model}", flush=True)
    print(f"  DECISION: {rep.decision}", flush=True)
    return rep


# --------------------------------------------------------------------------
# live-flow hook: sidecar reconciliation (trades table + MT5 history)
# --------------------------------------------------------------------------
def _msg_channel(msg_id: Optional[str]) -> Optional[int]:
    """daemon writes trades.msg_id as '<chat_id>:<orig>' — recover channel."""
    s = str(msg_id or "")
    if ":" in s:
        head = s.split(":", 1)[0]
        try:
            return int(head)
        except ValueError:
            return None
    return None


def _pick_tp(tp_json: Optional[str], side: str) -> Optional[float]:
    """Mirror executor._pick_tp over the JSON tp list stored in trades."""
    try:
        tps = json.loads(tp_json or "[]")
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(tps, list) or not tps:
        return None
    return float(tps[-1] if (side or "").lower() == "sell" else tps[0])


def _position_state(ticket: int):
    """(is_open, entry_price, magic, open_time, volume_in, entry_deals)."""
    m = _mt5_mod()
    if m is None:
        return None
    for p in m.positions_get() or []:
        if int(p.ticket) == ticket:
            return (True, float(p.price_open), int(p.magic), float(p.time),
                    float(p.volume), [])
    deals = m.history_deals_get(position=ticket) or []
    ins = [d for d in deals if int(getattr(d, "entry", 0)) == 0]  # DEAL_ENTRY_IN
    if not ins:
        return (False, None, MAGIC_RELAY, None, None, deals)
    d0 = ins[0]
    return (False, float(d0.price), int(getattr(d0, "magic", MAGIC_RELAY) or MAGIC_RELAY),
            float(d0.time), float(d0.volume), deals)


def _profit_r(symbol: str, deals, entry_price, sl, volume_in) -> Optional[float]:
    """Realized R multiple: net money (profit+commission+swap over ALL deals
    of the position) / money risk of the ORIGINAL SL distance."""
    if not deals or entry_price is None or not sl or not volume_in:
        return None
    m = _mt5_mod()
    info = m.symbol_info(symbol) if m else None
    if info is None:
        return None
    tick_size = float(getattr(info, "trade_tick_size", 0) or getattr(info, "point", 0) or 0)
    tick_value = float(getattr(info, "trade_tick_value", 0) or 0)
    if tick_size <= 0 or tick_value <= 0:
        return None
    risk_money = abs(float(entry_price) - float(sl)) / tick_size * tick_value * float(volume_in)
    if risk_money <= 0:
        return None
    net = sum(float(d.profit) + float(d.commission) + float(d.swap) for d in deals)
    return net / risk_money


def backfill_once(db: Optional[str] = None) -> Dict[str, int]:
    """One reconciliation pass over the live trade flow (read-only MT5):
    record entries for executed trades not yet labeled, and close labels for
    tickets whose position fully exited. Returns counters."""
    con = _conn(db)
    try:
        rows = con.execute(
            "SELECT ticket, msg_id, ts, symbol, side, lot, sl, tp"
            " FROM trades WHERE status='executed' AND ticket IS NOT NULL"
            " AND ticket!=0 ORDER BY id DESC LIMIT 500").fetchall()
        mapped = {int(r[0]) for r in con.execute("SELECT ticket FROM neural_label_map")}
        open_outcomes = {int(r[0]) for r in con.execute(
            "SELECT m.ticket FROM neural_label_map m JOIN neural_labels l"
            " ON m.label_id=l.id WHERE l.outcome IS NULL")}
    finally:
        con.close()
    stats = {"entries": 0, "closes": 0, "errors": 0}
    m = _mt5_mod()
    live_tickets = None
    if m is not None:
        positions = m.positions_get()
        if positions is not None:  # None = API error, not 'no positions'
            live_tickets = {int(p.ticket) for p in positions}
    for ticket, msg_id, ts, symbol, side, lot, sl, tp in rows:
        try:
            ticket = int(ticket)
            if ticket not in mapped:
                st = _position_state(ticket)
                if st is None or st[1] is None:
                    continue  # MT5 offline or no history yet
                _, entry_price, magic, open_time, _, _ = st
                label_id = record_entry(
                    ticket, symbol, side, entry_price, sl,
                    _pick_tp(tp, side), _msg_channel(msg_id), magic,
                    entry_ts=open_time, source="watch", db=db)
                if label_id is not None:
                    mapped.add(ticket)
                    stats["entries"] += 1
                    print(f"entry label #{label_id}: ticket {ticket} {side} {symbol}",
                          flush=True)
                continue
            if ticket in open_outcomes and live_tickets is not None \
                    and ticket not in live_tickets:
                st = _position_state(ticket)
                if st is None:
                    continue
                _, entry_price, magic, _, volume_in, deals = st
                outs = [d for d in deals if int(getattr(d, "entry", 0)) in (1, 2)]
                vol_out = sum(float(d.volume) for d in outs)
                if not deals or (volume_in and vol_out < volume_in - 1e-9):
                    continue  # history lag or partial close -> wait
                pr = _profit_r(symbol, deals, entry_price, sl, volume_in)
                if pr is None:
                    stats["errors"] += 1
                    print(f"close label skipped: ticket {ticket} - no SL R basis",
                          flush=True)
                    continue
                closed_at = max(float(d.time) for d in deals)
                outcome = record_close(ticket, pr, closed_ts=closed_at, db=db)
                if outcome is not None:
                    stats["closes"] += 1
                    open_outcomes.discard(ticket)
                    print(f"close label: ticket {ticket} profit_r={pr:+.4f}"
                          f" -> outcome {outcome}", flush=True)
        except Exception as e:  # noqa: BLE001 — one bad row must not stop the pass
            stats["errors"] += 1
            print(f"backfill error ticket {ticket}: {type(e).__name__}: {e}",
                  flush=True)
    return stats


def evaluate_collection_gate(db_path=None):
    """Persist diagnostic evaluation; never authorize unverified training rows.

    Rows without an executed-trade audit trail need independent provenance
    review before promotion. This deliberately does not mutate live entry rules.
    """
    from dataclasses import asdict
    dbp = db_path or DB_PATH
    report = asdict(run_evaluation(dbp))
    from neural_pipeline import connect, verified_rows
    con = connect(dbp)
    try:
        verified = len(verified_rows(con))
    finally:
        con.close()
    report.update(cost_per_trade=0.0, scoring='binary win/loss',
                  verified_executed_labels=verified,
                  evaluated_at=time.time(), shadow_model_activated=False,
                  limitations=[
                      'purged_splits exists but evaluate does not invoke it',
                      'validation threshold is selected before fitting again on full training slice',
                      'binary win/loss net is not realized cash or R-multiple net'])
    report['evaluation_decision'] = report['decision']
    if verified < MIN_LABELS:
        report['decision'] = 'CONTINUE'
        report['promotion_blocker'] = (
            f'Only {verified} labels match executed trades; remaining labels '
            'require provenance review. Diagnostic metrics cannot authorize promotion.')
    elif report['decision'] == 'PROMOTE':
        # Fail closed: no live entry consumer/model activation contract exists here.
        report['decision'] = 'KEEP_SHADOW'
        report['promotion_blocker'] = 'Shadow inference consumer not wired; activation requires integration.'
    elif report['decision'].startswith('REJECT'):
        report['decision'] = 'CONTINUE'
    path = dbp + '.neural_eval.json'
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
    os.replace(tmp, path)
    print('COLLECTION_GATE ' + json.dumps(report, sort_keys=True), flush=True)
    return report


def watch(interval_s: float = 5.0) -> None:
    """Live sidecar loop — the zero-edit hook into the trade flow. Honors the
    STOP file (like manage.py); every pass is MT5-read-only."""
    print(f"neural_label_collector watch: every {interval_s:.0f}s "
          f"(STOP file or Ctrl+C to exit)", flush=True)
    last_evaluated = None
    last_progress = 0.0
    while not os.path.exists(STOP_FILE):
        try:
            stats = backfill_once()
            counts = label_counts()
            if time.monotonic() - last_progress >= 60 or stats['entries'] or stats['closes']:
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] progress {counts}", flush=True)
                last_progress = time.monotonic()
            # Reconcile broker evidence every pass; retraining has its own durable
            # 100-verified-trade watermark, including across process restarts.
            from neural_pipeline import tick
            tick(DB_PATH, _mt5_mod(), os.environ.get('NEURAL_MLFLOW_TRACKING_URI'))
            if counts['complete'] >= MIN_LABELS and counts['complete'] != last_evaluated:
                evaluate_collection_gate()
                last_evaluated = counts['complete']
            if stats["entries"] or stats["closes"] or stats["errors"]:
                print(f"[{time.strftime('%H:%M:%S')}] entries={stats['entries']} "
                      f"closes={stats['closes']} errors={stats['errors']}",
                      flush=True)
        except Exception as e:  # noqa: BLE001
            print("watch pass error:", type(e).__name__, e, flush=True)
        for _ in range(max(1, int(interval_s))):
            if os.path.exists(STOP_FILE):
                break
            time.sleep(1)
    print("watch stopped (STOP file).", flush=True)


# --------------------------------------------------------------------------
# (5) standalone main
# --------------------------------------------------------------------------
def main(argv: Optional[Sequence[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv[0] if argv else "status"
    if cmd == "watch":
        interval = float(argv[1]) if len(argv) > 1 else 5.0
        watch(interval)
        return 0
    if cmd == "backfill":
        stats = backfill_once()
        print(f"backfill: entries={stats['entries']} closes={stats['closes']} "
              f"errors={stats['errors']}", flush=True)
    elif cmd not in ("status",):
        print(f"usage: {os.path.basename(__file__)} [status|backfill|watch [secs]]",
              flush=True)
        return 2
    counts = label_counts()
    print(f"neural labels: {counts['complete']} complete / {counts['total']} "
          f"recorded ({counts['pending']} pending close)", flush=True)
    if counts["complete"] >= MIN_LABELS:
        run_evaluation()
        return 0
    print(f"evaluation deferred: need {MIN_LABELS - counts['complete']} more "
          f"complete labels (gate {MIN_LABELS}, holdout AUC gate {HOLDOUT_AUC_MIN})",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

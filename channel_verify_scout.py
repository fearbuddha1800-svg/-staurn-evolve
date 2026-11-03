"""SCOUT-VERIFICATION engine (READ-ONLY): expedited V2 exit-geometry check of
the 3 scout-verified gold channels the user is watching live.

Faithful port of the proven V2 engine (channel_verify2.py / method spec in
agent-reports/exit-geometry.md): channel DIRECTION + OUR trailing exits.

Per channel (last ~300 messages, current fixed parser.py):
  - same keep-filter as V1/V2: parse_ok, non-manage, has SL, >=1 TP, numeric
    entry, not stale (>1% from price at signal time)
  - variant A: initial SL = the channel's stated SL (R = |entry - SL|)
  - variant B: initial SL = 2 x ATR(14) (Wilder, M15, strictly closed bars
    before the entry bar; stated SL ignored)
  - ALL channel TPs ignored; exit management = manage.py rules from
    config.json: SL -> entry +/- 10pt buffer at +1R favorable, from +1.5R
    trails 0.5R behind best favorable price (ratchet-only)
  - market entry at the open of the first M15 bar at/after signal time
  - 48h walk; conservative same-bar rule (stop as of bar open checked FIRST)
  - 0.07R round-trip cost haircut per trade
  - verdict bands on expectancy after costs: >= +0.05R POSITIVE EDGE,
    <= -0.05R NEGATIVE, else FLAT; n < 8 resolved = INSUFFICIENT (tentative)
  - per-channel call: PROMOTE to trading policy (winning variant + params)
    or STAY SHADOW

Safety (same guarantees as V2):
  - telethon.session is NEVER touched: a sqlite-backup copy is made to
    telethon-scout-verify.session BEFORE connecting, and only the copy is used
  - MT5 strictly read-only: initialize/shutdown + market-data reads only
    (copy_rates_range / symbol_info / symbol_info_tick / symbol_select);
    NEVER order_send, never positions_get, no trades
  - no existing file is edited; creates only: channel_verify_scout.py (this
    file, already on disk), telethon-scout-verify.session (+ -journal),
    scout-verification.json, agent-reports/scout-verification.md
"""
from broker_lifecycle import initialize_existing, broker_status
import asyncio
import json
import os
import shutil
import sqlite3
import sys
import time
from bisect import bisect_left, bisect_right
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
sys.dont_write_bytecode = True  # never touch __pycache__
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import MetaTrader5 as mt5  # noqa: E402
import daemon  # noqa: E402  (for daemon._env_creds())
import parser as sigparser  # noqa: E402  (the relay's own parser, JUST FIXED)
from executor import resolve_symbol  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

LIVE_SESSION = os.path.join(BASE, "telethon.session")             # NEVER touched
SESSION = os.path.join(BASE, "telethon-scout-verify.session")     # our private copy
REPORT = os.path.join(BASE, "scout-verification.json")
REPORT_MD = os.path.join(BASE, "agent-reports", "scout-verification.md")

with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
    CFG = json.load(f)
_M = CFG.get("manage") or {}
BE_AT_R = float(_M.get("be_at_r", 1.0))            # 1.0
TRAIL_FROM_R = float(_M.get("trail_from_r", 1.5))  # 1.5
TRAIL_DIST_R = float(_M.get("trail_dist_r", 0.5))  # 0.5
BE_BUF_PTS = int(_M.get("be_buffer_points", 10))    # manage.py default

# the 3 scout-verified channels (task spec); plain names for readable tables
CHANNELS = [
    (-1001207746934, "XAUHQ", "t.me/Goldsignals"),
    (-1001588519179, "SureShotFX free gold", "t.me/ssfgold"),
    (-1001868019139, "Gold Signals VIP", "t.me/gold_forex_signals_vip"),
]
FALLBACK_NAMES = {cid: name for cid, name, _u in CHANNELS}
USERNAMES = {cid: uname for cid, _n, uname in CHANNELS}

MSG_LIMIT = 300             # last ~300 messages per channel (same as V2)
LOOKBACK_S = 7 * 24 * 3600  # bars before signal: ATR warmup (Wilder converges)
FORWARD_S = 120 * 3600      # 48h walk + weekend-gap headroom
HORIZON_S = 48 * 3600       # trade must resolve within 48h from entry
M15 = 900
STALE_FRAC = 0.01           # >1% away from price at signal time = stale re-post
MIN_SAMPLE = 8              # task gate: >= 8 complete signals for a valid call
COST_R = 0.07               # round-trip cost haircut per trade (V1/V2/backtest.py)
RECAP_PATTERNS = ("tp hit", "pips")
OFFSET_SYMBOLS = ("XAUUSD", "EURUSD", "GBPUSD", "US30", "XAGUSD", "AUDUSD")
ATR_PERIOD = 14
ATR_SL_MULT = 2.0           # variant B: SL = 2 x ATR(14)
VARIANTS = ("A", "B")
EXP_BAND = 0.05             # |expectancy after costs| < 0.05R -> FLAT

# prior evidence from the full sweep (channel_verify3.py, OLD parser, 200-msg
# window) - cited for context only; this run supersedes it with the fixed parser
PRIOR = {
    -1001207746934: "full-sweep (old parser, 200 msgs): 0 complete signals - not verified",
    -1001588519179: "full-sweep (old parser, 200 msgs): NEGATIVE - best variant B -0.112R over 26 trades",
    -1001868019139: "full-sweep (old parser, 200 msgs): POSITIVE EDGE - variant B +0.124R over 25 trades",
}

_selected_symbols = set()  # symbols we had to symbol_select() for data access
_point_cache = {}          # symbol -> point (for the BE buffer)


# ---------------------------------------------------------------- session copy
def copy_session():
    """Copy telethon.session -> telethon-scout-verify.session WITHOUT touching
    or contending the live session: prefer the sqlite backup API (lock-safe),
    fall back to a read-only file copy. The -journal is copied too if present.
    The live session file is only ever OPENED READ-ONLY, never connected."""
    for junk in (SESSION, SESSION + "-journal"):
        if os.path.exists(junk):
            os.remove(junk)  # only ever removes OUR research copies
    try:
        src = sqlite3.connect(f"file:{LIVE_SESSION}?mode=ro", uri=True, timeout=10)
        dst = sqlite3.connect(SESSION)
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
    except Exception as e:  # noqa: BLE001
        print(f"sqlite backup fell back to file copy ({type(e).__name__}: {e})")
        shutil.copy2(LIVE_SESSION, SESSION)
    j = LIVE_SESSION + "-journal"
    if os.path.exists(j):
        shutil.copy2(j, SESSION + "-journal")
    print(f"scout-verify session copy ready: {SESSION} ({os.path.getsize(SESSION)} bytes)")


# ------------------------------------------------------------------ mt5 helpers
def compute_server_offset():
    """MT5 server-time offset, V2 method: server epochs are real epoch +
    offset for every symbol, so the FRESHEST tick across liquid symbols is
    the correct estimator (XAUUSD's demo feed can be frozen)."""
    now = time.time()
    per_symbol = {}
    for s in OFFSET_SYMBOLS:
        t = mt5.symbol_info_tick(s)
        if t is not None:
            per_symbol[s] = int(t.time)
    if not per_symbol:
        raise RuntimeError("no ticks available to compute server offset")
    freshest = max(per_symbol.values())
    offset = freshest - now
    if not (0 < offset < 6 * 3600):
        raise RuntimeError(f"implausible server offset {offset}s")
    xau = per_symbol.get("XAUUSD")
    print(f"server offset: {offset:.0f}s ({offset/3600:.2f}h ahead of UTC), "
          f"source: freshest tick of {len(per_symbol)} symbols")
    if xau is not None and xau < freshest - 60:
        print(f"  note: XAUUSD tick was STALE by {freshest - xau}s "
              "(demo feed frozen) - freshest symbol used instead")
    return offset, per_symbol


def get_bars(sym, t_from, t_to):
    """M15 bars in server-epoch window [t_from, t_to), or None."""
    r = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M15, int(t_from), int(t_to))
    if (r is None or len(r) == 0) and sym not in _selected_symbols:
        # symbol known to broker but not visible: select it (executor does the
        # same pre-trade; this is market-watch state, NOT a trade)
        if mt5.symbol_info(sym) is None:
            mt5.symbol_select(sym, True)
            _selected_symbols.add(sym)
            r = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M15, int(t_from), int(t_to))
    return r


def be_buffer(sym):
    """Break-even buffer in PRICE units: be_buffer_points * point (manage.py).
    Falls back to 0.0 (exact BE) if symbol info is unavailable."""
    if sym in _point_cache:
        pt = _point_cache[sym]
    else:
        info = mt5.symbol_info(sym)
        pt = float(info.point) if (info is not None and info.point) else None
        _point_cache[sym] = pt
    return (BE_BUF_PTS * pt) if pt else 0.0


def to_utc_epoch(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # telethon returns UTC
    return dt.timestamp()


def wilder_atr(bars, upto, period=ATR_PERIOD):
    """Wilder ATR(period) over the CLOSED bars strictly before index `upto`
    (the entry bar is still open at entry time, so it is excluded). Seed =
    SMA of the first `period` true ranges, then Wilder smoothing. None when
    there is not enough history."""
    if upto < period + 1:
        return None
    trs = []
    atr = None
    for i in range(1, upto):
        h, l = float(bars[i]["high"]), float(bars[i]["low"])
        pc = float(bars[i - 1]["close"])
        tr = max(h - l, abs(h - pc), abs(l - pc))
        if atr is None:
            trs.append(tr)
            if len(trs) == period:
                atr = sum(trs) / period
        else:
            atr = (atr * (period - 1) + tr) / period
    return atr


# --------------------------------------------------------------- policy v2 sim
def simulate_v2(bars, tarr, k, side, entry, sl_init, r_init, buf):
    """Walk M15 bars from entry bar k under POLICY V2.

    The stop as it stood at BAR OPEN is checked first (conservative same-bar
    rule: SL before trail-advance); only if it survives may this bar's
    favorable extreme advance BE/trail, and the new level applies from the
    NEXT bar. BE/trail levels are ratchet-only (never widen). Exits at a stop
    fill at the stop level (no-slippage convention, same as V1/V2).

    Returns (label, r, exit_price, exit_srv_epoch) with label in
    {"sl", "be", "trail", "timeout", "pending"}."""
    is_buy = side == "buy"
    sl = sl_init
    label = "sl"        # which level closed the trade (initial stop so far)
    best = entry        # best favorable price seen so far
    be_done = False
    horizon = int(tarr[k]) + HORIZON_S  # 48h from simulated entry
    end = k
    for idx in range(k, len(tarr)):
        if tarr[idx] >= horizon:
            break
        end = idx
        hi, lo = float(bars[idx]["high"]), float(bars[idx]["low"])
        # 1) stop AS OF BAR OPEN (SL before trail-advance)
        if (is_buy and lo <= sl) or ((not is_buy) and hi >= sl):
            r = ((sl - entry) if is_buy else (entry - sl)) / r_init
            return label, r, sl, int(tarr[idx])
        # 2) advance best / BE / trail from this bar's favorable extreme
        fav = hi if is_buy else lo
        best = max(best, fav) if is_buy else min(best, fav)
        moved = (best - entry) if is_buy else (entry - best)  # favorable excursion
        if not be_done and moved >= BE_AT_R * r_init:
            cand = (entry + buf) if is_buy else (entry - buf)
            if (is_buy and cand > sl) or ((not is_buy) and cand < sl):
                sl, label, be_done = cand, "be", True
        if moved >= TRAIL_FROM_R * r_init:
            cand = (best - TRAIL_DIST_R * r_init) if is_buy else (best + TRAIL_DIST_R * r_init)
            if (is_buy and cand > sl) or ((not is_buy) and cand < sl):
                sl, label = cand, "trail"
    if tarr[-1] < horizon:
        return "pending", None, None, None
    exit_px = float(bars[end]["close"])
    pr = ((exit_px - entry) if is_buy else (entry - exit_px)) / r_init
    return "timeout", pr, exit_px, int(tarr[end]) + M15


# ---------------------------------------------------------------- channel pass
def new_channel_state(cid, fallback_name):
    return {
        "id": cid, "name": fallback_name, "plain_name": fallback_name,
        "username": USERNAMES.get(cid),
        "messages": 0, "media_only": 0, "not_signal": 0, "unparseable": 0,
        "unverifiable": 0, "recap_posts": 0, "no_data": 0, "pending": 0,
        "degenerate": 0, "stale": 0, "error": None, "signals": [],
        "variants": {
            v: {"trades": 0, "wins": 0, "losses": 0, "win_pct": None,
                "net_r": None, "avg_r": None, "expectancy_after_costs_r": None,
                "max_dd_r": None, "verdict": None, "pending": 0, "no_atr": 0,
                "classes": {"sl": 0, "be": 0, "trail": 0, "timeout": 0},
                "r_list": [], "ordered": []}
            for v in VARIANTS
        },
    }


def tally(st, v, res, entry_epoch):
    d = st["variants"][v]
    label, r, _px, _t = res
    if label == "pending":
        d["pending"] += 1
    elif label == "no_atr_history":
        d["no_atr"] += 1
    else:
        d["r_list"].append(r)
        d["ordered"].append((entry_epoch, r))
        d["classes"][label] = d["classes"].get(label, 0) + 1


def pack_variant(init_sl, r_init, res):
    label, r, px, t = res
    d = {"init_sl": round(init_sl, 5) if init_sl is not None else None,
         "r_init": round(r_init, 5) if r_init else None,
         "outcome": label}
    if r is not None:
        d["r"] = round(r, 3)
    if px is not None:
        d["exit"] = round(px, 5)
    if t is not None:
        d["exit_time_server"] = (datetime.fromtimestamp(t, tz=timezone.utc)
                                  .replace(tzinfo=None).isoformat() + "+srv")
    return d


def safe_resolve_symbol(raw):
    """resolve_symbol() without the fatal fallback: this MetaTrader5 package
    build has no mt5.symbol_search, and channels with text-artifact 'symbols'
    (GROWTH/STRONG/... - 6-letter words that look like pairs) would otherwise
    raise AttributeError and abort the whole channel pass. Unresolvable
    symbols -> None -> honest 'no_symbol_on_broker' funnel count."""
    try:
        return resolve_symbol(raw)
    except Exception:  # noqa: BLE001
        return None


async def analyze_channel(client, cid, fallback_name, offset):
    st = new_channel_state(cid, fallback_name)
    try:
        try:
            ent = await client.get_entity(cid)
            title = getattr(ent, "title", None) or fallback_name
            uname = getattr(ent, "username", None)
            if uname:
                st["username"] = uname
        except Exception:  # noqa: BLE001
            title = fallback_name
        st["name"] = title

        async for m in client.iter_messages(int(cid), limit=MSG_LIMIT):
            st["messages"] += 1
            text = (m.message or "").strip()
            if not text:
                st["media_only"] += 1
                continue
            low = text.lower()
            if any(p in low for p in RECAP_PATTERNS):
                st["recap_posts"] += 1  # result language: count, never simulate
                continue
            parsed = sigparser.parse_signal(text)
            if not parsed.get("parse_ok"):
                st["unparseable" if parsed.get("is_signal") else "not_signal"] += 1
                continue
            if parsed.get("action") not in ("buy", "sell"):  # non-manage guard
                continue
            sl = parsed.get("sl")
            tps = parsed.get("tps") or []
            entry = parsed.get("entry")
            if sl is None or not tps or not isinstance(entry, float):
                st["unverifiable"] += 1
                continue

            utc_ep = to_utc_epoch(m.date)
            if utc_ep is None:
                st["unverifiable"] += 1
                continue
            sig_srv = utc_ep + offset
            raw_sym = parsed.get("symbol")
            sym = safe_resolve_symbol(raw_sym)
            rec = {"msg_id": m.id,
                   "date_utc": (m.date.replace(tzinfo=timezone.utc).isoformat()
                                if m.date.tzinfo is None else m.date.isoformat()),
                   "raw_symbol": raw_sym, "resolved": sym,
                   "side": parsed["action"], "entry": entry, "sl": sl,
                   "tps": tps}
            if not sym:
                st["no_data"] += 1
                rec["outcome"] = "no_symbol_on_broker"
                st["signals"].append(rec)
                continue
            bars = get_bars(sym, sig_srv - LOOKBACK_S, sig_srv + FORWARD_S)
            if bars is None or len(bars) == 0:
                st["no_data"] += 1
                rec["outcome"] = "no_price_data"
                st["signals"].append(rec)
                continue
            tarr = bars["time"]

            # market price at signal time: open of the bar COVERING the signal,
            # else close of the last bar before it (market was closed)
            j = bisect_right(tarr, sig_srv) - 1
            if j < 0:
                st["no_data"] += 1
                rec["outcome"] = "no_price_data"
                st["signals"].append(rec)
                continue
            covering = int(tarr[j]) + M15 > sig_srv
            ref_price = float(bars[j]["open"]) if covering else float(bars[j]["close"])
            rec["price_at_signal"] = round(ref_price, 5)
            rec["entry_gap_pct"] = round(abs(entry - ref_price) / ref_price * 100, 3)

            if rec["entry_gap_pct"] > STALE_FRAC * 100:
                st["stale"] += 1
                rec["outcome"] = "stale_repost"
                st["signals"].append(rec)
                continue

            # market entry at the first bar OPENING at/after signal time
            k = bisect_left(tarr, sig_srv)
            if k >= len(tarr):
                st["pending"] += 1
                rec["outcome"] = "pending_no_bar_yet"
                st["signals"].append(rec)
                continue
            sim_entry = float(bars[k]["open"])
            side = parsed["action"]

            # ---- variant A: initial SL = the channel's stated SL -----------
            r_a = abs(sim_entry - sl)
            if r_a <= 0:
                st["degenerate"] += 1
                rec["outcome"] = "degenerate_sl_eq_entry"
                st["signals"].append(rec)
                continue
            rec["sim_entry"] = round(sim_entry, 5)
            buf = be_buffer(sym)
            res_a = simulate_v2(bars, tarr, k, side, sim_entry, sl, r_a, buf)
            rec["variants"] = {"A": pack_variant(sl, r_a, res_a)}
            tally(st, "A", res_a, int(tarr[k]))

            # ---- variant B: initial SL = 2 x ATR(14) at entry --------------
            # (channel SL ignored entirely; ATR from strictly closed bars)
            atr = wilder_atr(bars, k)
            rec["atr14_m15"] = round(atr, 5) if atr else None
            if not atr or atr <= 0:
                res_b = ("no_atr_history", None, None, None)
                rec["variants"]["B"] = pack_variant(None, None, res_b)
            else:
                r_b = ATR_SL_MULT * atr
                sl_b = (sim_entry - r_b) if side == "buy" else (sim_entry + r_b)
                res_b = simulate_v2(bars, tarr, k, side, sim_entry, sl_b, r_b, buf)
                rec["variants"]["B"] = pack_variant(sl_b, r_b, res_b)
            tally(st, "B", res_b, int(tarr[k]))
            st["signals"].append(rec)
    except Exception as e:  # noqa: BLE001
        st["error"] = f"{type(e).__name__}: {e}"
    return st


# -------------------------------------------------------------------- statistics
def max_dd(series):
    peak = cum = dd = 0.0
    for x in series:
        cum += x
        if cum > peak:
            peak = cum
        if peak - cum > dd:
            dd = peak - cum
    return dd


def verdict_for(n, exp):
    if not n:
        return "INSUFFICIENT DATA: 0 resolved trades"
    tag = ("POSITIVE EDGE" if exp >= EXP_BAND
           else "NEGATIVE" if exp <= -EXP_BAND else "FLAT")
    if n < MIN_SAMPLE:
        return f"INSUFFICIENT DATA (n={n} < {MIN_SAMPLE}) - tentatively {tag}"
    return tag


def finalize_variant(d):
    rs = d.pop("r_list")
    ordered = d.pop("ordered")
    n = len(rs)
    d["trades"] = n
    d["wins"] = sum(1 for r in rs if r > 0)
    d["losses"] = n - d["wins"]
    d["win_pct"] = round(100.0 * d["wins"] / n, 1) if n else None
    d["net_r"] = round(sum(rs), 2) if n else None
    d["avg_r"] = round(sum(rs) / n, 3) if n else None
    d["expectancy_after_costs_r"] = (round(d["avg_r"] - COST_R, 3)
                                     if d["avg_r"] is not None else None)
    if n:
        ordered.sort(key=lambda x: x[0])  # chronological by entry epoch
        d["max_dd_r"] = round(max_dd([r - COST_R for _, r in ordered]), 2)
    else:
        d.setdefault("max_dd_r", None)
    d["verdict"] = verdict_for(n, d["expectancy_after_costs_r"])
    return d


# ----------------------------------------------------------------- promote call
def policy_params(variant):
    """signal_policy params (config.json schema) for the winning variant."""
    p = ({"sl_mode": "channel"} if variant == "A"
         else {"sl_mode": "atr", "atr_mult": ATR_SL_MULT})
    p["tp_mode"] = "none"  # all channel TPs ignored; manage.py trailing exits
    return p


def recommend_channel(st):
    """Explicit per-channel call: PROMOTE (winning variant + params) or
    STAY SHADOW. PROMOTE requires >= MIN_SAMPLE resolved trades and
    expectancy after costs >= +EXP_BAND on the best adequately-sampled
    variant."""
    adequates = {v: st["variants"][v] for v in VARIANTS
                 if st["variants"][v]["trades"] >= MIN_SAMPLE
                 and st["variants"][v]["expectancy_after_costs_r"] is not None}
    if not adequates:
        best_v = max(VARIANTS, key=lambda v: st["variants"][v]["trades"])
        d = st["variants"][best_v]
        return {"call": "STAY SHADOW", "winning_variant": None,
                "params": None, "reason":
                f"fewer than {MIN_SAMPLE} resolved trades in both variants "
                f"(A n={st['variants']['A']['trades']}, B n={st['variants']['B']['trades']}) "
                "- sample too small to promote"}
    best_v = max(adequates, key=lambda v: adequates[v]["expectancy_after_costs_r"])
    d = adequates[best_v]
    if d["expectancy_after_costs_r"] >= EXP_BAND:
        return {"call": "PROMOTE", "winning_variant": best_v,
                "params": policy_params(best_v),
                "exp_after_costs_r": d["expectancy_after_costs_r"],
                "trades": d["trades"], "win_pct": d["win_pct"],
                "max_dd_r": d["max_dd_r"],
                "reason": f"variant {best_v} clears the bar: "
                          f"{d['expectancy_after_costs_r']:+.3f}R expectancy after "
                          f"costs over {d['trades']} resolved trades "
                          f"(win% {d['win_pct']}, maxDD {d['max_dd_r']}R)"}
    other = st["variants"]["B" if best_v == "A" else "A"]
    return {"call": "STAY SHADOW", "winning_variant": best_v, "params": None,
            "exp_after_costs_r": d["expectancy_after_costs_r"],
            "trades": d["trades"],
            "reason": f"best variant {best_v} is "
                      f"{d['expectancy_after_costs_r']:+.3f}R after costs over "
                      f"{d['trades']} trades - does not clear +{EXP_BAND}R "
                      f"(other variant A n={other['trades']} "
                      f"exp {other['expectancy_after_costs_r']})"}


# ------------------------------------------------------------------ reporting
def fmt(x, spec=None, dash="-"):
    if x is None:
        return dash
    if spec is None:
        return str(x)
    return format(x, spec)


def console_table(results, pooled):
    hdr = (f"{'channel':<24}{'var':>4}{'trades':>7}{'win%':>7}{'avgR':>8}"
           f"{'expCost':>8}{'maxDD':>7}  VERDICT")
    lines = [hdr, "-" * len(hdr)]
    for s in results:
        for v in VARIANTS:
            d = s["variants"][v]
            lines.append(
                f"{s['plain_name'][:23]:<24}{v:>4}{d['trades']:>7}"
                f"{fmt(d['win_pct'], '.1f'):>7}{fmt(d['avg_r'], '+.3f'):>8}"
                f"{fmt(d['expectancy_after_costs_r'], '+.3f'):>8}"
                f"{fmt(d['max_dd_r'], '.2f'):>7}  {d['verdict']}")
    lines.append("-" * len(hdr))
    for v in VARIANTS:
        d = pooled[v]
        lines.append(
            f"{'ALL 3 CHANNELS (pooled)':<24}{v:>4}{d['trades']:>7}"
            f"{fmt(d['win_pct'], '.1f'):>7}{fmt(d['avg_r'], '+.3f'):>8}"
            f"{fmt(d['expectancy_after_costs_r'], '+.3f'):>8}"
            f"{fmt(d['max_dd_r'], '.2f'):>7}  {d['verdict']}")
    return "\n".join(lines)


def md_row(cname, v, d):
    return (f"| {cname} | {v} | {d['trades']} | {fmt(d['win_pct'], '.1f')} "
            f"| {fmt(d['avg_r'], '+.3f')} "
            f"| {fmt(d['expectancy_after_costs_r'], '+.3f')} "
            f"| {fmt(d['max_dd_r'], '.2f')} | {d['verdict']} |")


def write_md(report, results, pooled, recs):
    """Write agent-reports/scout-verification.md FIRST (file is the primary
    deliverable), then the caller prints the console summary."""
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    L = []
    ap = L.append
    ap("# SCOUT VERIFICATION: 3 scout-verified channels x relay exit geometry (POLICY V2)")
    ap("")
    ap(f"_generated {report['generated_utc']} · engine: `channel_verify_scout.py` "
       f"(read-only port of `channel_verify2.py`) · full data: `scout-verification.json` "
       f"· Telegram on `telethon-scout-verify.session` (sqlite backup copy; live "
       f"`telethon.session` never touched) · parser: current fixed `parser.py` "
       f"(arrow-format TPs + emoji-adjacent SLs)_")
    ap("")
    ap("## Channels")
    ap("")
    ap("| channel | id | link |")
    ap("|---|---|---|")
    for cid, name, uname in CHANNELS:
        ap(f"| {FALLBACK_NAMES[cid]} | `{cid}` | {uname} |")
    ap("")
    ap("## Question")
    ap("")
    ap("Expedited re-verification of the 3 scout-verified gold channels with the "
       "JUST-FIXED parser (arrow-format TPs, emoji-adjacent SLs): does the "
       "channels' raw DIRECTION carry an edge when every trade is managed by "
       "the relay's own trailing exit (`manage.py`), all channel TPs ignored?")
    ap("")
    ap("## Method")
    ap("")
    ap(f"- Last ~{MSG_LIMIT} messages per channel, relay's own deterministic "
       "parser, same keep-filter as V1/V2: parse_ok, non-manage, has SL, "
       ">=1 TP, numeric entry, not stale (>1% from price at signal time).")
    ap("- Market entry at the open of the first M15 bar at/after signal time "
       "(MT5 server-time offset from the freshest tick across "
       f"{'/'.join(OFFSET_SYMBOLS)}; this run: "
       f"{report['method']['server_offset_s']}s).")
    ap(f"- **Variant A**: initial SL = the channel's stated SL (R = |entry - SL|). "
       f"**Variant B**: initial SL = {ATR_SL_MULT:g} x ATR({ATR_PERIOD}) "
       "(Wilder, M15, strictly closed bars before entry; stated SL ignored).")
    ap("- ALL channel TPs ignored. Exit management identical to `manage.py` "
       f"(config.json `manage`): SL -> entry +/- {BE_BUF_PTS} points at "
       f"+{BE_AT_R:g}R favorable; from +{TRAIL_FROM_R:g}R favorable the SL "
       f"trails {TRAIL_DIST_R:g}R behind the best favorable price. Ratchet-only.")
    ap(f"- Walk up to {HORIZON_S // 3600}h from entry. Conservative same-bar rule: "
       "the stop as it stood at bar open is checked FIRST; that bar's favorable "
       "extreme may then advance the stop, effective next bar.")
    ap(f"- Costs: {COST_R}R round-trip haircut per trade. win% = resolved trades "
       "with R > 0. max DD = worst peak-to-trough of the cumulative after-cost "
       "R curve, trades ordered by entry time.")
    ap(f"- Verdict bands on expectancy after costs: >= +{EXP_BAND}R POSITIVE EDGE, "
       f"<= -{EXP_BAND}R NEGATIVE, else FLAT; n < {MIN_SAMPLE} resolved trades "
       f"= INSUFFICIENT (verdict tentative). Task gate: >= {MIN_SAMPLE} complete "
       "signals required for a promote call.")
    ap("- Trades whose 48h window extends beyond available data are `pending` "
       "and excluded from stats. MT5 strictly read-only "
       "(copy_rates/symbol_info/symbol_info_tick only; no order_send).")
    ap("")
    ap("## Results: channel x variant")
    ap("")
    ap("| channel | variant | trades | win% | avg R | exp after costs (R) "
       "| max DD (R) | verdict |")
    ap("|---|---|---:|---:|---:|---:|---:|---|")
    for s in results:
        for v in VARIANTS:
            ap(md_row(s["plain_name"], v, s["variants"][v]))
    for v in VARIANTS:
        d = pooled[v]
        ap(f"| **ALL 3 CHANNELS (pooled)** | **{v}** | {d['trades']} | "
           f"{fmt(d['win_pct'], '.1f')} | {fmt(d['avg_r'], '+.3f')} | "
           f"{fmt(d['expectancy_after_costs_r'], '+.3f')} | "
           f"{fmt(d['max_dd_r'], '.2f')} | {d['verdict']} |")
    ap("")
    ap("## Recommendations (promote / shadow)")
    ap("")
    for s in results:
        r = recs[int(s["id"])]
        ap(f"### {s['plain_name']} (`{s['id']}`)")
        ap("")
        if r["call"] == "PROMOTE":
            ap(f"- **CALL: PROMOTE to trading policy - variant {r['winning_variant']}** "
               f"({r['reason']}).")
            ap(f"- Policy params: `{json.dumps(r['params'])}` "
               "(sl_mode/atr_mult/tp_mode per config.json signal_policy schema); "
               "exits via manage.py: BE at +1R (10pt buffer), trail 0.5R from "
               "+1.5R, 48h horizon, 0.07R costs assumed.")
        else:
            ap(f"- **CALL: STAY SHADOW** - {r['reason']}.")
        ap(f"- Prior evidence: {PRIOR.get(int(s['id']), 'n/a')}.")
        ap("")
    ap("## Per-channel detail")
    ap("")
    for s in results:
        ap(f"### {s['plain_name']} (`{s['id']}`)")
        ap("")
        ap(f"- messages {s['messages']} (media-only {s['media_only']}, "
           f"recaps {s['recap_posts']}, unparseable {s['unparseable'] + s['unverifiable']}, "
           f"stale {s['stale']}, no-data {s['no_data']}, pending-no-bar {s['pending']})")
        for v in VARIANTS:
            d = s["variants"][v]
            ap(f"- **variant {v}**: {d['trades']} resolved "
               f"(initial-SL {d['classes']['sl']}, BE {d['classes']['be']}, "
               f"trail {d['classes']['trail']}, timeout {d['classes']['timeout']}; "
               f"pending {d['pending']}, no-ATR {d['no_atr']}), "
               f"win% {fmt(d['win_pct'], '.1f')}, avg {fmt(d['avg_r'], '+.3f')}R, "
               f"exp after costs {fmt(d['expectancy_after_costs_r'], '+.3f')}R, "
               f"net {fmt(d['net_r'], '+.2f')}R, maxDD {fmt(d['max_dd_r'], '.2f')}R "
               f"-> **{d['verdict']}**")
        ap("")
    ap("## Caveats")
    ap("")
    ap("- M15 granularity with the conservative same-bar rule takes the WORST "
       "fill ordering; real manage.py trailing (10s ticks) would do at least "
       "this well.")
    ap("- Samples are one ~300-message window per channel; n between "
       f"{MIN_SAMPLE} and ~20 should be treated as a small sample - consider "
       "reduced risk_pct on promotion and re-verify after another 2 weeks of "
       "live shadow data.")
    ap("- The parser still cannot read ASCII `->` arrows or TPs/SLs glued to "
       "decorative emoji with no separator (unicode arrows read fine); any "
       "such messages land in `unparseable` and are honestly counted, never "
       "simulated.")
    ap("- The 48h horizon leaves the freshest ~2 days of signals `pending`, "
       "excluded from stats.")
    ap("- No slippage modeling; fills at stop levels, 0.07R haircut covers "
       "spread/commission in R terms (same assumption as V1/V2/backtest.py).")
    ap("- Read-only guarantees: `telethon.session` never opened for connect and "
       "never written (research ran on `telethon-scout-verify.session`); MT5 "
       "never sent an order; no existing file modified. Created: "
       "`channel_verify_scout.py`, `telethon-scout-verify.session` (+journal), "
       "`scout-verification.json`, `agent-reports/scout-verification.md`.")
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return REPORT_MD


async def run():
    copy_session()  # FIRST: never touch the live session afterwards
    if not initialize_existing(mt5):
        print("MT5 connection unavailable:", broker_status())
        return 1
    print("MT5 attached (read-only):", mt5.account_info().server)
    results = []
    try:
        offset, per_symbol_ticks = compute_server_offset()
        api_id, api_hash = daemon._env_creds()
        if not (api_id and api_hash):
            print("no Telegram api credentials via daemon._env_creds()")
            return 1
        from telethon import TelegramClient
        client = TelegramClient(SESSION, api_id, api_hash)
        await client.connect()
        try:
            if not await client.is_user_authorized():
                print("scout-verify session NOT authorized (copy failed?)")
                return 1
            me = await client.get_me()
            print(f"Telegram: logged in as {me.first_name} (@{me.username})")
            for cid, name, _u in CHANNELS:
                print(f"--- verifying {name} ({cid}) ...")
                results.append(await analyze_channel(client, cid, name, offset))
        finally:
            await client.disconnect()
    finally:
        mt5.shutdown()
        print("MT5 shutdown (connection closed; terminal untouched)")

    # accumulate pooled RAW trade lists BEFORE finalize (which pops them)
    pooled_raw = {v: {"r_list": [], "ordered": [],
                      "classes": {"sl": 0, "be": 0, "trail": 0, "timeout": 0},
                      "pending": 0, "no_atr": 0} for v in VARIANTS}
    for st in results:
        for v in VARIANTS:
            sv = st["variants"][v]
            pr = pooled_raw[v]
            pr["r_list"].extend(sv["r_list"])
            pr["ordered"].extend(sv["ordered"])
            for kk, n in sv["classes"].items():
                pr["classes"][kk] += n
            pr["pending"] += sv["pending"]
            pr["no_atr"] += sv["no_atr"]

    # finalize per-channel variant stats, then per-channel recommendations
    for st in results:
        for v in VARIANTS:
            finalize_variant(st["variants"][v])
    pooled = {v: finalize_variant(pooled_raw[v]) for v in VARIANTS}

    recs = {int(st["id"]): recommend_channel(st) for st in results}
    for st in results:
        st["recommendation"] = recs[int(st["id"])]
        st["prior_evidence"] = PRIOR.get(int(st["id"]))

    n_promote = sum(1 for r in recs.values() if r["call"] == "PROMOTE")
    overall = (f"{n_promote} of {len(results)} channels clear the "
               f"+{EXP_BAND}R bar with >= {MIN_SAMPLE} resolved trades; "
               f"{len(results) - n_promote} stay shadow")

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "research": "SCOUT VERIFICATION: 3 scout-verified channels x relay "
                    "trailing exit (POLICY V2, fixed parser)",
        "method": {
            "messages_per_channel": MSG_LIMIT,
            "parser": "relay's own parser.parse_signal (current fixed version: "
                      "arrow-format TPs + emoji-adjacent SLs)",
            "keep_filter": "parse_ok, non-manage, has SL, >=1 TP, numeric entry, "
                           "not stale >1% (identical to V1/V2)",
            "timeframe": "M15",
            "horizon": f"{HORIZON_S // 3600}h from simulated entry",
            "entry": "open of first M15 bar at/after signal time (market entry)",
            "initial_sl": "variant A = channel's stated SL; variant B = "
                          f"{ATR_SL_MULT:g} x Wilder ATR({ATR_PERIOD}) M15 of "
                          "strictly closed bars before the entry bar",
            "channel_tps": "IGNORED entirely",
            "exit_management": f"manage.py rules from config.json: SL -> entry "
                                f"+/- {BE_BUF_PTS}pt buffer at +{BE_AT_R:g}R; from "
                                f"+{TRAIL_FROM_R:g}R trails {TRAIL_DIST_R:g}R behind "
                                "best favorable price; ratchet-only",
            "same_bar_rule": "stop as of bar open checked FIRST; this bar's "
                              "favorable extreme may then advance the stop, "
                              "effective next bar (conservative)",
            "timeout": "exit at close of last bar inside 48h, partial +/-R",
            "stale": "stated entry >1% away from price at signal time",
            "recap": "messages containing 'tp hit' or 'pips' counted, never simulated",
            "win_pct": "resolved trades with R > 0 (BE+buffer exits are tiny wins)",
            "costs": f"{COST_R}R round-trip haircut per trade (same as V1/V2/backtest.py)",
            "max_dd": "worst peak-to-trough of cumulative after-cost R curve, "
                      "trades ordered by entry time",
            "verdict_bands": f"expectancy after costs >= +{EXP_BAND}R POSITIVE EDGE, "
                              f"<= -{EXP_BAND}R NEGATIVE, else FLAT; n < {MIN_SAMPLE} "
                              "= INSUFFICIENT DATA (tentative)",
            "min_sample_gate": MIN_SAMPLE,
            "server_offset_s": round(offset),
            "server_offset_method": "freshest tick across " + "/".join(OFFSET_SYMBOLS),
            "tick_times_at_run": per_symbol_ticks,
            "symbols_selected_for_data": sorted(_selected_symbols),
            "session": "telethon-scout-verify.session (sqlite backup copy of "
                       "telethon.session; live session never connected/written)",
            "mt5_access": "read-only: initialize/shutdown + copy_rates/"
                          "symbol_info/symbol_info_tick/symbol_select; "
                          "order_send never called",
        },
        "channels": results,
        "pooled": pooled,
        "recommendations": {str(k): v for k, v in recs.items()},
        "overall": {"verdict": overall},
    }
    md_path = write_md(report, results, pooled, recs)   # file FIRST
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"markdown report saved: {md_path}")
    print(f"report saved: {REPORT}")

    print()
    print(console_table(results, pooled))
    print()
    print(f"OVERALL: {overall}")
    for cid in recs:
        r = recs[cid]
        line = (f"CALL {FALLBACK_NAMES[cid]} ({cid}): {r['call']}"
                + (f" variant {r['winning_variant']} params {json.dumps(r['params'])}"
                   if r["params"] else "") + f" - {r['reason']}")
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))

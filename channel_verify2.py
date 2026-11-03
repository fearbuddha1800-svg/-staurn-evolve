"""EXIT-GEOMETRY research engine (READ-ONLY): channel DIRECTION x OUR exit.

Research question (POLICY V2): V1 (channel_verify.py / channel_report.json)
showed every watched channel is a TP-farm - 81-91% win rates but avg R ~ 0,
because TP1 sits far closer than the SL. This engine isolates the variable:
it keeps the channels' DIRECTION, entry timing and keep-filter IDENTICAL to
V1, but replaces their exit geometry with the relay's own manage.py
trailing engine and ignores every channel TP.

Per signal, per variant:
  - market entry at the open of the first M15 bar at/after signal time
  - initial stop / R basis:
      variant A = the channel's stated SL (R = |sim_entry - stated SL|)
      variant B = 2 x ATR(14) (Wilder, M15, strictly closed bars before the
                  entry bar; stated SL ignored entirely)
  - ALL channel TPs are IGNORED (no take-profit anywhere)
  - exit management, same rules as manage.py / config.json "manage":
      +1.0R favorable  -> SL to entry +/- 10-point buffer (break-even)
      >= +1.5R favorable -> SL trails 0.5R behind the best favorable price,
      ratchet-only, never widens
  - walk up to 48h from simulated entry
  - conservative same-bar rule: the stop AS IT STOOD AT BAR OPEN is checked
    FIRST; only if it survives may that bar's favorable extreme advance the
    stop, and the new level is effective from the NEXT bar
  - 0.07R round-trip cost haircut per trade (same as V1 / backtest.py)

Everything else reuses V1's proven pipeline verbatim: sqlite-backup session
copy to telethon-research.session BEFORE connecting (the live
telethon.session is never opened for connect and never written), the relay's
own deterministic parser with the same keep-filter (recap skip, parse_ok,
non-manage, SL + >=1 TP + numeric entry, not stale >1%), the MT5 server-time
offset from the freshest tick across liquid symbols, and the M15 bar walk.

MT5 strictly read-only: initialize/shutdown + market-data reads only
(copy_rates_range / symbol_info / symbol_info_tick / symbol_select for data
visibility). NEVER order_send, never positions_get, no trades.

No existing file is edited. Creates only:
  channel_report_v2.json, agent-reports/exit-geometry.md,
  telethon-research.session (+ -journal).
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
import parser as sigparser  # noqa: E402  (the relay's own parser)
from executor import resolve_symbol  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

LIVE_SESSION = os.path.join(BASE, "telethon.session")       # NEVER touched
SESSION = os.path.join(BASE, "telethon-research.session")   # our private copy
REPORT = os.path.join(BASE, "channel_report_v2.json")
REPORT_MD = os.path.join(BASE, "agent-reports", "exit-geometry.md")
V1_REPORT = os.path.join(BASE, "channel_report.json")

with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
    CFG = json.load(f)
_M = CFG.get("manage") or {}
BE_AT_R = float(_M.get("be_at_r", 1.0))            # 1.0
TRAIL_FROM_R = float(_M.get("trail_from_r", 1.5))   # 1.5
TRAIL_DIST_R = float(_M.get("trail_dist_r", 0.5))  # 0.5
BE_BUF_PTS = int(_M.get("be_buffer_points", 10))   # manage.py default

# watched channels come from config.json (same 5 as V1); plain names kept
# from V1 for readable tables
FALLBACK_NAMES = {
    -1002369502254: "Best Signal Forex",
    -1002692333123: "XAUUSD PRO SIGNAL",
    -1001920020352: "Grow Trading",
    -1002165799093: "XAUUSD FREE SIGNALS",
    -1001284268486: "Easy Forex OFFICIAL",
}
try:
    CHANNEL_IDS = [int(c) for c in (CFG.get("channels") or [])]
except (TypeError, ValueError):
    CHANNEL_IDS = list(FALLBACK_NAMES.keys())

MSG_LIMIT = 300            # last ~300 messages per channel (same as V1)
LOOKBACK_S = 7 * 24 * 3600  # bars before signal: ATR warmup (Wilder converges)
FORWARD_S = 120 * 3600      # 48h walk + weekend-gap headroom
HORIZON_S = 48 * 3600       # trade must resolve within 48h from entry
M15 = 900
STALE_FRAC = 0.01          # >1% away from price at signal time = stale re-post
MIN_SAMPLE = 10             # same as V1
COST_R = 0.07               # round-trip cost haircut per trade (V1/backtest.py)
RECAP_PATTERNS = ("tp hit", "pips")
OFFSET_SYMBOLS = ("XAUUSD", "EURUSD", "GBPUSD", "US30", "XAGUSD", "AUDUSD")
ATR_PERIOD = 14
ATR_SL_MULT = 2.0           # variant B: SL = 2 x ATR(14)
VARIANTS = ("A", "B")
EXP_BAND = 0.05             # |expectancy after costs| < 0.05R -> FLAT

_selected_symbols = set()  # symbols we had to symbol_select() for data access
_point_cache = {}          # symbol -> point (for the BE buffer)


# ---------------------------------------------------------------- session copy
def copy_session():
    """Copy telethon.session -> telethon-research.session WITHOUT touching or
    contending the live session: prefer the sqlite backup API (lock-safe),
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
    print(f"research session copy ready: {SESSION} ({os.path.getsize(SESSION)} bytes)")


# ------------------------------------------------------------------ mt5 helpers
def compute_server_offset():
    """Determine the MT5 server-time offset ONCE, V1 method: server epochs
    are real epoch + offset for every symbol, so the FRESHEST tick across
    liquid symbols is the correct estimator (XAUUSD's demo feed can be
    frozen, which would under-report the offset)."""
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
    (the entry bar is still open at entry time, so it is excluded - same
    convention as strategy.py, which decides on closed bars). Seed = SMA of
    the first `period` true ranges, then Wilder smoothing. Returns None when
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
    fill at the stop level (same no-slippage convention as V1; BE/trail
    levels are always levels the market actually traded through, because
    they can only arm after the favorable side visited them).

    Returns (label, r, exit_price, exit_srv_epoch) with label in
    {"sl" (initial stop), "be" (break-even stop), "trail" (trailing stop),
    "timeout" (48h horizon close), "pending" (data ends before horizon)}.
    """
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


async def analyze_channel(client, cid, fallback_name, offset):
    st = new_channel_state(cid, fallback_name)
    try:
        try:
            ent = await client.get_entity(cid)
            title = getattr(ent, "title", None) or fallback_name
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
            sym = resolve_symbol(raw_sym)
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


def load_v1():
    """V1 per-channel summary (the channels' own exit geometry) for contrast."""
    try:
        with open(V1_REPORT, encoding="utf-8") as f:
            v1 = json.load(f)
        return {int(c["id"]): {
            "simulated": c.get("simulated"), "win_pct": c.get("win_pct"),
            "avg_r": c.get("avg_r"),
            "expectancy_after_costs_r": c.get("expectancy_after_costs_r"),
        } for c in v1.get("channels", [])}
    except Exception:  # noqa: BLE001
        return {}


# ------------------------------------------------------------------ reporting
def fmt(x, spec=None, dash="-"):
    if x is None:
        return dash
    if spec is None:
        return str(x)
    return format(x, spec)


def console_table(results, pooled, best):
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
            f"{'ALL CHANNELS (pooled)':<24}{v:>4}{d['trades']:>7}"
            f"{fmt(d['win_pct'], '.1f'):>7}{fmt(d['avg_r'], '+.3f'):>8}"
            f"{fmt(d['expectancy_after_costs_r'], '+.3f'):>8}"
            f"{fmt(d['max_dd_r'], '.2f'):>7}  {d['verdict']}")
    if best:
        lines.append("")
        lines.append(f"BEST COMBO (n>={MIN_SAMPLE}): {best['label']} -> "
                     f"{best['trades']} trades, win% {best['win_pct']}, "
                     f"avg {best['avg_r']:+.3f}R, expectancy after costs "
                     f"{best['expectancy_after_costs_r']:+.3f}R, "
                     f"maxDD {best['max_dd_r']}R")
    return "\n".join(lines)


def md_table(rows):
    out = ["| channel | variant | trades | win% | avg R | exp after costs (R) "
           "| max DD (R) | verdict |",
           "|---|---|---:|---:|---:|---:|---:|---|"]
    out.extend(rows)
    return "\n".join(out)


def md_row(cname, v, d):
    return (f"| {cname} | {v} | {d['trades']} | {fmt(d['win_pct'], '.1f')} "
            f"| {fmt(d['avg_r'], '+.3f')} "
            f"| {fmt(d['expectancy_after_costs_r'], '+.3f')} "
            f"| {fmt(d['max_dd_r'], '.2f')} | {d['verdict']} |")


def write_md(report, results, pooled, best, v1map):
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    L = []
    ap = L.append
    ap("# EXIT-GEOMETRY research: channel DIRECTION x relay trailing exit "
       "(POLICY V2)")
    ap("")
    ap(f"_generated {report['generated_utc']} · engine: `channel_verify2.py` "
       f"(read-only) · full data: `channel_report_v2.json` · "
       f"baseline: `channel_report.json` (V1, the channels' own exits)_")
    ap("")
    ap("## Question")
    ap("")
    ap("V1 forensics showed every watched channel is a **TP-farm**: 81-91% win "
       "rates but avg R ~ 0 after costs, because their TP1 sits far closer "
       "than their SL (they harvest cosmetic win%, give back -1R on the "
       "losers). This research isolates the variable: **keep the channels' "
       "direction and entry timing, throw away their entire exit geometry, "
       "and manage every trade with the relay's own `manage.py` engine** "
       "(break-even at +1R, then a 0.5R trailing stop from +1.5R - no "
       "take-profit anywhere).")
    ap("")
    ap("## Method")
    ap("")
    ap("- Same 300-message fetch per channel, same deterministic parser and "
       "same keep-filter as V1: parse_ok, non-manage, has SL, >=1 TP, numeric "
       "entry, not stale (>1% from price at signal time). Trade set is "
       "identical to V1; only the exit policy changes.")
    ap("- Market entry at the open of the first M15 bar at/after signal time "
       "(MT5 server-time offset from the freshest tick across "
       "XAUUSD/EURUSD/GBPUSD/US30/XAGUSD/AUDUSD; this run: "
       f"{report['method']['server_offset_s']}s).")
    ap("- **Variant A**: initial SL = the channel's stated SL "
       "(R = |entry - SL|). **Variant B**: initial SL = "
       f"{ATR_SL_MULT:g} x ATR({ATR_PERIOD}) (Wilder, M15, strictly closed "
       "bars before entry; the stated SL is ignored).")
    ap("- ALL channel TPs ignored. Exit management identical to "
       f"`manage.py` (config.json `manage`): SL -> entry +/- "
       f"{BE_BUF_PTS} points at +{BE_AT_R:g}R favorable; from "
       f"+{TRAIL_FROM_R:g}R favorable the SL trails {TRAIL_DIST_R:g}R behind "
       "the best favorable price. Ratchet-only, never widens.")
    ap(f"- Walk up to {HORIZON_S // 3600}h from entry. Conservative same-bar "
       "rule: the stop as it stood at bar open is checked FIRST; that bar's "
       "favorable extreme may then advance the stop, effective next bar. "
       "(BE/trail levels are always levels the market actually traded "
       "through, so their fills are real; initial-SL fills are at the SL "
       "level, same no-slippage convention as V1.)")
    ap(f"- Costs: {COST_R}R round-trip haircut per trade. win% = resolved "
       "trades with R > 0 (break-even exits with the 10-point buffer count "
       "as tiny wins, which they are). max DD = worst peak-to-trough of the "
       "cumulative after-cost R curve, trades ordered by entry time.")
    ap(f"- Verdict bands on expectancy after costs: >= +{EXP_BAND}R "
       f"POSITIVE EDGE, <= -{EXP_BAND}R NEGATIVE, else FLAT; "
       f"n < {MIN_SAMPLE} resolved trades = INSUFFICIENT DATA (verdict is "
       "tentative).")
    ap("- Trades whose 48h window extends beyond available data are `pending` "
       "and excluded from stats (the 48h horizon vs V1's 24h means the "
       "freshest ~2 days of signals are still open - counts are reported "
       "honestly per channel).")
    ap("- Telegram ran on a sqlite-backup COPY of the live session "
       "(`telethon-research.session`); `telethon.session` was never opened "
       "for connect and never written. MT5 access was strictly read-only: "
       "initialize/shutdown + copy_rates/symbol_info/symbol_info_tick only; "
       "no order_send anywhere.")
    ap("")
    ap("## Results: channel x variant")
    ap("")
    rows = []
    for s in results:
        for v in VARIANTS:
            rows.append(md_row(s["plain_name"], v, s["variants"][v]))
    rows.append("| **ALL CHANNELS (pooled)** | **A** | "
                f"{pooled['A']['trades']} | {fmt(pooled['A']['win_pct'], '.1f')} "
                f"| {fmt(pooled['A']['avg_r'], '+.3f')} "
                f"| {fmt(pooled['A']['expectancy_after_costs_r'], '+.3f')} "
                f"| {fmt(pooled['A']['max_dd_r'], '.2f')} "
                f"| {pooled['A']['verdict']} |")
    rows.append("| **ALL CHANNELS (pooled)** | **B** | "
                f"{pooled['B']['trades']} | {fmt(pooled['B']['win_pct'], '.1f')} "
                f"| {fmt(pooled['B']['avg_r'], '+.3f')} "
                f"| {fmt(pooled['B']['expectancy_after_costs_r'], '+.3f')} "
                f"| {fmt(pooled['B']['max_dd_r'], '.2f')} "
                f"| {pooled['B']['verdict']} |")
    ap(md_table(rows))
    ap("")
    ap("Exit-mix per variant (pooled): initial-SL full losses "
       f"{pooled['A']['classes']['sl'] + pooled['B']['classes']['sl']} "
       f"(A {pooled['A']['classes']['sl']} / B {pooled['B']['classes']['sl']}), "
       "break-even exits "
       f"{pooled['A']['classes']['be'] + pooled['B']['classes']['be']} "
       f"(A {pooled['A']['classes']['be']} / B {pooled['B']['classes']['be']}), "
       "trailing-stop exits "
       f"{pooled['A']['classes']['trail'] + pooled['B']['classes']['trail']} "
       f"(A {pooled['A']['classes']['trail']} / "
       f"B {pooled['B']['classes']['trail']}), "
       "48h timeouts "
       f"{pooled['A']['classes']['timeout'] + pooled['B']['classes']['timeout']} "
       f"(A {pooled['A']['classes']['timeout']} / "
       f"B {pooled['B']['classes']['timeout']}).")
    ap("")
    ap("## V1 (their exits) vs V2 (our exits), expectancy after costs")
    ap("")
    ap("| channel | V1 trades | V1 win% | V1 avg R | V1 exp | "
       "V2-A exp | V2-B exp | delta (best V2 - V1) |")
    ap("|---|---:|---:|---:|---:|---:|---:|---:|")
    for s in results:
        v1 = v1map.get(int(s["id"]), {})
        v1e = v1.get("expectancy_after_costs_r")
        ea = s["variants"]["A"]["expectancy_after_costs_r"]
        eb = s["variants"]["B"]["expectancy_after_costs_r"]
        cands = [x for x in (ea, eb) if x is not None]
        delta = (max(cands) - v1e) if (cands and v1e is not None) else None
        ap(f"| {s['plain_name']} "
           f"| {fmt(v1.get('simulated'))} | {fmt(v1.get('win_pct'), '.1f')} "
           f"| {fmt(v1.get('avg_r'), '+.3f')} | {fmt(v1e, '+.3f')} "
           f"| {fmt(ea, '+.3f')} | {fmt(eb, '+.3f')} "
           f"| {fmt(delta, '+.3f')} |")
    ap("")
    ap("## Per-channel detail")
    ap("")
    for s in results:
        ap(f"### {s['plain_name']} (`{s['id']}`)")
        ap("")
        ap(f"- messages {s['messages']} (media-only {s['media_only']}, "
           f"recaps {s['recap_posts']}, unparseable {s['unparseable'] + s['unverifiable']}, "
           f"stale {s['stale']}, pending-no-bar {s['pending']})")
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
    ap("## Verdict")
    ap("")
    if best:
        ap(f"- **Best combo: {best['label']}** - {best['trades']} trades, "
           f"win% {best['win_pct']}, avg {best['avg_r']:+.3f}R, "
           f"**expectancy after costs {best['expectancy_after_costs_r']:+.3f}R**, "
           f"maxDD {best['max_dd_r']}R "
           f"({best['verdict']}).")
    ap(f"- **Research answer: {report['overall']['verdict']}** "
       f"(pooled expectancy after costs: A {fmt(pooled['A']['expectancy_after_costs_r'], '+.3f')}R "
       f"over {pooled['A']['trades']} trades, "
       f"B {fmt(pooled['B']['expectancy_after_costs_r'], '+.3f')}R "
       f"over {pooled['B']['trades']} trades).")
    ap(f"- {report['overall']['verdict_note']}")
    ap("")
    ap("## Caveats")
    ap("")
    ap("- M15 granularity: no intra-bar path, so the conservative same-bar "
       "rule systematically takes the WORST fill ordering; real trailing "
       "would have done at least this well (manage.py runs on 10s ticks).")
    ap("- Samples are small: Grow Trading has ~3 checkable signals, Easy "
       "Forex OFFICIAL posts zero verifiable signals (143 of ~300 messages "
       "are self-reported recaps). Only the XAUUSD channels and Best Signal "
       "Forex reach double digits.")
    ap("- The 48h horizon (vs V1's 24h) leaves the freshest ~2 days of "
       "signals open (`pending`); they are excluded from stats, so V2 "
       "samples skew slightly older than V1's.")
    ap("- No slippage modeling (fills at the stop level); the 0.07R haircut "
       "covers spread/commission in R terms, same assumption as the relay's "
       "own backtest.")
    ap("- Read-only guarantees: `telethon.session` untouched (research ran "
       "on a backup copy), MT5 never sent an order, no existing file was "
       "modified. Created: `channel_verify2.py`, `channel_report_v2.json`, "
       "`agent-reports/exit-geometry.md`, `telethon-research.session`.")
    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return REPORT_MD


async def run():
    copy_session()
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
                print("research session NOT authorized (copy failed?)")
                return 1
            me = await client.get_me()
            print(f"Telegram: logged in as {me.first_name} (@{me.username})")
            for cid in CHANNEL_IDS:
                fb = FALLBACK_NAMES.get(cid, str(cid))
                print(f"--- researching {fb} ({cid}) ...")
                results.append(await analyze_channel(client, cid, fb, offset))
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

    # finalize per-channel variant stats
    for st in results:
        for v in VARIANTS:
            finalize_variant(st["variants"][v])

    # pooled per variant across channels
    pooled = {v: finalize_variant(pooled_raw[v]) for v in VARIANTS}

    v1map = load_v1()
    for st in results:
        st["v1_channel_exit"] = v1map.get(int(st["id"]))

    # best combo with an adequate sample
    combos = []
    for st in results:
        for v in VARIANTS:
            d = st["variants"][v]
            if d["trades"] >= MIN_SAMPLE and d["expectancy_after_costs_r"] is not None:
                combos.append({"label": f"{st['plain_name']} x variant {v}", **d})
    combos.sort(key=lambda c: c["expectancy_after_costs_r"], reverse=True)
    best = combos[0] if combos else None

    n_pos = sum(1 for c in combos if c["expectancy_after_costs_r"] >= EXP_BAND)
    if best is not None and best["expectancy_after_costs_r"] >= EXP_BAND:
        verdict = "POSITIVE EDGE - direction carries real edge once exit geometry is ours"
        note = (f"{n_pos} of {len(combos)} adequately-sampled combos are "
                f"positive after costs; replacing the channels' TP-farm exits "
                f"with the trailing engine flips the best channel from ~0R "
                f"(V1) to {best['expectancy_after_costs_r']:+.3f}R per trade.")
    elif pooled["A"]["expectancy_after_costs_r"] is not None and (
            pooled["A"]["expectancy_after_costs_r"] > 0 or
            pooled["B"]["expectancy_after_costs_r"] > 0):
        verdict = "MIXED - some combos improve but none clear the +%.2fR bar" % EXP_BAND
        note = ("The trailing engine recovers most of the TP-farm giveback "
                "(expectancy moves toward breakeven) but the channels' raw "
                "direction does not clear costs decisively.")
    else:
        verdict = "NEGATIVE - the channels' direction itself carries no edge"
        note = ("Even with our exit geometry the signals lose after costs: "
                "the problem is the DIRECTION, not just their exits.")

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "research": "EXIT-GEOMETRY: channel direction + relay trailing exit (POLICY V2)",
        "method": {
            "messages_per_channel": MSG_LIMIT,
            "parser": "relay's own parser.parse_signal (deterministic, no AI fallback)",
            "keep_filter": "parse_ok, non-manage, has SL, >=1 TP, numeric entry, "
                           "not stale >1% (identical to V1)",
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
            "costs": f"{COST_R}R round-trip haircut per trade (same as V1/backtest.py)",
            "max_dd": "worst peak-to-trough of cumulative after-cost R curve, "
                      "trades ordered by entry time",
            "verdict_bands": f"expectancy after costs >= +{EXP_BAND}R POSITIVE EDGE, "
                             f"<= -{EXP_BAND}R NEGATIVE, else FLAT; "
                             f"n < {MIN_SAMPLE} = INSUFFICIENT DATA (tentative)",
            "server_offset_s": round(offset),
            "server_offset_method": "freshest tick across " + "/".join(OFFSET_SYMBOLS),
            "tick_times_at_run": per_symbol_ticks,
            "symbols_selected_for_data": sorted(_selected_symbols),
            "session": "telethon-research.session (sqlite backup copy of "
                       "telethon.session; live session never connected/written)",
            "mt5_access": "read-only: initialize/shutdown + copy_rates/"
                          "symbol_info/symbol_info_tick/symbol_select; "
                          "order_send never called",
        },
        "channels": results,
        "pooled": pooled,
        "best_combo": best,
        "overall": {"verdict": verdict, "verdict_note": note,
                    "adequate_sample_combos": len(combos),
                    "positive_combos": n_pos},
    }
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"report saved: {REPORT}")

    print()
    print(console_table(results, pooled, best))
    print()
    print(f"RESEARCH VERDICT: {verdict}")
    if best:
        print(f"BEST COMBO: {best['label']}: {best['trades']} trades, "
              f"win% {best['win_pct']}, avg {best['avg_r']:+.3f}R, "
              f"expectancy after costs {best['expectancy_after_costs_r']:+.3f}R, "
              f"maxDD {best['max_dd_r']}R")

    md_path = write_md(report, results, pooled, best, v1map)
    print(f"markdown report saved: {md_path}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))

---
slug: channel_verify_mass
type: note
graph: gitnexus
---

"""MASS-VERIFICATION engine (READ-ONLY): the 14 watched channels that have NO
prior verification evidence, x relay exit geometry (POLICY V2).

Faithful port of the proven V2 engine (channel_verify2.py / method spec in
agent-reports/exit-geometry.md, current fixed-parser port channel_verify_scout.py):
channel DIRECTION + OUR trailing exits.

Channel set (14 = every config.json-watched channel not covered by any prior
verification report - V1/V2/V3/scout):
  - the 12 joined channels in new_channels_batch.json (never simulated)
  - the 2 scout-shortlist incumbents already in config.json channels but never
    simulated: Lingrid Forex Signals (-1001189068380, scout-channels-v2.md #5)
    and Forex GDP - Free Signals (-1001175463265, scout-channels-v2.md #7)

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
    (MT5 server-time offset from the freshest tick across liquid symbols)
  - 48h walk; conservative same-bar rule (stop as of bar open checked FIRST)
  - 0.07R round-trip cost haircut per trade
  - verdict bands on expectancy after costs (exit-geometry.md): >= +0.05R
    POSITIVE EDGE, <= -0.05R NEGATIVE, else FLAT; n < 10 resolved =
    INSUFFICIENT DATA (tentative)
  - per-channel call with expectancy numbers:
      PROMOTE  (winning variant + signal_policy params)  exp >= +0.05R, n >= 10
      DEMOTE   (remove from config.json channels)         best adequate variant exp <= -0.05R
      STAY SHADOW (record only)                          everything else

  - duplicate-content detection: channels with identical (exact mirrors)
    or >= 80%-overlapping (near-mirrors) trade fingerprints - same side +
    entry-bar open + outcome R - are flagged as one cluster, pooled only
    once (deduped pooled stats), and at most ONE channel of a cluster may
    be promoted (double-execution guard)

Safety (same guarantees as V2/scout):
  - telethon.session is NEVER touched: a sqlite-backup copy is made to
    telethon-mass.session BEFORE connecting, and only the copy is used
  - MT5 strictly read-only: initialize/shutdown + market-data reads only
    (copy_rates_range / symbol_info / symbol_info_tick / symbol_select);
    NEVER order_send, never positions_get, no trades
  - no existing file is edited; creates only: channel_verify_mass.py (this
    file), telethon-mass.session (+ -journal), mass-verification.json,
    agent-reports/mass-verification.md
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
import parser as sigparser  # noqa: E402  (the relay's own parser, fixed)
from executor import resolve_symbol  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

LIVE_SESSION = os.path.join(BASE, "telethon.session")          # NEVER touched
SESSION = os.path.join(BASE, "telethon-mass.session")          # our private copy
REPORT = os.path.join(BASE, "mass-verification.json")
REPORT_MD = os.path.join(BASE, "agent-reports", "mass-verification.md")
BATCH_FILE = os.path.join(BASE, "new_channels_batch.json")

with open(os.path.join(BASE, "config.json"), encoding="utf-8") as f:
    CFG = json.load(f)
_M = CFG.get("manage") or {}
BE_AT_R = float(_M.get("be_at_r", 1.0))            # 1.0
TRAIL_FROM_R = float(_M.get("trail_from_r", 1.5))  # 1.5
TRAIL_DIST_R = float(_M.get("trail_dist_r", 0.5))  # 0.5
BE_BUF_PTS = int(_M.get("be_buffer_points", 10))    # manage.py default

# the 2 scout-shortlist incumbents already in config.json channels but never
# simulated (names/usernames confirmed from the session's entity cache)
INCUMBENTS = [
    (-1001189068380, "Lingrid Forex Signals", "t.me/lingridchannel"),
    (-1001175463265, "Forex GDP - Free Signals (scout)", "t.me/forexgdpfree"),
]


def load_channels():
    """The 14 verification targets: the 12 joined channels from
    new_channels_batch.json + the 2 never-simulated incumbents. Fails loudly
    if the batch file is unreadable (never silently verifies a different set).
    """
    with open(BATCH_FILE, encoding="utf-8") as f:
        batch = json.load(f)
    out = []
    for c in batch.get("joined", []):
        cid = int(c["id"])
        handle = c.get("handle") or str(cid)
        out.append((cid, handle, f"t.me/{handle}" if c.get("handle") else ""))
    out.extend(INCUMBENTS)
    return out


CHANNELS = load_channels()
FALLBACK_NAMES = {cid: name for cid, name, _u in CHANNELS}
USERNAMES = {cid: uname for cid, _n, uname in CHANNELS}

MSG_LIMIT = 300             # last ~300 messages per channel (same as V2)
LOOKBACK_S = 7 * 24 * 3600  # bars before signal: ATR warmup (Wilder converges)
FORWARD_S = 120 * 3600      # 48h walk + weekend-gap headroom
HORIZON_S = 48 * 3600       # trade must resolve within 48h from entry
M15 = 900
STALE_FRAC = 0.01           # >1% away from price at signal time = stale re-post
MIN_SAMPLE = 10             # exit-geometry.md: n < 10 = INSUFFICIENT (tentative)
COST_R = 0.07               # round-trip cost haircut per trade (V1/V2/backtest.py)
RECAP_PATTERNS = ("tp hit", "pips")
OFFSET_SYMBOLS = ("XAUUSD", "EURUSD", "GBPUSD", "US30", "XAGUSD", "AUDUSD")
ATR_PERIOD = 14
ATR_SL_MULT = 2.0           # variant B: SL = 2 x ATR(14)
VARIANTS = ("A", "B")
EXP_BAND = 0.05             # |expectancy after costs| < 0.05R -> FLAT

# prior evidence (context only; this run is the FIRST simulation for all 14)
PRIOR = {
    -1001189068380: "scout-channels-v2.md shortlist #5 (Lingrid) - external "
                    "survey evidence only, never simulated before this run",
    -1001175463265: "scout-channels-v2.md shortlist #7 (Forex GDP free feed) "
                    "- external survey evidence only, never simulated before "
                    "this run",
}
NO_PRIOR = ("no prior verification evidence - first simulation run (new batch; "
            "not present in scan-inventory.md / full-sweep.md verified set)")

_selected_symbols = set()  # symbols we had to symbol_select() for data access
_point_cache = {}          # symbol -> point (for the BE buffer)


# ---------------------------------------------------------------- session copy
def copy_session():
    """Copy telethon.session -> telethon-mass.session WITHOUT touching or
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
    print(f"mass-verify session copy ready: {SESSION} ({os.path.getsize(SESSION)} bytes)")


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


# ------------------------------------------------------- duplicate detection
def trade_keyset(st, v):
    """Set of (side, entry-bar open, outcome R) for the variant's resolved
    trades - a content fingerprint independent of message ids and posting
    time (mirrors often re-post with a ~1min delay)."""
    ks = set()
    for s in st["signals"]:
        d = (s.get("variants") or {}).get(v)
        if d and d.get("r") is not None:
            ks.add((s["side"], s.get("sim_entry"), round(d["r"], 3)))
    return ks


def build_clusters(results):
    """Detect duplicate-content channels. Exact mirrors: identical variant-A
    AND variant-B trade fingerprints (>= 3 trades). Near-mirrors: >= 80% A-
    fingerprint overlap with a cluster leader (re-posts often land one bar
    later, changing a single entry/outcome). This niche re-brands one VIP
    feed into several 'channels'; mirrors are NOT independent evidence and
    must not be promoted alongside each other (same signal = double
    execution). Leader = highest (closest-to-zero, i.e. OLDEST) channel id -
    the original; re-brands get newer ids."""
    info = {int(st["id"]): (trade_keyset(st, "A"), trade_keyset(st, "B"))
            for st in results}
    clusters = []
    used = set()
    for st in results:
        cid = int(st["id"])
        if cid in used:
            continue
        ka, kb = info[cid]
        if len(ka) < 3:
            continue
        members = [cid]
        for st2 in results:
            cid2 = int(st2["id"])
            if cid2 == cid or cid2 in used or cid2 in members:
                continue
            ka2, kb2 = info[cid2]
            if ka2 == ka and kb2 == kb:
                members.append(cid2)
        if len(members) > 1:
            leader = max(members)  # oldest Telegram id = likely the original
            clusters.append({"leader": leader, "members": sorted(members),
                             "n_channels": len(members),
                             "n_trades": len(ka)})
            used.update(members)
    # near-mirror pass: >= 80% A-fingerprint overlap with a cluster leader
    for st in results:
        cid = int(st["id"])
        if cid in used:
            continue
        ka = info[cid][0]
        if len(ka) < 3:
            continue
        best, best_ov = None, 0.0
        for c in clusters:
            kl = info[c["leader"]][0]
            if not kl:
                continue
            ov = len(ka & kl) / min(len(ka), len(kl))
            if ov > best_ov:
                best_ov, best = ov, c
        if best is not None and best_ov >= 0.8:
            best.setdefault("near_members", []).append(cid)
            best["n_channels"] += 1
            used.add(cid)
    for c in clusters:
        c.setdefault("near_members", [])
        c["all_members"] = sorted(c["members"] + c["near_members"])
    cmap = {m: c for c in clusters for m in c["all_members"]}
    return clusters, cmap


# ----------------------------------------------------------------- promote call
def policy_params(variant):
    """signal_policy params (config.json schema) for the winning variant."""
    p = ({"sl_mode": "channel"} if variant == "A"
         else {"sl_mode": "atr", "atr_mult": ATR_SL_MULT})
    p["tp_mode"] = "none"  # all channel TPs ignored; manage.py trailing exits
    return p


def best_adequate(st):
    """(variant, stats) of the best adequately-sampled variant, or (None, None)."""
    bv, bd = None, None
    for v in VARIANTS:
        d = st["variants"][v]
        if d["trades"] >= MIN_SAMPLE and d["expectancy_after_costs_r"] is not None:
            if bd is None or d["expectancy_after_costs_r"] > bd["expectancy_after_costs_r"]:
                bv, bd = v, d
    return bv, bd


def recommend_channel(st):
    """Explicit per-channel call with expectancy numbers:
    PROMOTE (winning variant + params) / DEMOTE (remove from watch) /
    STAY SHADOW (record only)."""
    bv, d = best_adequate(st)
    if bv is None:
        return {"call": "STAY SHADOW", "winning_variant": None,
                "params": None,
                "reason": f"fewer than {MIN_SAMPLE} resolved trades in both "
                          f"variants (A n={st['variants']['A']['trades']}, "
                          f"B n={st['variants']['B']['trades']}) - sample too "
                          "small for a promote/demote call"}
    if d["expectancy_after_costs_r"] >= EXP_BAND:
        return {"call": "PROMOTE", "winning_variant": bv,
                "params": policy_params(bv),
                "exp_after_costs_r": d["expectancy_after_costs_r"],
                "trades": d["trades"], "win_pct": d["win_pct"],
                "max_dd_r": d["max_dd_r"],
                "reason": f"variant {bv} clears the bar: "
                          f"{d['expectancy_after_costs_r']:+.3f}R expectancy "
                          f"after costs over {d['trades']} resolved trades "
                          f"(win% {d['win_pct']}, maxDD {d['max_dd_r']}R)"}
    if d["expectancy_after_costs_r"] <= -EXP_BAND:
        other = st["variants"]["B" if bv == "A" else "A"]
        return {"call": "DEMOTE (remove from config.json channels)",
                "winning_variant": bv, "params": None,
                "exp_after_costs_r": d["expectancy_after_costs_r"],
                "trades": d["trades"], "win_pct": d["win_pct"],
                "max_dd_r": d["max_dd_r"],
                "reason": f"best variant {bv} is "
                          f"{d['expectancy_after_costs_r']:+.3f}R after costs "
                          f"over {d['trades']} trades - at or below "
                          f"-{EXP_BAND}R: verified NEGATIVE, do not relay "
                          f"(other variant n={other['trades']} "
                          f"exp {other['expectancy_after_costs_r']})"}
    return {"call": "STAY SHADOW", "winning_variant": bv, "params": None,
            "exp_after_costs_r": d["expectancy_after_costs_r"],
            "trades": d["trades"],
            "reason": f"best variant {bv} is "
                      f"{d['expectancy_after_costs_r']:+.3f}R after costs over "
                      f"{d['trades']} trades - does not clear +{EXP_BAND}R"}


def build_ranked(results, recs):
    """Rank channels: adequately-sampled first by best-variant expectancy
    after costs (desc), then the rest by best sample size (desc)."""
    adequate, rest = [], []
    for st in results:
        bv, bd = best_adequate(st)
        entry = {"id": int(st["id"]), "name": st["plain_name"],
                 "best_variant": bv,
                 "trades": bd["trades"] if bd else max(
                     st["variants"][v]["trades"] for v in VARIANTS),
                 "exp_after_costs_r": bd["expectancy_after_costs_r"] if bd else None,
                 "win_pct": bd["win_pct"] if bd else None,
                 "max_dd_r": bd["max_dd_r"] if bd else None,
                 "verdict": bd["verdict"] if bd else None,
                 "call": recs[int(st["id"])]["call"]}
        (adequate if bd else rest).append(entry)
    adequate.sort(key=lambda e: -e["exp_after_costs_r"])
    rest.sort(key=lambda e: -e["trades"])
    ranked = adequate + rest
    for i, e in enumerate(ranked, 1):
        e["rank"] = i
    return ranked


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
            f"{f'ALL {len(CHANNELS)} CHANNELS (pooled)':<24}{v:>4}{d['trades']:>7}"
            f"{fmt(d['win_pct'], '.1f'):>7}{fmt(d['avg_r'], '+.3f'):>8}"
            f"{fmt(d['expectancy_after_costs_r'], '+.3f'):>8}"
            f"{fmt(d['max_dd_r'], '.2f'):>7}  {d['verdict']}")
    return "\n".join(lines)


def md_row(cname, v, d):
    return (f"| {cname} | {v} | {d['trades']} | {fmt(d['win_pct'], '.1f')} "
            f"| {fmt(d['avg_r'], '+.3f')} "
            f"| {fmt(d['expectancy_after_costs_r'], '+.3f')} "
            f"| {fmt(d['max_dd_r'], '.2f')} | {d['verdict']} |")


def write_md(report, results, pooled, pooled_dedup, recs, ranked, clusters):
    """Write agent-reports/mass-verification.md FIRST (file is the primary
    deliverable), then the caller prints the console summary."""
    os.makedirs(os.path.dirname(REPORT_MD), exist_ok=True)
    nm = {int(s["id"]): s["name"] for s in results}  # id -> plain name
    L = []
    ap = L.append
    ap(f"# MASS VERIFICATION: {len(CHANNELS)} unverified watched channels x "
       "relay exit geometry (POLICY V2)")
    ap("")
    ap(f"_generated {report['generated_utc']} · engine: `channel_verify_mass.py` "
       "(read-only port of `channel_verify2.py` / `channel_verify_scout.py`) · "
       "full data: `mass-verification.json` · Telegram on `telethon-mass.session` "
       "(sqlite backup copy; live `telethon.session` never touched) · parser: "
       "current fixed `parser.py` (arrow-format TPs + emoji-adjacent SLs) · "
       "method per `agent-reports/exit-geometry.md`_")
    ap("")
    ap("## Channel set (the 14)")
    ap("")
    ap("Every channel in config.json `channels` NOT covered by any prior "
       "verification report (V1 `channel_report.json` / V2 "
       "`channel_report_v2.json` / V3 `channel_report_v3.json` / scout "
       "`scout-verification.json`): the 12 newly joined channels in "
       "`new_channels_batch.json` plus the 2 scout-shortlist incumbents that "
       "were being watched live without any simulation evidence.")
    ap("")
    ap("| # | channel | id | link | origin |")
    ap("|---:|---|---:|---|---|")
    for i, (cid, name, uname) in enumerate(CHANNELS, 1):
        origin = ("new batch (`new_channels_batch.json`)"
                  if int(cid) not in PRIOR else
                  "config incumbent, scout-channels-v2.md shortlist")
        ap(f"| {i} | {FALLBACK_NAMES[cid]} | `{cid}` | {uname} | {origin} |")
    ap("")
    ap("## Duplicate-content clusters (mirrors)")
    ap("")
    if clusters:
        ap("Several of the 14 channels post the SAME signals - identical "
           "(or near-identical, within one M15 bar) side, entry-bar open and "
           "outcome for every resolved trade, posted within ~1 min of each "
           "other. They are re-branded mirrors of one source, not "
           "independent evidence. The pooled rows below therefore report BOTH "
           "raw and DEDUPED stats (every unique signal counted once); at "
           "most ONE channel per cluster may ever be promoted, or every "
           "signal would execute twice.")
        ap("")
        ap("| cluster | mirror channels | shared resolved trades | leader (keep/promote this one) |")
        ap("|---|---|---:|---|")
        for i, c in enumerate(clusters, 1):
            parts = []
            for m in c["members"]:
                if m != c["leader"]:
                    parts.append(f"{nm[m]} (`{m}`)")
            for m in c["near_members"]:
                parts.append(f"{nm[m]} (`{m}`, near-mirror)")
            ap(f"| C{i} | {', '.join(parts)} | {c['n_trades']} | "
               f"{nm[c['leader']]} (`{c['leader']}`) |")
        ap("")
    else:
        ap("None detected: every channel's trade fingerprint is unique.")
        ap("")
    ap("## Question")
    ap("")
    ap("Does the raw DIRECTION of these 14 channels carry an edge when every "
       "trade is managed by the relay's own trailing exit (`manage.py`), all "
       "channel TPs ignored - i.e. should any of them be promoted from the "
       "default `shadow` signal_policy to a trading policy, and should any be "
       "removed from the watch list outright?")
    ap("")
    ap("## Method (identical to exit-geometry.md unless noted)")
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
       "= INSUFFICIENT DATA (verdict is tentative).")
    ap("- Calls: **PROMOTE** needs best adequate variant exp >= +"
       f"{EXP_BAND}R and n >= {MIN_SAMPLE}; **DEMOTE** (remove from config.json "
       f"`channels`) when the best adequate variant is <= -{EXP_BAND}R; "
       "**DUPLICATE** for mirror feeds (identical trade set as another watched "
       "channel - keep/promote at most ONE per cluster); everything else stays "
       "in the default `shadow` policy. All 14 channels "
       "are currently watched with `signal_policy._default = {\"mode\": "
       "\"shadow\"}` - nothing is auto-traded from them today.")
    ap("- Trades whose 48h window extends beyond available data are `pending` "
       "and excluded from stats. MT5 strictly read-only "
       "(copy_rates/symbol_info/symbol_info_tick/symbol_select only; no "
       "order_send).")
    ap("")
    ap(f"## Results: channel x variant ({len(CHANNELS)} channels)")
    ap("")
    ap("| channel | variant | trades | win% | avg R | exp after costs (R) "
       "| max DD (R) | verdict |")
    ap("|---|---|---:|---:|---:|---:|---:|---|")
    for s in results:
        for v in VARIANTS:
            ap(md_row(s["plain_name"], v, s["variants"][v]))
    for v in VARIANTS:
        d = pooled[v]
        ap(f"| **ALL {len(CHANNELS)} CHANNELS (pooled, raw)** | **{v}** | {d['trades']} | "
           f"{fmt(d['win_pct'], '.1f')} | {fmt(d['avg_r'], '+.3f')} | "
           f"{fmt(d['expectancy_after_costs_r'], '+.3f')} | "
           f"{fmt(d['max_dd_r'], '.2f')} | {d['verdict']} |")
    for v in VARIANTS:
        d = pooled_dedup[v]
        ap(f"| **ALL CHANNELS (pooled, DEDUPED - mirrors counted once)** | **{v}** | "
           f"{d['trades']} | {fmt(d['win_pct'], '.1f')} | "
           f"{fmt(d['avg_r'], '+.3f')} | "
           f"{fmt(d['expectancy_after_costs_r'], '+.3f')} | "
           f"{fmt(d['max_dd_r'], '.2f')} | {d['verdict']} |")
    ap("")
    ap(f"## Ranked (best variant per channel, expectancy after costs)")
    ap("")
    ap("| # | channel | id | A: n / exp | B: n / exp | best | best exp (R) | "
       "verdict | call |")
    ap("|---:|---|---:|---|---|---|---:|---|---|")
    for e in ranked:
        st = next(s for s in results if int(s["id"]) == e["id"])
        a, b = st["variants"]["A"], st["variants"]["B"]
        ap(f"| {e['rank']} | {e['name']} | `{e['id']}` "
           f"| {a['trades']} / {fmt(a['expectancy_after_costs_r'], '+.3f')} "
           f"| {b['trades']} / {fmt(b['expectancy_after_costs_r'], '+.3f')} "
           f"| {fmt(e['best_variant'])} "
           f"| {fmt(e['exp_after_costs_r'], '+.3f')} "
           f"| {fmt(e['verdict'])} | {e['call']} |")
    ap("")
    ap("## Recommendations (promote / shadow / demote)")
    ap("")
    for s in results:
        r = recs[int(s["id"])]
        ap(f"### {s['name']} (`{s['id']}`)")
        ap("")
        if r["call"] == "PROMOTE":
            ap(f"- **CALL: PROMOTE to trading policy - variant "
               f"{r['winning_variant']}** ({r['reason']}).")
            ap(f"- Policy params: `{json.dumps(r['params'])}` "
               "(sl_mode/atr_mult/tp_mode per config.json signal_policy "
               "schema); exits via manage.py: BE at +1R (10pt buffer), "
               "trail 0.5R from +1.5R, 48h horizon, 0.07R costs assumed.")
        elif r["call"].startswith("DEMOTE"):
            ap(f"- **CALL: DEMOTE - remove from config.json `channels`** "
               f"({r['reason']}).")
        elif r["call"].startswith("DUPLICATE"):
            ap(f"- **CALL: DUPLICATE - mirror of "
               f"{nm[r.get('duplicate_of')]} (`{r.get('duplicate_of')}`)** - "
               f"{r['reason']}")
            ap("- Action: keep at most one channel of the cluster in "
               "config.json `channels`; if the leader is promoted, remove "
               "this mirror (or keep it shadow) - never promote both.")
        else:
            ap(f"- **CALL: STAY SHADOW** - {r['reason']}.")
        if s.get("error"):
            ap(f"- **channel error during fetch: {s['error']}**")
        ap(f"- Prior evidence: {PRIOR.get(int(s['id']), NO_PRIOR)}.")
        ap("")
    ap("## Per-channel detail")
    ap("")
    for s in results:
        ap(f"### {s['name']} (`{s['id']}`)")
        ap("")
        ap(f"- messages {s['messages']} (media-only {s['media_only']}, "
           f"recaps {s['recap_posts']}, unparseable {s['unparseable'] + s['unverifiable']}, "
           f"stale {s['stale']}, no-data {s['no_data']}, pending-no-bar {s['pending']})"
           + (f" **ERROR: {s['error']}**" if s.get("error") else ""))
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
    ap(f"- Samples are one ~{MSG_LIMIT}-message window per channel; n between "
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
    ap("- Read-only guarantees: `telethon.session` never opened for connect "
       "and never written (research ran on `telethon-mass.session`); MT5 "
       "never sent an order; no existing file modified; config.json "
       "read-only; no process started or stopped. Created: "
       "`channel_verify_mass.py`, `telethon-mass.session` (+journal), "
       "`mass-verification.json`, `agent-reports/mass-verification.md`.")
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
                print("mass-verify session NOT authorized (copy failed?)")
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

    # stash RAW per-channel trades BEFORE finalize (finalize pops them);
    # each trade keeps its content key (side, entry-bar open, R) so the
    # pooled-dedup pass can count every unique signal exactly once
    raw_by_channel = {}
    for st in results:
        cid = int(st["id"])
        raw_by_channel[cid] = {}
        for v in VARIANTS:
            ordered = list(st["variants"][v]["ordered"])  # (entry_epoch, r)
            tr = []
            for s in st["signals"]:
                d = (s.get("variants") or {}).get(v)
                if d and d.get("r") is not None:
                    tr.append({"key": (s["side"], s.get("sim_entry"),
                                       round(d["r"], 3)),
                               "r": d["r"], "cls": d.get("outcome"),
                               "epoch": None})
            if len(tr) != len(ordered):  # cannot happen by construction
                note = f"internal: {v} tally misalign {len(tr)} vs {len(ordered)}"
                st["error"] = f"{st['error']} | {note}" if st.get("error") else note
                ordered = [(0, t["r"]) for t in tr]
            for t, (ep, _r) in zip(tr, ordered):
                t["epoch"] = ep
            raw_by_channel[cid][v] = {
                "trades": tr,
                "pending": st["variants"][v]["pending"],
                "no_atr": st["variants"][v]["no_atr"]}

    # finalize per-channel variant stats, then recommendations
    for st in results:
        for v in VARIANTS:
            finalize_variant(st["variants"][v])
    pooled = {v: finalize_variant(pooled_raw[v]) for v in VARIANTS}

    # duplicate-content clusters -> per-channel calls + deduped pooled stats
    clusters, cmap = build_clusters(results)
    recs = {int(st["id"]): recommend_channel(st) for st in results}
    name_by_id = {int(st["id"]): st["name"] for st in results}
    kinfo = {int(st["id"]): (trade_keyset(st, "A"), trade_keyset(st, "B"))
             for st in results}
    for st in results:
        cid = int(st["id"])
        c = cmap.get(cid)
        st["duplicate_of"] = (c["leader"] if (c and cid != c["leader"]) else None)
        if c:
            st["duplicate_cluster_members"] = c["all_members"]
        if not c:
            continue
        leader_name = name_by_id[c["leader"]]
        if cid == c["leader"]:
            mirrors = [f"{name_by_id[m]} (`{m}`)" for m in c["all_members"]
                       if m != cid]
            recs[cid]["reason"] += (
                f" NOTE: content is mirrored by {c['n_channels'] - 1} other "
                f"watched channel(s) ({', '.join(mirrors)}); promote at most "
                "ONE channel of this cluster.")
        else:
            base = recs[cid]
            ka, kl = kinfo[cid][0], kinfo[c["leader"]][0]
            if ka == kl and kinfo[cid][1] == kinfo[c["leader"]][1]:
                kind = (f"identical trade set (same {c['n_trades']} resolved "
                        "signals, same side/entry/outcome)")
            else:
                kind = (f"near-identical trade set ({len(ka & kl)} of "
                        f"{len(ka)} resolved signals shared)")
            recs[cid] = {
                "call": "DUPLICATE (mirror feed)",
                "winning_variant": None, "params": None,
                "exp_after_costs_r": base.get("exp_after_costs_r"),
                "trades": base.get("trades"),
                "duplicate_of": c["leader"],
                "reason": f"{kind} with {leader_name} (`{c['leader']}`) - "
                          "the same content re-branded; NOT independent "
                          "evidence. Keep at most ONE channel of this "
                          "cluster in config.json; if the leader is "
                          "promoted, do NOT also add this mirror (every "
                          "signal would execute twice)."}

    # deduped pooled: every UNIQUE trade (content key) counted exactly once
    # across all 14 channels - mirrors never double-count evidence
    dedup_raw = {v: {"r_list": [], "ordered": [],
                     "classes": {"sl": 0, "be": 0, "trail": 0, "timeout": 0},
                     "pending": 0, "no_atr": 0} for v in VARIANTS}
    seen = {v: set() for v in VARIANTS}
    for st in results:  # results order = CHANNELS order (deterministic)
        src = raw_by_channel[int(st["id"])]
        for v in VARIANTS:
            dst, sv = dedup_raw[v], seen[v]
            for t in src[v]["trades"]:
                if t["key"] in sv:
                    co

... (truncated, 57150 total bytes) ...


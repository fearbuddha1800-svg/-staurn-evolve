"""Channel signal forensics engine (READ-ONLY).

Replays the watched Telegram signal channels' historical messages through the
relay's own deterministic parser (parser.parse_signal), then simulates every
verifiable signal against REAL MT5 M15 history (MetaQuotes-Demo) to compute the
honest win rate per channel.

Rules (per audit spec):
  - fetch last ~300 messages per watched channel (config.json 'channels')
  - recap posts ('tp hit' / 'pips' language): counted, never simulated
  - keep only parse_ok, non-manage signals with SL + >=1 TP + numeric entry
  - STALE = stated entry more than 1% away from the market price at signal time
  - market entry at the open of the first M15 bar after signal time, then walk
    bars for 24h from entry: SL touched first (or SL+TP same bar) = LOSS (-1R);
    TP1 (nearest TP in trade direction) first = WIN (+R, R=tp_dist/sl_dist);
    neither = TIMEOUT (exit at last close, partial +/-R)
  - verbatim server-time handling: MT5 bar/tick epochs are SERVER wall time
    treated as UTC. Offset determined ONCE from the freshest tick (XAUUSD feed
    was stale/frozen at audit time, so its tick alone under-reports the offset).

Strictly read-only for MT5: initialize/shutdown + market-data reads only. Never
order_send, never positions_get, no trades, no existing file edited. Telegram
works on a COPY of the live session (telethon-verify.session) so the running
daemon is never contended.

Creates only: channel_report.json (+ telethon-verify.session files).
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

LIVE_SESSION = os.path.join(BASE, "telethon.session")
SESSION = os.path.join(BASE, "telethon-verify.session")
REPORT = os.path.join(BASE, "channel_report.json")

# watched channels (config.json 'channels') + known names for the report
CHANNELS = {
    -1002369502254: "Best Signal Forex",
    -1002692333123: "XAUUSD PRO SIGNAL",
    -1001920020352: "Grow Trading",
    -1002165799093: "XAUUSD FREE SIGNALS",
    -1001284268486: "Easy Forex OFFICIAL",
}

MSG_LIMIT = 300          # last ~300 messages per channel
LOOKBACK_S = 8 * 3600    # bars fetched before signal time (price-at-signal ref)
FORWARD_S = 80 * 3600    # bars fetched after signal (weekend gap + 24h walk)
HORIZON_S = 24 * 3600    # trade must resolve within 24h from simulated entry
M15 = 900
STALE_FRAC = 0.01        # >1% away from price at signal time = stale re-post
MIN_SAMPLE = 10
COST_R = 0.07            # round-trip cost haircut per trade, same as relay's backtest.py
RECAP_PATTERNS = ("tp hit", "pips")
OFFSET_SYMBOLS = ("XAUUSD", "EURUSD", "GBPUSD", "US30", "XAGUSD", "AUDUSD")

_selected_symbols = set()  # symbols we had to symbol_select() for data access


# ---------------------------------------------------------------- session copy
def copy_session():
    """Copy telethon.session -> telethon-verify.session WITHOUT contending the
    live daemon: prefer the sqlite backup API (lock-safe), fall back to file copy.
    The -journal is copied too if present."""
    for junk in (SESSION, SESSION + "-journal"):
        if os.path.exists(junk):
            os.remove(junk)  # only ever removes OUR verify copies
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
    print(f"session copy ready: {SESSION} ({os.path.getsize(SESSION)} bytes)")


# ------------------------------------------------------------------ mt5 helpers
def compute_server_offset():
    """Determine the MT5 server-time offset ONCE. Spec method is
    symbol_info_tick('XAUUSD').time vs now, but XAUUSD's demo feed can be
    frozen (it was at audit time), which under-reports the offset by the tick
    age. Server epochs are real epoch + offset for EVERY symbol, so the
    FRESHEST tick across liquid symbols is the correct estimator."""
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
        # same pre-trade; this is market-watch state, not a trade)
        if mt5.symbol_info(sym) is None:
            mt5.symbol_select(sym, True)
            _selected_symbols.add(sym)
            r = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M15, int(t_from), int(t_to))
    return r


def to_utc_epoch(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)  # telethon returns UTC
    return dt.timestamp()


def simulate(bars, tarr, k, side, sl, tp1, sl_dist, entry):
    """Walk M15 bars from entry bar k. SL-first when both touched in one bar
    (conservative, same convention as the relay's own backtest). Returns
    (outcome, r, exit_price, exit_srv_epoch)."""
    horizon = int(tarr[k]) + HORIZON_S  # 24h from simulated entry
    end = k
    for idx in range(k, len(tarr)):
        if tarr[idx] >= horizon:
            break
        end = idx
        hi, lo = bars[idx]["high"], bars[idx]["low"]
        if side == "buy":
            sl_hit, tp_hit = lo <= sl, (tp1 is not None and hi >= tp1)
        else:
            sl_hit, tp_hit = hi >= sl, (tp1 is not None and lo <= tp1)
        if sl_hit:
            return "loss", -1.0, sl, int(tarr[idx])
        if tp_hit:
            return "win", abs(tp1 - entry) / sl_dist, tp1, int(tarr[idx])
    if tarr[-1] < horizon:
        # data does not reach past the horizon -> trade still open/unresolvable
        return "pending", None, None, None
    exit_px = float(bars[end]["close"])
    pr = ((exit_px - entry) if side == "buy" else (entry - exit_px)) / sl_dist
    return "timeout", pr, exit_px, int(tarr[end]) + M15


# --------------------------------------------------------------- channel audit
async def analyze_channel(client, cid, fallback_name, offset):
    st = {
        "id": cid, "name": fallback_name, "plain_name": fallback_name,
        "messages": 0, "media_only": 0,
        "not_signal": 0, "unparseable": 0, "unverifiable": 0, "recap_posts": 0,
        "no_data": 0, "pending": 0, "degenerate": 0, "stale": 0,
        "wins": 0, "losses": 0, "timeouts": 0, "r_list": [], "signals": [],
        "error": None,
    }
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
            rec = {"msg_id": m.id, "date_utc": m.date.replace(tzinfo=timezone.utc).isoformat() if m.date.tzinfo is None else m.date.isoformat(),
                   "raw_symbol": raw_sym, "resolved": sym, "side": parsed["action"],
                   "entry": entry, "sl": sl, "tps": tps}
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
            sl_dist = abs(sim_entry - sl)
            if sl_dist <= 0:
                st["degenerate"] += 1
                rec["outcome"] = "degenerate_sl_eq_entry"
                st["signals"].append(rec)
                continue
            # TP1 = nearest TP in the trade's direction from the simulated fill
            if side == "buy":
                cands = [t for t in tps if t > sim_entry]
                tp1 = min(cands) if cands else None
            else:
                cands = [t for t in tps if t < sim_entry]
                tp1 = max(cands) if cands else None
            rec["sim_entry"] = round(sim_entry, 5)
            rec["tp1"] = tp1

            outcome, r, exit_px, exit_t = simulate(bars, tarr, k, side, sl, tp1,
                                                   sl_dist, sim_entry)
            if outcome == "pending":
                st["pending"] += 1
            else:
                key = {"win": "wins", "loss": "losses", "timeout": "timeouts"}[outcome]
                st[key] += 1
                st["r_list"].append(r)
            rec["outcome"] = outcome
            rec["r"] = round(r, 3) if r is not None else None
            rec["exit"] = round(exit_px, 5) if exit_px is not None else None
            if exit_t is not None:
                rec["exit_time_server"] = datetime.utcfromtimestamp(exit_t).isoformat() + "+srv"
            st["signals"].append(rec)
    except Exception as e:  # noqa: BLE001
        st["error"] = f"{type(e).__name__}: {e}"
    return st


def finalize(st, offset):
    sim = st["wins"] + st["losses"] + st["timeouts"]
    checked = sim + st["stale"]
    wins = st["wins"]
    win_pct = (100.0 * wins / sim) if sim else None
    win_pct_all = (100.0 * wins / checked) if checked else None
    net_r = round(sum(st["r_list"]), 2)
    avg_r = round(net_r / sim, 3) if sim else None
    exp_cost = round(avg_r - COST_R, 3) if avg_r is not None else None
    dates = [s.get("date_utc") for s in st["signals"] if s.get("date_utc")]
    st.update(simulated=sim, checked=checked, win_pct=win_pct,
              win_pct_incl_stale=win_pct_all, net_r=net_r, avg_r=avg_r,
              expectancy_after_costs_r=exp_cost,
              first_signal_utc=min(dates) if dates else None,
              last_signal_utc=max(dates) if dates else None)
    # verdict: economically honest - a high win% with tiny avg R is cosmetic,
    # because these channels set TP1 much closer than the SL.
    v, extra = "", []
    if sim < MIN_SAMPLE:
        v = f"INSUFFICIENT DATA: only {sim} verifiable signal(s) (<{MIN_SAMPLE}) - too few to judge"
    if sim:
        w, a = win_pct or 0.0, avg_r or 0.0
        if a >= 0.25 and w >= 50:
            tag = "GOOD"
        elif a >= 0 or w >= 35:
            tag = "MEDIOCRE"
        else:
            tag = "BAD"
        if w >= 55 and 0 <= a < 0.25:
            extra.append(f"win% is cosmetic: avg win only {a}R (TP1 set far closer than SL)")
        if exp_cost is not None and exp_cost < 0 <= avg_r:
            extra.append(f"expectancy negative after {COST_R}R/trade costs ({exp_cost}R)")
        if sim < MIN_SAMPLE:
            v += f" - tentatively {tag.lower()}"
        else:
            v = tag
        if avg_r is not None and avg_r < 0 and sim >= MIN_SAMPLE:
            extra.append(f"net {net_r}R over {sim} trades")
        if st["stale"] >= max(5, 0.25 * checked) and st["stale"] > 0:
            pct = round(100.0 * st["stale"] / checked, 1) if checked else 0
            extra.append(f"STALE-POSTER ({st['stale']}/{checked} = {pct}% old-trade re-posts)")
        if st["recap_posts"] >= 10 and st["recap_posts"] > checked:
            extra.append(f"RECAP-HEAVY ({st['recap_posts']} self-reported result posts "
                         f"vs {checked} checkable signals)")
    else:
        v = v or "INSUFFICIENT DATA: 0 verifiable signals"
        if st["unparseable"] + st["unverifiable"] > 0:
            extra.append(f"{st['unparseable'] + st['unverifiable']} signal-like messages, "
                         "none complete (SL+TP+entry)")
    if extra:
        v += " | " + " | ".join(extra)
    st["verdict"] = v
    return st


async def run():
    copy_session()
    if not initialize_existing(mt5):
        print("MT5 connection unavailable:", broker_status())
        return 1
    print("MT5 attached (read-only):", mt5.account_info().server)
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
                print("verify session NOT authorized (copy failed?)")
                return 1
            me = await client.get_me()
            print(f"Telegram: logged in as {me.first_name} (@{me.username})")
            results = []
            for cid, name in CHANNELS.items():
                print(f"--- auditing {name} ({cid}) ...")
                st = await analyze_channel(client, cid, name, offset)
                results.append(finalize(st, offset))
        finally:
            await client.disconnect()
    finally:
        mt5.shutdown()
        print("MT5 shutdown (connection closed; terminal untouched)")

    for st in results:
        st.pop("r_list", None)

    # rank: adequate-sample channels first, then by win%, then avg R
    results.sort(key=lambda s: (s["simulated"] >= MIN_SAMPLE,
                                 s["win_pct"] if s["win_pct"] is not None else -1,
                                 s["avg_r"] if s["avg_r"] is not None else -99), reverse=True)

    hdr = (f"{'channel':<26}{'checked':>8}{'W':>5}{'L':>5}{'T':>5}"
           f"{'win%':>8}{'avgR':>7}{'stale':>7}{'recaps':>8}  VERDICT")
    lines = [hdr, "-" * len(hdr)]
    for s in results:
        wp = f"{s['win_pct']:.1f}" if s["win_pct"] is not None else "-"
        ar = f"{s['avg_r']:.2f}" if s["avg_r"] is not None else "-"
        lines.append(
            f"{s['plain_name'][:25]:<26}{s['checked']:>8}{s['wins']:>5}{s['losses']:>5}"
            f"{s['timeouts']:>5}{wp:>8}{ar:>7}{s['stale']:>7}{s['recap_posts']:>8}"
            f"  {s['verdict']}")
    print()
    print("\n".join(lines))

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "method": {
            "messages_per_channel": MSG_LIMIT,
            "parser": "relay's own parser.parse_signal (deterministic, no AI fallback)",
            "keep_filter": "parse_ok, non-manage, has SL, >=1 TP, numeric entry",
            "timeframe": "M15", "horizon": "24h from simulated entry",
            "entry": "open of first M15 bar at/after signal time (market entry)",
            "same_bar_rule": "SL checked before TP (conservative)",
            "tp1": "nearest TP in trade direction from simulated fill",
            "timeout": "exit at last close within window, partial +/-R recorded",
            "stale": "stated entry >1% away from price at signal time (bar covering signal)",
            "recap": "messages containing 'tp hit' or 'pips' counted, never simulated",
            "win_pct": "wins/(wins+losses+timeouts) over resolved trades; "
                       "win_pct_incl_stale also reported",
            "costs": "table R is gross; expectancy_after_costs_r subtracts "
                     f"{COST_R}R/trade round-trip cost (the relay's own backtest.py haircut)",
            "verdict_rules": "GOOD: avg_r>=0.25 & win%>=50; MEDIOCRE: breakeven-ish "
                             "(avg_r>=0 or win%>=35); BAD: losing on both; "
                             "channels with <10 verifiable signals are flagged unverifiable",
            "server_offset_s": round(offset),
            "server_offset_method": "freshest tick across " + "/".join(OFFSET_SYMBOLS),
            "tick_times_at_audit": per_symbol_ticks,
            "note_xauusd_feed": ("XAUUSD demo feed was frozen at audit time "
                                 "(last tick server 22:59:59) - its tick alone "
                                 "under-reports the offset; freshest symbol used"),
            "symbols_selected_for_data": sorted(_selected_symbols),
            "media_only_not_parsed": "image-only messages counted, not OCR-parsed",
        },
        "channels": results,
    }
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nreport saved: {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run()))

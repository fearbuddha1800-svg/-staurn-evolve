---
slug: channel_verify3
type: note
graph: gitnexus
---

"""FULL CHANNEL SWEEP engine v3 (READ-ONLY): inventory -> triage -> deep verify.

Sweeps EVERY dialog the account can see (main folder AND archived) to find the
best Telegram signal sources for the relay, then deep-verifies the promising
ones with the PROVEN V2 exit-geometry pipeline.

Stages (run separately or 'all'):
  scan     STEP 0+1+2: sqlite-backup copy of telethon.session ->
           telethon-scan.session (the live session is NEVER connected), full
           dialog inventory via iter_dialogs(limit=None) AND
           iter_dialogs(limit=None, archived=True), exclusion of bots
           (GMGN*, BotFather, @hermes_*), own channels and the 'Signal Relay
           Feed' output channel, then cheap triage (~200 msgs per chat through
           parser.parse_signal + ai_filter.looks_like_results). Ranked by
           (complete signals, parse rate, freshness) ->
           scan-inventory.json FIRST, then agent-reports/scan-inventory.md.
  verify   STEP 3: every chat with >= 8 complete signals gets the V2
           exit-geometry verification EXACTLY per agent-reports/
           exit-geometry.md, by reusing channel_verify2's proven engine
           verbatim (300-msg fetch, recap skip, keep-filter, stale screen,
           market entry at first M15 bar at/after signal, variant A = stated
           SL / variant B = 2xATR(14) Wilder, ALL channel TPs ignored,
           BE at +1R (+10pt buffer), 0.5R trail from +1.5R, ratchet-only,
           48h walk, conservative same-bar rule, 0.07R costs) ->
           channel_report_v3.json.
  report   STEP 4: agent-reports/full-sweep.md - ranked table of ALL verified
           chats (expectancy after costs per variant, verdict) + explicit
           recommendations: which ids to add to config.json channels +
           signal_policy entries with validated parameters, which stay in
           shadow mode.

Read-only guarantees identical to the proven pipeline: telethon.session is
only ever opened read-only (sqlite backup API) and never connected; MT5 is
initialize/shutdown + copy_rates/symbol_info/symbol_info_tick/symbol_select
ONLY - order_send is never called anywhere; config.json is read, never
written; no existing file is modified; no channel is joined; no process is
started or stopped. Creates only: channel_verify3.py's own outputs -
scan-inventory.json, agent-reports/scan-inventory.md, channel_report_v3.json,
agent-reports/full-sweep.md, telethon-scan.session (+ -journal).
"""
from broker_lifecycle import initialize_existing, broker_status
import argparse
import asyncio
import json
import os
import re
import shutil
import sqlite3
import sys
import time
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)
sys.dont_write_bytecode = True  # never touch __pycache__
if BASE not in sys.path:
    sys.path.insert(0, BASE)

import ai_filter            # noqa: E402  (looks_like_results recap screen)
import daemon               # noqa: E402  (daemon._env_creds() ONLY; main() never runs)
import parser as sigparser  # noqa: E402  (relay's own deterministic parser)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

LIVE_SESSION = os.path.join(BASE, "telethon.session")       # live daemon's - NEVER connected
SESSION      = os.path.join(BASE, "telethon-scan.session")  # our private scan copy
SCAN_JSON    = os.path.join(BASE, "scan-inventory.json")
SCAN_MD      = os.path.join(BASE, "agent-reports", "scan-inventory.md")
REPORT_V3    = os.path.join(BASE, "channel_report_v3.json")
FULL_MD      = os.path.join(BASE, "agent-reports", "full-sweep.md")
V2_REPORT    = os.path.join(BASE, "channel_report_v2.json")
V1_REPORT    = os.path.join(BASE, "channel_report.json")
CFG_JSON     = os.path.join(BASE, "config.json")

OWN_FEED_ID = -1004403985547          # 'Signal Relay Feed' - the relay's own output channel
BOT_USERNAME_RE = re.compile(r"(?i)^(gmgn.*|botfather|hermes_.*)$")
BOT_TITLE_RE    = re.compile(r"(?i)^(gmgn[\s_\-\.].*|bot\s*father|hermes_.*)$")

MSG_LIMIT_SCAN = 200        # cheap triage window per chat (~200 per spec)
VERIFY_MIN_COMPLETE = 8     # deep-verify gate: complete signals in triage window
RECAP_PATTERNS = ("tp hit", "pips")   # proven pipeline recap screen (V1/V2)
FLOOD_SLEEP = 240           # auto-sleep through flood waits up to this many s
MIN_SAMPLE = 10             # adequate-sample bar (same as V1/V2)
EXP_BAND = 0.05             # |expectancy after costs| < 0.05R -> FLAT


# ---------------------------------------------------------------- session copy
def copy_session(force=False):
    """STEP 0: copy telethon.session (+ -journal) -> telethon-scan.session via
    the sqlite backup API (the live session is only ever OPENED READ-ONLY,
    never connected). Skipped if our copy already exists, unless --force."""
    if os.path.exists(SESSION) and not force:
        print(f"scan session already present: {SESSION} "
              f"({os.path.getsize(SESSION)} bytes)")
        return
    for junk in (SESSION, SESSION + "-journal"):
        if os.path.exists(junk):
            os.remove(junk)  # only ever removes OUR scan copies
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
    print(f"scan session copy ready: {SESSION} ({os.path.getsize(SESSION)} bytes)")


async def connect():
    api_id, api_hash = daemon._env_creds()
    if not (api_id and api_hash):
        raise RuntimeError("no Telegram api credentials via daemon._env_creds()")
    from telethon import TelegramClient
    client = TelegramClient(SESSION, api_id, api_hash)
    client.flood_sleep_threshold = FLOOD_SLEEP
    try:
        await client.connect()
        ok = await client.is_user_authorized()
    except sqlite3.DatabaseError as e:
        print(f"sqlite error on connect ({e}); retrying WITHOUT the copied -journal")
        j = SESSION + "-journal"
        if os.path.exists(j):
            os.remove(j)  # our copy only
        client = TelegramClient(SESSION, api_id, api_hash)
        client.flood_sleep_threshold = FLOOD_SLEEP
        await client.connect()
        ok = await client.is_user_authorized()
    if not ok:
        raise RuntimeError("scan session NOT authorized (copy failed?)")
    me = await client.get_me()
    print(f"Telegram: logged in as {me.first_name} (@{me.username}) id={me.id}")
    return client, me


def _iso(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


# ------------------------------------------------------------------ inventory
def classify(me_id, d, ent, cid):
    """-> (chat_type, excluded, reason). Excludes bots (entity flag, GMGN*/
    BotFather/@hermes_* patterns), the account's own chats/channels and the
    relay's own output feed. Everything else is swept."""
    uname = (getattr(ent, "username", None) or "").strip()
    title = str(d.name or getattr(ent, "title", "") or uname or cid)
    if cid == me_id:
        return "user-self", True, "own: Saved Messages (self chat)"
    if cid == OWN_FEED_ID:
        return "channel", True, "own: Signal Relay Feed (relay output channel)"
    if getattr(ent, "bot", False):
        return "bot", True, f"bot: @{uname or title}"
    if uname and BOT_USERNAME_RE.match(uname):
        return "bot", True, f"bot (username pattern): @{uname}"
    if BOT_TITLE_RE.match(title):
        return "bot", True, f"bot (title pattern): {title}"
    if getattr(ent, "megagroup", None) is not None:  # Channel entity
        ctype = "megagroup" if ent.megagroup else "channel"
        if getattr(ent, "creator", False):
            return ctype, True, f"own channel/group (creator flag): {title}"
        return ctype, False, None
    if d.is_user:
        return "user", False, None
    if d.is_group:
        return "group", False, None
    return "unknown", False, None


async def stage_inventory(client, me):
    """STEP 1: every dialog from BOTH iter_dialogs calls, deduped by id."""
    seen = {}
    async for d in client.iter_dialogs(limit=None):
        seen[int(d.id)] = d
    n_main = len(seen)
    async for d in client.iter_dialogs(limit=None, archived=True):
        seen.setdefault(int(d.id), d)
    print(f"inventory: {n_main} dialogs from main pass, "
          f"{len(seen)} unique after archived pass")
    chats = []
    for cid, d in seen.items():
        ent = getattr(d, "entity", None)
        ctype, excluded, reason = classify(me.id, d, ent, cid)
        uname = (getattr(ent, "username", None) or "").strip()
        chats.append({
            "id": cid,
            "title": str(d.name or getattr(ent, "title", "") or uname or cid),
            "type": ctype,
            "archived": bool(d.archived),
            "username": uname or None,
            "participants": getattr(ent, "participants_count", None),
            "excluded": excluded,
            "exclude_reason": reason,
        })
    return chats


# --------------------------------------------------------------------- triage
async def triage_chat(client, rec):
    """STEP 2 (cheap): ~200 msgs through parser.parse_signal +
    ai_filter.looks_like_results. Headline 'complete' follows the proven
    pipeline flow verbatim (media -> recap skip 'tp hit'/'pips' -> parse ->
    parse_ok + non-manage + SL + >=1 TP + numeric entry)."""
    st = {
        "messages": 0, "media_only": 0, "recap_posts": 0, "ai_recap_posts": 0,
        "is_signal": 0, "parse_ok": 0, "manage": 0, "incomplete": 0,
        "complete": 0, "complete_raw": 0,
        "first_msg_utc": None, "last_msg_utc": None, "span_days": None,
        "signals_per_day": None, "parse_rate": None,
        "complete_newest_utc": None, "complete_oldest_utc": None,
        "symbols": {}, "sides": {}, "error": None,
    }
    newest = oldest = None
    try:
        async for m in client.iter_messages(int(rec["id"]), limit=MSG_LIMIT_SCAN):
            st["messages"] += 1
            d = m.date
            if d is not None:
                if newest is None or d > newest:
                    newest = d
                if oldest is None or d < oldest:
                    oldest = d
            text = (m.message or "").strip()
            if not text:
                st["media_only"] += 1
                continue
            if ai_filter.looks_like_results(text):
                st["ai_recap_posts"] += 1
            parsed = sigparser.parse_signal(text)
            act = parsed.get("action")
            if parsed.get("is_signal"):
                st["is_signal"] += 1
            if parsed.get("parse_ok"):
                st["parse_ok"] += 1
            if act == "manage":
                st["manage"] += 1
            sl = parsed.get("sl")
            tps = parsed.get("tps") or []
            entry = parsed.get("entry")
            complete_raw = (bool(parsed.get("parse_ok")) and act in ("buy", "sell")
                            and sl is not None and len(tps) >= 1
                            and isinstance(entry, float))
            if complete_raw:
                st["complete_raw"] += 1
                sym = parsed.get("symbol") or "?"
                st["symbols"][sym] = st["symbols"].get(sym, 0) + 1
                st["sides"][act] = st["sides"].get(act, 0) + 1
                if st["complete_newest_utc"] is None:  # iter runs newest->oldest
                    st["complete_newest_utc"] = _iso(d)
                st["complete_oldest_utc"] = _iso(d)
            low = text.lower()
            if any(p in low for p in RECAP_PATTERNS):
                st["recap_posts"] += 1
                continue
            if complete_raw:
                st["complete"] += 1
            elif parsed.get("is_signal") and act in ("buy", "sell"):
                st["incomplete"] += 1
    except Exception as e:  # noqa: BLE001
        st["error"] = f"{type(e).__name__}: {e}"
    if newest and oldest and newest > oldest:
        span_s = (newest - oldest).total_seconds()
    else:
        span_s = 0.0
    st["span_days"] = round(span_s / 86400.0, 3) if st["messages"] else None
    if st["complete"]:
        st["signals_per_day"] = round(
            st["complete"] * 86400.0 / max(span_s, 3600.0), 2)
    else:
        st["signals_per_day"] = 0.0
    st["parse_rate"] = (round(st["parse_ok"] / st["is_signal"], 3)
                        if st["is_signal"] else None)
    return st


def rank_included(chats):
    """Rank by (complete desc, parse rate desc, freshness desc) - stable
    multi-pass sort."""
    inc = [c for c in chats if not c["excluded"]]
    inc.sort(key=lambda c: c.get("last_msg_utc") or "", reverse=True)
    inc.sort(key=lambda c: -(c.get("parse_rate") or 0.0))
    inc.sort(key=lambda c: -int(c.get("complete") or 0))
    for i, c in enumerate(inc, 1):
        c["rank"] = i
    return inc


def fmt(x, spec=None, dash="-"):
    if x is None:
        return dash
    if spec is None:
        return str(x)
    return format(x, spec)


def write_scan_md(scan):
    os.makedirs(os.path.dirname(SCAN_MD), exist_ok=True)
    L = []
    ap = L.append
    ap("# FULL CHANNEL SWEEP - inventory + cheap triage (SCAN)")
    ap("")
    ap(f"_generated {scan['generated_utc']} · engine: `channel_verify3.py` "
       "(read-only) · full data: `scan-inventory.json` · Telegram ran on "
       "`telethon-scan.session`, a sqlite-backup copy of the live "
       "`telethon.session` (live session never connected, never written)_")
    ap("")
    ap("## Method")
    ap("")
    ap(f"- Inventory: `iter_dialogs(limit=None)` AND "
       f"`iter_dialogs(limit=None, archived=True)`, deduped by id - main "
       f"folder AND archive.")
    ap(f"- Excluded: bots (entity bot flag / GMGN* / BotFather / @hermes_*), "
       f"the account's own chats+channels (creator flag, Saved Messages) and "
       f"the relay's own output channel 'Signal Relay Feed' "
       f"(`{OWN_FEED_ID}`).")
    ap(f"- Triage: last {MSG_LIMIT_SCAN} messages per chat, every text "
       "through the relay's own `parser.parse_signal` + "
       "`ai_filter.looks_like_results` (no MT5, no network writes).")
    ap("- **complete** = the proven pipeline's keep-filter on this window: "
       "non-recap ('tp hit'/'pips' skipped, counted as `recaps`), parse_ok, "
       "non-manage, has SL, >=1 TP, numeric entry. `raw` adds the same "
       "count WITHOUT the recap screen. `ai-recap` counts "
       "`looks_like_results` hits (wider net).")
    ap("- `sig/day` = complete * 86400 / window-seconds (window floored at "
       "1h). Ranked by complete -> parse rate (parse_ok/is_signal) -> "
       "freshness (newest message).")
    ap("")
    ap(f"Dialogs inventoried: **{scan['dialogs_total']}** - excluded "
       f"**{scan['excluded_total']}**, triaged **{scan['triaged_total']}** "
       f"(candidates for deep verification, complete >= "
       f"{VERIFY_MIN_COMPLETE}: **{len(scan['verify_candidates'])}**).")
    ap("")
    ap("## Excluded dialogs")
    ap("")
    ap("| chat | id | type | archived | reason |")
    ap("|---|---:|---|---|---|")
    for c in scan["chats"]:
        if c["excluded"]:
            ap(f"| {c['title'][:40]} | {c['id']} | {c['type']} "
               f"| {'yes' if c['archived'] else 'no'} | {c['exclude_reason']} |")
    ap("")
    ap("## Triage table (all swept chats, ranked)")
    ap("")
    ap("| # | chat | id | type | arch | msgs | complete | raw | is_sig | "
       "parse_ok | rate | manage | recaps | ai-recap | media | sig/day | "
       "last message (UTC) | err |")
    ap("|---:|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
       "---:|---:|---:|---|---|")
    for c in scan["chats"]:
        if c["excluded"]:
            continue
        ap(f"| {c['rank']} | {c['title'][:36]} | {c['id']} | {c['type']} "
           f"| {'A' if c['archived'] else '-'} | {c['messages']} "
           f"| {c['complete']} | {c['complete_raw']} | {c['is_signal']} "
           f"| {c['parse_ok']} | {fmt(c['parse_rate'], '.2f')} | {c['manage']} "
           f"| {c['recap_posts']} | {c['ai_recap_posts']} | {c['media_only']} "
           f"| {fmt(c['signals_per_day'], '.2f')} "
           f"| {(c['last_msg_utc'] or '')[:16]} "
           f"| {'ERR' if c['error'] else ''} |")
    ap("")
    ap("## Deep-verify gate (complete >= "
       f"{VERIFY_MIN_COMPLETE} in the {MSG_LIMIT_SCAN}-msg window)")
    ap("")
    ap("| # | chat | id | complete | sig/day | symbols |")
    ap("|---:|---|---:|---:|---:|---|")
    for c in scan["verify_candidates"]:
        syms = ", ".join(f"{k}x{v}" for k, v in sorted(
            (c.get("symbols") or {}).items(), key=lambda kv: -kv[1])[:6])
        ap(f"| {c['rank']} | {c['title'][:36]} | {c['id']} | {c['complete']} "
           f"| {fmt(c['signals_per_day'], '.2f')} | {syms} |")
    ap("")
    ap("Next: `channel_verify3.py verify` runs the V2 exit-geometry "
       "verification (per `agent-reports/exit-geometry.md`) on every "
       "candidate above.")
    with open(SCAN_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return SCAN_MD


async def stage_scan(fresh):
    copy_session(force=fresh)
    client, me = await connect()
    try:
        chats = await stage_inventory(client, me)
        included = [c for c in chats if not c["excluded"]]
        print(f"triaging {len(included)} chats "
              f"({MSG_LIMIT_SCAN} msgs each) ...")
        for i, rec in enumerate(included, 1):
            print(f"[{i}/{len(included)}] triage {rec['type']:<9} "
                  f"{rec['title'][:40]!r} ({rec['id']})", flush=True)
            rec.update(await triage_chat(client, rec))
        inc = rank_included(chats)
    finally:
        await client.disconnect()
        print("Telegram disconnected")

    candidates = [c for c in inc if int(c.get("complete") or 0) >= VERIFY_MIN_COMPLETE]
    scan = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "sweep": "FULL CHANNEL SWEEP scan: inventory + cheap triage (read-only)",
        "me": {"id": me.id, "name": (me.first_name or "") + (f" {me.last_name}" if me.last_name else ""),
               "username": me.username},
        "method": {
            "inventory": "iter_dialogs(limit=None) + iter_dialogs(limit=None,"
                         " archived=True), deduped by id",
            "exclusions": "bots (entity.bot, GMGN*, BotFather, @hermes_*), "
                          f"own chats/channels (creator flag), Signal Relay "
                          f"Feed {OWN_FEED_ID}",
            "triage_msgs_per_chat": MSG_LIMIT_SCAN,
            "parser": "relay's own parser.parse_signal (deterministic)",
            "recap_screen": "ai_filter.looks_like_results counted (ai_recap_posts); "
                            "pipeline recap skip = 'tp hit'/'pips' (recap_posts)",
            "complete_definition": "parse_ok, non-manage, has SL, >=1 TP, "
                                   "numeric entry, not a 'tp hit'/'pips' recap "
                                   "(identical to the V1/V2 keep-filter)",
            "signals_per_day": "complete * 86400 / max(window_seconds, 3600)",
            "ranking": "complete desc, parse_rate desc, newest message desc",
            "session": "telethon-scan.session (sqlite backup copy of "
                      "telethon.session; live session never connected/written)",
        },
        "dialogs_total": len(chats),
        "excluded_total": sum(1 for c in chats if c["excluded"]),
        "triaged_total": sum(1 for c in chats if not c["excluded"]),
        "verify_gate": VERIFY_MIN_COMPLETE,
        "verify_candidates": candidates,
        "chats": chats,
    }
    # JSON file FIRST, always
    with open(SCAN_JSON, "w", encoding="utf-8") as f:
        json.dump(scan, f, indent=2, default=str)
    print(f"scan inventory saved: {SCAN_JSON}")
    md = write_scan_md(scan)
    print(f"scan markdown saved: {md}")
    hdr = (f"{'#':>3} {'chat':<34} {'complete':>8} {'raw':>5} {'sig/d':>6} "
           f"{'recaps':>7} {'last msg':<17}")
    print("\n" + hdr)
    print("-" * len(hdr))
    for c in inc[:40]:
        print(f"{c['rank']:>3} {c['title'][:33]:<34} {c['complete']:>8} "
              f"{c['complete_raw']:>5} {c['signals_per_day']:>6.2f} "
              f"{c['recap_posts']:>7} {(c['last_msg_utc'] or '')[:16]:<17}")
    print(f"\ndeep-verify candidates (complete >= {VERIFY_MIN_COMPLETE}): "
          f"{len(candidates)}")
    for c in candidates:
        print(f"  #{c['rank']} {c['title'][:40]} ({c['id']}) "
              f"complete={c['complete']}")
    return 0


# ------------------------------------------------------------ deep verification
def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return default


def _safe_resolve_symbol(raw):
    """executor.resolve_symbol semantics minus the mt5.symbol_search tail,
    which does not exist in this MetaTrader5 package and raises
    AttributeError, ABORTING a channel's verification mid-iteration when a
    swept chat posts an exotic/unlisted symbol (hit during this sweep:
    Gold Signals VIP crashed at 11/300 msgs, XAUUSD GOLD PRO TRADER at
    211/300). Exact + prefix/suffix candidates are identical to
    executor.resolve_symbol; the search fallback is guarded. executor.py
    itself is NEVER modified - this patches only the imported engine's
    namespace at runtime, inside this read-only process."""
    if not raw:
        return None
    import MetaTrader5 as mt5
    from executor import _symbol_cache
    if raw in _symbol_cache:
        return _symbol_cache[raw]
    raw_u = raw.upper()
    cands = [raw_u, raw_u.replace("/", ""), f".{raw_u}", f"{raw_u}.r",
             f"{raw_u}r", f"{raw_u}.c", f"{raw_u}.m", f"{raw_u}_", f"m{raw_u}"]
    resolved = None
    for c in cands:
        if mt5.symbol_info(c):
            resolved = c
            break
    if resolved is None:
        try:
            hits = mt5.symbol_search(raw_u) or []
            exact = next((h.name for h in hits
                          if getattr(h, "name", "").upper() == raw_u), None)
            resolved = exact or (hits[0].name if hits else None)
        except AttributeError:
            resolved = None
    _symbol_cache[raw] = resolved  # cache misses too: one broker call per symbol
    return resolved


async def stage_verify():
    scan = load_json(SCAN_JSON)
    if not scan:
        print(f"no scan inventory at {SCAN_JSON} - run the scan stage first")
        return 1
    candidates = [c for c in scan.get("verify_candidates") or []
                  if int(c.get("complete") or 0) >= VERIFY_MIN_COMPLETE]
    if not candidates:
        print("no chat has >= %d complete signals - nothing to deep-verify"
              % VERIFY_MIN_COMPLETE)
    if not os.path.exists(SESSION):
        copy_session()
    else:
        print(f"reusing scan session copy: {SESSION}")

    import channel_verify2 as v2   # the PROVEN V2 exit-geometry engine
    import MetaTrader5 as mt5      # noqa: F401  (same module object as v2's)
    # generalize-the-engine patch: the V2 engine's imported resolver crashes
    # on symbols not found via exact/prefix candidates (mt5.symbol_search does
    # not exist in this package). Runtime-only; no file is modified.
    v2.resolve_symbol = _safe_resolve_symbol
    print("engine patch applied: v2.resolve_symbol -> safe resolver "
          "(no mt5.symbol_search)")

    results = []
    offset = None
    per_symbol_ticks = None
    if not initialize_existing(mt5):
        print("MT5 connection unavailable:", broker_status())
        return 1
    print("MT5 attached (read-only):", mt5.account_info().server)
    try:
        if candidates:
            offset, per_symbol_ticks = v2.compute_server_offset()
            client, me = await connect()
            try:
                for c in candidates:
                    print(f"--- deep-verify {c['title'][:40]} ({c['id']}) "
                          f"triage complete={c['complete']} ...", flush=True)
                    st = await v2.analyze_channel(client, int(c["id"]),
                                                  c["title"], offset)
                    st["archived"] = bool(c.get("archived"))
                    st["triage"] = {k: c.get(k) for k in (
                        "rank", "complete", "complete_raw", "signals_per_day",
                        "parse_rate", "recap_posts", "manage", "media_only",
                        "messages", "symbols", "sides", "last_msg_utc")}
                    results.append(st)
            finally:
                await client.disconnect()
                print("Telegram disconnected")
    finally:
        mt5.shutdown()
        print("MT5 shutdown (connection closed; terminal untouched)")

    # pooled accumulation BEFORE finalize pops the raw lists (verbatim v2.run)
    pooled_raw = {v: {"r_list": [], "ordered": [],
                      "classes": {"sl": 0, "be": 0, "trail": 0, "timeout": 0},
                      "pending": 0, "no_atr": 0} for v in v2.VARIANTS}
    for st in results:
        for v in v2.VARIANTS:
            sv = st["variants"][v]
            pr = pooled_raw[v]
            pr["r_list"].extend(sv["r_list"])
            pr["ordered"].extend(sv["ordered"])
            for kk, n in sv["classes"].items():
                pr["classes"][kk] += n
            pr["pending"] += sv["pending"]
            pr["no_atr"] += sv["no_atr"]
    for st in results:
        for v in v2.VARIANTS:
            v2.finalize_variant(st["variants"][v])
    pooled = {v: v2.finalize_variant(pooled_raw[v]) for v in v2.VARIANTS}

    # best combos with an adequate sample
    combos = []
    for st in results:
        for v in v2.VARIANTS:
            d = st["variants"][v]
            if d["trades"] >= MIN_SAMPLE and d["expectancy_after_costs_r"] is not None:
                combos.append({"label": f"{st['plain_name']} x variant {v}",
                               "chat_id": st["id"], "variant": v, **d})
    combos.sort(key=lambda c: c["expectancy_after_costs_r"], reverse=True)
    best = combos[0] if combos else None
    n_pos = sum(1 for c in combos if c["expectancy_after_costs_r"] >= EXP_BAND)
    if best is not None and best["expectancy_after_costs_r"] >= EXP_BAND:
        overall = ("POSITIVE EDGE - at least one swept source carries real "
                   "edge under the relay's own exit geometry")
        note = (f"{n_pos} of {len(combos)} adequately-sampled combos are "
                f"positive after costs; best combo {best['label']} "
                f"{best['expectancy_after_costs_r']:+.3f}R/trade.")
    elif results and any((pooled[v]["expectancy_after_costs_r"] or 0) > 0
                         for v in v2.VARIANTS):
        overall = "MIXED - some combos improve but none clear the +%.2fR bar" % EXP_BAND
        note = "Trailing exits recover part of the TP-farm giveback; no swept source clears costs decisively."
    else:
        overall = "NEGATIVE - no swept source carries edge under our exits"
        note = "Even with the relay's own trailing engine the swept sources lose after costs."

    # cross-reference the incumbents' earlier verdicts
    v2rep = load_json(V2_REPORT) or {}
    v1rep = load_json(V1_REPORT) or {}
    v2map = {int(c["id"]): c for c in v2rep.get("channels", [])}
    v1map = {int(c["id"]): c for c in v1rep.get("channels", [])}
    cross = {}
    for st in results:
        cid = int(st["id"])
        e = {}
        if cid in v1map:
            e["v1"] = {k: v1map[cid].get(k) for k in (
                "simulated", "win_pct", "avg_r", "expectancy_after_costs_r")}
        if cid in v2map:
            e["v2"] = {}
            for v in v2.VARIANTS:
                d = (v2map[cid].get("variants") or {}).get(v) or {}
                e["v2"][v] = {k: d.get(k) for k in (
                    "trades", "win_pct", "avg_r",
                    "expectancy_after_costs_r", "verdict")}
        if e:
            cross[str(cid)] = e

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "research": "FULL CHANNEL SWEEP v3: every dialog inventoried + triaged; "
                    "deep verification via the V2 exit-geometry engine "
                    "(channel direction x relay trailing exit)",
        "method": {
            "scan": "see scan-inventory.json (inventory + "
                    f"{MSG_LIMIT_SCAN}-msg triage per chat)",
            "verify_gate": f"chats with >= {VERIFY_MIN_COMPLETE} complete "
                           "signals in the triage window",
            "verify_engine": "channel_verify2.analyze_channel verbatim "
                             "(300-msg fetch, recap skip, keep-filter, stale "
                             "1% screen, market entry at first M15 bar at/after "
                             "signal)",
            "variants": "A = channel's stated SL; B = 2 x Wilder ATR(14) M15 "
                        "(strictly closed bars); ALL channel TPs ignored",
            "exit_management": "manage.py rules: BE at +1R (+10pt buffer), "
                               "0.5R trail from +1.5R, ratchet-only; 48h walk; "
                               "conservative same-bar rule",
            "costs": "0.07R round-trip haircut per trade",
            "verdict_bands": f"exp after costs >= +{EXP_BAND}R POSITIVE EDGE, "
                             f"<= -{EXP_BAND}R NEGATIVE, else FLAT; "
                             f"n < {MIN_SAMPLE} = INSUFFICIENT DATA (tentative)",
            "server_offset_s": round(offset) if offset is not None else None,
            "server_offset_method": "freshest tick across XAUUSD/EURUSD/GBPUSD/"
                                    "US30/XAGUSD/AUDUSD",
            "tick_times_at_run": per_symbol_ticks,
            "session": "telethon-scan.session (copy; live session never "
                       "connected/written)",
            "mt5_access": "read-only: initialize/shutdown + copy_rates/"
                          "symbol_info/symbol_info_tick/symbol_select; "
                          "order_send never called",
        },
        "scan_candidates": [{"id": c["id"], "title": c["title"],
                             "complete": c["complete"],
                             "signals_per_day": c.get("signals_per_day"),
                             "archived": c.get("archived")}
                            for c in candidates],
        "verified_count": len(results),
        "channels": results,
        "pooled": pooled,
        "best_combo": best,
        "overall": {"verdict": overall, "verdict_note": note,
                    "adequate_sample_combos": len(combos),
                    "positive_combos": n_pos},
        "cross_reference_v1_v2": cross,
    }
    with open(REPORT_V3, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nreport saved: {REPORT_V3}")
    errs = [(s["plain_name"], s["error"]) for s in results if s.get("error")]
    if errs:
        print("WARNING - verification errors (channel truncated):")
        for name, e in errs:
            print(f"  {name}: {e}")

    hdr = (f"{'chat':<28}{'var':>4}{'trades':>7}{'win%':>7}{'avgR':>8}"
           f"{'expCost':>8}{'maxDD':>7}  VERDICT")
    print("\n" + hdr)
    print("-" * len(hdr))
    for s in results:
        for v in v2.VARIANTS:
            d = s["variants"][v]
            print(f"{s['plain_name'][:27]:<28}{v:>4}{d['trades']:>7}"
                  f"{fmt(d['win_pct'], '.1f'):>7}{fmt(d['avg_r'], '+.3f'):>8}"
                  f"{fmt(d['expectancy_after_costs_r'], '+.3f'):>8}"
                  f"{fmt(d['max_dd_r'], '.2f'):>7}  {d['verdict']}")
    print("-" * len(hdr))
    for v in v2.VARIANTS:
        d = pooled[v]
        print(f"{'ALL VERIFIED (pooled)':<28}{v:>4}{d['trades']:>7}"
              f"{fmt(d['win_pct'], '.1f'):>7}{fmt(d['avg_r'], '+.3f'):>8}"
              f"{fmt(d['expectancy_after_costs_r'], '+.3f'):>8}"
              f"{fmt(d['max_dd_r'], '.2f'):>7}  {d['verdict']}")
    print(f"\nOVERALL: {overall}")
    if best:
        print(f"BEST COMBO: {best['label']}: {best['trades']} trades, "
              f"win% {best['win_pct']}, expectancy after costs "
              f"{best['expectancy_after_costs_r']:+.3f}R, maxDD {best['max_dd_r']}R")
    print("next: channel_verify3.py report -> agent-reports/full-sweep.md")
    return 0


# ------------------------------------------------------------------ reporting
def best_variant(st):
    best = None
    for v in ("A", "B"):
        d = st["variants"][v]
        exp = d.get("expectancy_after_costs_r")
        if not d.get("trades") or exp is None:
            continue
        if best is None or exp > best[1]["expectancy_after_costs_r"]:
            best = (v, d)
    return best


def policy_for(v):
    """signal_policy entry matching the WINNING variant's validated geometry."""
    if v == "B":
        return {"sl_mode": "atr", "atr_mult": 2.0, "tp_mode": "none"}
    return {"sl_mode": "channel", "tp_mode": "none"}


def recommend_for(st):
    """-> (class, policy_dict, note). Conservative decision rule:
    go-live only on an ADEQUATE sample with expectancy >= +0.05R after
    costs; promising-but-thin or flat sources go to shadow; verified
    negative adequate samples are not added at all."""
    bv = best_variant(st)
    if bv is None:
        return ("skip", None,
                "zero resolved trades in either variant - nothing to trade")
    v, d = bv
    n, exp = d["trades"], d["expectancy_after_costs_r"]
    adequate = n >= MIN_SAMPLE
    if adequate and exp >= EXP_BAND:
        return ("go-live", policy_for(v),
                f"variant {v}: {n} trades, exp after costs {exp:+.3f}R "
                f"(win% {d['win_pct']}, maxDD {d['max_dd_r']}R)")
    if adequate and exp <= -EXP_BAND:
        return ("do-not-add", {"mode": "shadow"},
                f"verified NEGATIVE: best variant {v} exp after costs "
                f"{exp:+.3f}R over {n} trades")
    if not adequate and exp >= EXP_BAND:
        return ("shadow-promising", {"mode": "shadow"},
                f"variant {v} exp after costs {exp:+.3f}R but only {n} trades "
                f"(<{MIN_SAMPLE}) - shadow until the sample grows")
    return ("shadow", {"mode": "shadow"},
            f"flat/thin: best variant {v} exp after costs {exp:+.3f}R over "
            f"{n} trades - record only")


def rank_verified(results):
    def key(st):
        bv = best_variant(st)
        if bv is None:
            return (0, -9.0, 0)
        v, d = bv
        return (1 if d["trades"] >= MIN_SAMPLE else 0,
                d["expectancy_after_costs_r"], d["trades"])
    return sorted(results, key=key, reverse=True)


def stage_report():
    scan = load_json(SCAN_JSON)
    rep = load_json(REPORT_V3)
    if not (scan and rep):
        print("need scan-inventory.json and channel_report_v3.json first")
        return 1
    cfg = load_json(CFG_JSON) or {}
    in_config = {int(c) for c in (cfg.get("channels") or [])}
    v2rep = load_json(V2_REPORT) or {}
    v2map = {int(c["id"]): c for c in v2rep.get("channels", [])}
    results = rank_verified(rep.get("channels") or [])
    pooled = rep.get("pooled") or {}
    cross = rep.get("cross_reference_v1_v2") or {}

    recs = []
    for st in results:
        cls, pol, note = recommend_for(st)
        cid = int(st["id"])
        recs.append({
            "id": st["id"], "title": st["plain_name"], "class": cls,
            "best_variant": best_variant(st)[0] if best_variant(st) else None,
            "policy": pol, "note": note,
            "already_in_config": cid in in_config,
            "archived": st.get("archived"),
            "signals_per_day": (st.get("triage") or {}).get("signals_per_day"),
        })
    rep_out = dict(rep)
    rep_out["recommendations"] = recs
    with open(REPORT_V3, "w", encoding="utf-8") as f:
        json.dump(rep_out, f, indent=2, default=str)

    os.makedirs(os.path.dirname(FULL_MD), exist_ok=True)
    L = []
    ap = L.append
    ap("# FULL CHANNEL SWEEP - ranked report + policy recommendations (V3)")
    ap("")
    ap(f"_generated {rep['generated_utc']} · engine: `channel_verify3.py` "
       "(read-only) · scan: `scan-inventory.json` + "
       "`agent-reports/scan-inventory.md` · full data: "
       "`channel_report_v3.json` · prior runs: `channel_report.json` (V1, "
       "their exits) and `channel_report_v2.json` (V2, incumbents only)_")
    ap("")
    ap("## Question")
    ap("")
    ap("Inventory and triage EVERY dialog the account can see (main folder + "
       "archive), then deep-verify every source with enough signal flow "
       f"(>= {VERIFY_MIN_COMPLETE} complete signals in a {scan['method']['triage_msgs_per_chat']}-msg window) "
       "under the PROVEN V2 exit-geometry method (`agent-reports/"
       "exit-geometry.md`): keep their direction + entry timing, throw away "
       "their exits, manage with the relay's own trailing engine.")
    ap("")
    ap("## Method (identical to exit-geometry.md unless noted)")
    ap("")
    ap(f"- Deep-verify fetch: 300 messages per candidate (per "
       f"exit-geometry.md), same recap skip ('tp hit'/'pips'), same "
       f"keep-filter, same stale screen (>1% from price at signal time).")
    m = rep.get("method") or {}
    ap(f"- Market entry at the open of the first M15 bar at/after signal "
       f"time; server-time offset from the freshest tick across 6 liquid "
       f"symbols (this run: {m.get('server_offset_s')}s).")
    ap("- Variant A = channel's stated SL; variant B = 2 x Wilder ATR(14) "
       "M15 (closed bars only); ALL channel TPs ignored; BE at +1R (+10pt "
       "buffer), 0.5R trail from +1.5R, ratchet-only; 48h walk; "
       "conservative same-bar rule; 0.07R round-trip costs.")
    ap(f"- Verdict bands: exp after costs >= +{EXP_BAND}R POSITIVE EDGE, "
       f"<= -{EXP_BAND}R NEGATIVE, else FLAT; n < {MIN_SAMPLE} resolved "
       "trades = INSUFFICIENT DATA (tentative).")
    ap("- Scan stage used NO MT5. Verify stage MT5 access strictly "
       "read-only (initialize/shutdown + copy_rates/symbol_info/"
       "symbol_info_tick/symbol_select; order_send never called). Telegram "
       "ran on `telethon-scan.session`, a sqlite-backup copy of the live "
       "`telethon.session` (never connected, never written). No existing "
       "file modified; config.json read-only; no channel joined.")
    ap("")
    ap("## Sweep summary")
    ap("")
    ap(f"- Dialogs inventoried: **{scan['dialogs_total']}** "
       f"(main folder + archived), excluded **{scan['excluded_total']}** "
       f"(bots / own chats / relay feed), triaged "
       f"**{scan['triaged_total']}**.")
    ap(f"- Deep-verify gate (complete >= {VERIFY_MIN_COMPLETE}): "
       f"**{len(scan.get('verify_candidates') or [])}** chats; "
       f"**{rep.get('verified_count')}** verified.")
    ap("")
    ap("## Ranked verified chats (best variant first)")
    ap("")
    ap("| # | chat | id | arch | sig/day | A: n / exp | B: n / exp | best | "
       "verdict (best variant) |")
    ap("|---:|---|---:|---|---:|---|---|---|---|")
    for i, st in enumerate(results, 1):
        a, b = st["variants"]["A"], st["variants"]["B"]
        bv = best_variant(st)
        bvtxt = bv[0] if bv else "-"
        verd = bv[1]["verdict"] if bv else "INSUFFICIENT DATA: 0 resolved trades"
        spd = (st.get("triage") or {}).get("signals_per_day")
        ap(f"| {i} | {st['plain_name'][:34]} | {st['id']} "
           f"| {'A' if st.get('archived') else '-'} | {fmt(spd, '.2f')} "
           f"| {a['trades']} / {fmt(a['expectancy_after_costs_r'], '+.3f')} "
           f"| {b['trades']} / {fmt(b['expectancy_after_costs_r'], '+.3f')} "
           f"| {bvtxt} | {verd} |")
    ap("")
    ap("Pooled across all verified chats: variant A "
       f"{pooled.get('A', {}).get('trades', 0)} trades, exp after costs "
       f"{fmt(pooled.get('A', {}).get('expectancy_after_costs_r'), '+.3f')}R; "
       f"variant B {pooled.get('B', {}).get('trades', 0)} trades, exp after "
       f"costs {fmt(pooled.get('B', {}).get('expectancy_after_costs_r'), '+.3f')}R.")
    ap("")
    errlines = [f"- **{st['plain_name']}** (`{st['id']}`): verification "
                f"INCOMPLETE - engine error `{st['error']}` "
                f"(processed {st['messages']}/300 messages; stats are "
                f"partial)"
                for st in results if st.get("error")]
    if errlines:
        ap("**Verification errors (partial data - treat these rows with "
           "suspicion):**")
        ap("")
        L.extend(errlines)
        ap("")
    ap("## Channel x variant detail")
    ap("")
    ap("| channel | variant | trades | win% | avg R | exp after costs (R) | "
       "max DD (R) | verdict |")
    ap("|---|---|---:|---:|---:|---:|---:|---|")
    for st in results:
        for v in ("A", "B"):
            d = st["variants"][v]
            ap(f"| {st['plain_name']} | {v} | {d['trades']} "
               f"| {fmt(d['win_pct'], '.1f')} | {fmt(d['avg_r'], '+.3f')} "
               f"| {fmt(d['expectancy_after_costs_r'], '+.3f')} "
               f"| {fmt(d['max_dd_r'], '.2f')} | {d['verdict']} |")
    ap("")
    ap("## Recommendations")
    ap("")
    live_adds = [r for r in recs if r["class"] == "go-live"]
    shadow_adds = [r for r in recs if r["class"] in ("shadow", "shadow-promising")]
    do_not_add = [r for r in recs if r["class"] in ("do-not-add", "skip")]
    ap("### Add to config.json `channels` + go-live `signal_policy` "
       "(validated parameters)")
    ap("")
    if live_adds:
        snippet = {"channels_add": [str(r["id"]) for r in live_adds],
                   "signal_policy_add": {str(r["id"]): r["policy"] for r in live_adds}}
        ap("```json")
        ap(json.dumps(snippet, indent=2))
        ap("```")
        for r in live_adds:
            tag = " (already in channels - keep/adjust policy)" if r["already_in_config"] else ""
            ap(f"- **{r['title']}** (`{r['id']}`){tag}: {r['note']}. "
               f"Policy: `{json.dumps(r['policy'])}`.")
    else:
        ap("_none - no swept chat clears the adequate-sample + "
           f"+{EXP_BAND}R bar in this run._")
    ap("")
    ap("### Add in SHADOW mode (recorded, never traded)")
    ap("")
    if shadow_adds:
        snippet = {"channels_add": [str(r["id"]) for r in shadow_adds],
                   "signal_policy_add": {str(r["id"]): r["policy"] for r in shadow_adds}}
        ap("```json")
        ap(json.dumps(snippet, indent=2))
        ap("```")
        for r in shadow_adds:
            ap(f"- **{r['title']}** (`{r['id']}`): {r['note']}.")
    else:
        ap("_none._")
    ap("")
    ap("### Do NOT add")
    ap("")
    if do_not_add:
        for r in do_not_add:
            ap(f"- **{r['title']}** (`{r['id']}`): {r['note']}.")
    else:
        ap("_none._")
    ap("")
    ap("### Incumbents (already in config.json) - keep/adjust")
    ap("")
    incumb = [r for r in recs if r["already_in_config"]]
    if incumb:
        for r in incumb:
            ap(f"- **{r['title']}** (`{r['id']}`): {r['class']} - {r['note']}.")
    for cid in sorted(in_config):
        if any(int(r["id"]) == cid for r in incumb):
            continue
        t = next((c for c in scan["chats"] if int(c["id"]) == cid), None)
        v2c = v2map.get(cid) or {}
        v2b = ((v2c.get("variants") or {}).get("B") or {})
        ap(f"- **{(t or {}).get('title', cid)}** (`{cid}`): NOT re-verified - "
           f"only {int((t or {}).get('complete') or 0)} complete signals in "
           f"the {MSG_LIMIT_SCAN}-msg triage window (gate "
           f"{VERIFY_MIN_COMPLETE}). Prior V2 evidence: "
           f"{v2b.get('verdict', 'n/a')}"
           + (f", B exp {v2b.get('expectancy_after_costs_r'):+.3f}R"
              if v2b.get("expectancy_after_costs_r") is not None else "")
           + ". Keep current config placement.")
    ap("")
    ap("## V1 / V2 / V3 comparison (incumbents)")
    ap("")
    rows = [("| chat | id | V1 exp (their exits) | V2-A exp | V2-B exp | "
             "V3-A exp | V3-B exp |"),
            "|---|---:|---:|---:|---:|---:|---:|"]
    for st in results:
        cid = str(st["id"])
        cx = cross.get(cid) or {}
        v1e = ((cx.get("v1") or {}).get("expectancy_after_costs_r"))
        v2a = ((cx.get("v2") or {}).get("A") or {}).get("expectancy_after_costs_r")
        v2b = ((cx.get("v2") or {}).get("B") or {}).get("expectancy_after_costs_r")
        rows.append(f"| {st['plain_name']} | {st['id']} "
                    f"| {fmt(v1e, '+.3f')} | {fmt(v2a, '+.3f')} "
                    f"| {fmt(v2b, '+.3f')} "
                    f"| {fmt(st['variants']['A']['expectancy_after_costs_r'], '+.3f')} "
                    f"| {fmt(st['variants']['B']['expectancy_after_costs_r'], '+.3f')} |")
    ap("\n".join(rows))
    ap("")
    ap("## Caveats")
    ap("")
    ap("- Same as exit-geometry.md: M15 granularity + conservative same-bar "
       "rule takes the WORST fill ordering (live manage.py trails on 10s "
       "ticks); no slippage modeling (0.07R haircut covers costs); the 48h "
       "horizon leaves the freshest ~2 days of signals `pending`, excluded "
       "from stats.")
    ap("- Triage complete counts are from a 200-message window; the verify "
       "stage re-derives its trade set from a 300-message fetch per "
       "exit-geometry.md, so per-chat message stats differ between the two "
       "files by design.")
    ap("- Media-only posts are counted, never OCR-parsed; user-chat samples "
       "can be tiny (a DM with a handful of signals) - treat 'INSUFFICIENT "
       "DATA' verdicts as exactly that.")
    ap("- Read-only guarantees: `telethon.session` never connected (scan ran "
       "on a sqlite backup copy), MT5 never sent an order, no existing file "
       "modified, config.json untouched, no channel joined, no process "
       "started/stopped. Created: `channel_verify3.py`, "
       "`scan-inventory.json`, `agent-reports/scan-inventory.md`, "
       "`channel_report_v3.json`, `agent-reports/full-sweep.md`, "
       "`telethon-scan.session`.")
    with open(FULL_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"full sweep report saved: {FULL_MD}")
    print("\nTop verified chats:")
    for i, st in enumerate(results[:8], 1):
        bv = best_variant(st)
        verd = bv[1]["verdict"] if bv else "no trades"
        exp = fmt(bv[1]["expectancy_after_costs_r"], '+.3f') if bv else "-"
        print(f"  {i}. {st['plain_name'][:36]:<38} {st['id']:>14}  "
              f"best={bv[0] if bv else '-'} exp={exp} {verd}")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Full channel sweep (read-only): scan | verify | report | all")
    ap.add_argument("stage", choices=["scan", "verify", "report", "all"])
    ap.add_argument("--fresh-session", action="store_true",
                    help="force a fresh sqlite-backup copy of the live session")
    args = ap.parse_args()
    rc = 0
    if args.stage in ("scan", "all"):
        rc = asyncio.run(stage_scan(args.fresh_session)) or rc
    if args.stage in ("verify", "all"):
        rc = asyncio.run(stage_verify()) or rc
    if args.stage in ("report", "all"):
        rc = stage_report() or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())


---
slug: analyze_channels
type: note
graph: gitnexus
---

"""Analyze candidate signal channels: fetch recent messages, parse each with the
pipeline's own parser, score consistency/quality. Read-only, no trading."""
import asyncio
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parser as p  # noqa: E402
from daemon import _get_client  # noqa: E402

CHANNELS = {
    -1002281357812: "TYL - TRADING",
    -1002073061621: "Simple Forex Tools",
    -1002692333123: "XAUUSD PRO SIGNAL",
    -1001932578394: "Christopher Alan Harrison",
    -1001346757271: "Intelligent Trading Signals",
    -1002369502254: "Best Signal Forex",
    -1002165799093: "XAUUSD FREE SIGNALS",
    -1001284268486: "Easy Forex OFFICIAL",
    -1002477522071: "PLATINUM PICKS",
    -1002011325214: "TrADE X POCKET OPTION",
    -1003828962121: "The Vault [CHAT]",
    -1004382544346: "The Lab",
    -1001920020352: "Grow Trading",
    -1003884507657: "Certified Picks",
    -1002759257576: "FTO",
    -1001715953952: "Pockets of Rizdom",
    -1001523638497: "FundedNext Official",
    -1003629327586: "Signal8",
    -1001904158438: "MQL5 Algo Trading",
    -1002360021655: "Vault by Miles Deutscher",
}
LIMIT = 150
NOW = datetime.now(timezone.utc)


async def stats(client, cid, title):
    msgs = []
    try:
        async for m in client.iter_messages(cid, limit=LIMIT):
            if m.message:
                msgs.append((m.date, m.message))
    except Exception as e:  # noqa: BLE001
        return {"title": title, "cid": cid, "error": f"{type(e).__name__}: {e}"[:70]}
    if not msgs:
        return {"title": title, "cid": cid, "error": "no text messages"}
    dates = [d for d, _ in msgs if d]
    span_days = max((max(dates) - min(dates)).total_seconds() / 86400.0, 1.0) if dates else 1.0
    executable = with_sl = with_tp = manage = 0
    symbols = {}
    last_sig_age = None
    for d, text in msgs:
        r = p.parse_signal(text)
        if not r.get("is_signal"):
            continue
        if r.get("action") == "manage":
            manage += 1
            continue
        if r.get("parse_ok"):
            executable += 1
            if r.get("sl"):
                with_sl += 1
            if r.get("tps"):
                with_tp += 1
            sym = r.get("symbol") or "?"
            symbols[sym] = symbols.get(sym, 0) + 1
            age = (NOW - d).total_seconds() / 86400.0 if d else 0
            if last_sig_age is None or age < last_sig_age:
                last_sig_age = age
    top_syms = ",".join(f"{s}({c})" for s, c in sorted(symbols.items(), key=lambda x: -x[1])[:3])
    sps = executable / span_days
    sltp = (with_sl + with_tp) / (2 * executable) if executable else 0.0
    fresh = 1.0 if (last_sig_age or 999) <= 7 else (0.6 if (last_sig_age or 999) <= 30 else 0.25)
    score = min(sps, 5.0) * (0.4 + 0.6 * sltp) * fresh
    return {"title": title, "cid": cid, "msgs": len(msgs), "span_d": round(span_days),
            "exec": executable, "sig_day": round(sps, 2), "sl%": round(100 * with_sl / executable) if executable else 0,
            "tp%": round(100 * with_tp / executable) if executable else 0,
            "last_age_d": round(last_sig_age, 1) if last_sig_age is not None else "none",
            "manage": manage, "syms": top_syms, "score": round(score, 2)}


async def main():
    client = _get_client()
    await client.connect()
    if not await client.is_user_authorized():
        print("NOT_AUTHORIZED")
        return
    rows = []
    for cid, title in CHANNELS.items():
        try:
            rows.append(await stats(client, cid, title))
            print("done:", title, flush=True)
        except Exception as e:  # noqa: BLE001
            rows.append({"title": title, "cid": cid, "error": str(e)[:70]})
    await client.disconnect()
    ok = [r for r in rows if "error" not in r]
    bad = [r for r in rows if "error" in r]
    print("\n== CHANNEL SCORES (sorted) ==")
    for r in sorted(ok, key=lambda x: -x["score"]):
        print(f"{r['score']:>6} | {r['title'][:26]:<26} | sig/day {r['sig_day']:>5} | "
              f"SL {r['sl%']:>3}% TP {r['tp%']:>3}% | last {str(r['last_age_d']):>6}d | "
              f"msgs {r['msgs']:>3} | {r['syms']}")
    if bad:
        print("\n== SKIPPED ==")
        for r in bad:
            print(f"{r['title'][:26]:<26} | {r['error']}")


asyncio.run(main())


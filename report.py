"""Daily report: compact digest of the signal-relay trade ledger + live account state.

Read-only. Run:  C:/Users/voidk/miniconda3/python.exe report.py
Prints plain text suitable for Telegram.
"""
from broker_lifecycle import initialize_existing
import json
import os
import sqlite3
import time

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "signals.db")
CONFIG = os.path.join(BASE, "config.json")


def ledger_stats():
    if not os.path.exists(DB):
        return None
    con = sqlite3.connect(DB)
    try:
        rows = con.execute("SELECT ts, symbol, side, lot, sl, tp, status, detail, ticket "
                           "FROM trades ORDER BY id").fetchall()
    finally:
        con.close()
    return rows


def main():
    today = time.strftime("%Y-%m-%d")
    rows = ledger_stats() or []
    today_rows = [r for r in rows if r[0].startswith(today)]
    status_today = {}
    for r in today_rows:
        status_today[r[6]] = status_today.get(r[6], 0) + 1

    lines = [f"📊 Signal-relay report — {time.strftime('%a %Y-%m-%d %H:%M')}"]
    if not rows:
        lines.append("No trades in ledger yet (pipeline tested but not live).")
    else:
        st = ", ".join(f"{k} {v}" for k, v in sorted(status_today.items())) or "none today"
        lines.append(f"Today: {len(today_rows)} signal(s) -> {st}")
        lines.append(f"All-time: {len(rows)} ledger row(s)")
        for r in rows[-5:]:
            lot = f"{r[3]} lots" if r[3] else ""
            lines.append(f"  {r[0]} {str(r[2] or '?').upper()} {r[1] or '?'} {lot} -> {r[6]}"
                         + (f" ({r[7]})" if r[7] else ""))

    # live account + open positions (best effort)
    try:
        import MetaTrader5 as mt5
        if initialize_existing(mt5):
            ai = mt5.account_info()
            lines.append(f"Account: {ai.server} #{ai.login} | balance {ai.balance:.2f} {ai.currency} "
                         f"| equity {ai.equity:.2f} | float P/L {ai.profit:+.2f}")
            poss = mt5.positions_get() or []
            if poss:
                lines.append(f"Open positions: {len(poss)}")
                for p in poss:
                    lines.append(f"  {p.symbol} {p.volume} {('BUY' if p.type == 0 else 'SELL')} "
                                 f"@ {p.price_open} | SL {p.sl or '-'} TP {p.tp or '-'} "
                                 f"| P/L {p.profit:+.2f}")
            else:
                lines.append("Open positions: none")
            haltpath = os.path.join(BASE, "HALT")
            if os.path.exists(haltpath):
                lines.append("⚠️ HALT file present — trading is PAUSED (delete it to resume).")
            mt5.shutdown()
    except Exception as e:  # noqa: BLE001
        lines.append(f"(live MT5 read skipped: {e})")
    print("\n".join(lines))


if __name__ == "__main__":
    main()

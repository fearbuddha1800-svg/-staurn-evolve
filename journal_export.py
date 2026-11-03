"""Journal Export — exports signals.db trades ledger to trade-journal import format.

Trade Journal imports executions (fills), not round-trip trades. Its round-trip engine
(FIFO/LIFO/WAVG) reconstructs trades from raw fills. We export each executed trade
as entry + exit fills when we have the data, or just entry for open positions.

Output: agent-reports/trade-journal-export.json (JSON array of execution objects)
Compatible with @luxalgo/journal-importers parseAuto() generic CSV/JSON mapper.
"""

from __future__ import annotations
import json
import os
import sqlite3
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

try:
    import MetaTrader5 as mt5
    _HAVE_MT5 = True
except Exception:
    _HAVE_MT5 = False

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "signals.db")
OUT_DIR = os.path.join(BASE, "agent-reports")
OUT_FILE = os.path.join(OUT_DIR, "trade-journal-export.json")

ALGO_MAGIC = 20261015
ACCOUNT_ID = "signal-relay"
SOURCE = "import"  # matches journal-core source type


def _fetch_executed_trades() -> List[Dict[str, Any]]:
    """Fetch all executed trades from signals.db with tickets."""
    trades = []
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2)
        cur = con.execute(
            "SELECT msg_id, ts, symbol, side, lot, entry, sl, tp, ticket, status, detail "
            "FROM trades WHERE status = 'executed' AND ticket IS NOT NULL AND ticket != 0 "
            "ORDER BY ts")
        for row in cur.fetchall():
            msg_id, ts, symbol, side, lot, entry, sl, tp, ticket, status, detail = row
            trades.append({
                "msg_id": msg_id, "ts": ts, "symbol": symbol, "side": side,
                "lot": lot, "entry": entry, "sl": sl, "tp": tp,
                "ticket": ticket, "status": status, "detail": detail
            })
        con.close()
    except Exception:
        pass
    return trades


def _get_mt5_deals_for_ticket(ticket: int) -> List[Any]:
    """Fetch MT5 deals for a given ticket (position)."""
    if not _HAVE_MT5:
        return []
    try:
        deals = mt5.history_deals_get(ticket=ticket)
        return list(deals) if deals else []
    except Exception:
        return []


def _build_execution(
    exec_id: str,
    symbol: str,
    side: str,  # "buy" or "sell"
    qty: float,
    price: float,
    timestamp: str,
    fee: float = 0.0,
    comment: str = "",
    position_id: str = ""
) -> Dict[str, Any]:
    """Build a single execution (fill) object matching journal-core schema."""
    return {
        "id": exec_id,
        "accountId": ACCOUNT_ID,
        "source": SOURCE,
        "symbol": symbol.replace("/", "").upper(),
        "side": side.lower(),
        "quantity": qty,
        "price": price,
        "time": timestamp,
        "fee": fee,
        "comment": comment,
        "positionId": position_id
    }


def _parse_ts(ts: str) -> str:
    """Normalize timestamp to ISO 8601 UTC."""
    # Input format: "2026-10-14 21:11:16" (local, assumed UTC for MT5)
    try:
        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        return dt.isoformat() + "Z"
    except Exception:
        return ts


def export_trades() -> List[Dict[str, Any]]:
    """Export all executed trades as executions (fills) for trade-journal import."""
    trades = _fetch_executed_trades()
    executions = []

    for t in trades:
        ticket = t["ticket"]
        symbol = t["symbol"]
        side = t["side"].lower()  # "buy" or "sell"
        lot = t["lot"] or 0.01
        entry_str = t["entry"]
        ts = _parse_ts(t["ts"])
        position_id = str(ticket)

        # Get MT5 deals for this ticket to find actual fill prices and fees
        deals = _get_mt5_deals_for_ticket(ticket)
        entry_price = None
        exit_price = None
        entry_fee = 0.0
        exit_fee = 0.0
        exit_time = None
        exit_side = "sell" if side == "buy" else "buy"

        if deals:
            # Separate entry and exit deals (entry has position_id=0 or is first)
            entry_deals = [d for d in deals if d.entry == mt5.DEAL_ENTRY_IN]
            exit_deals = [d for d in deals if d.entry == mt5.DEAL_ENTRY_OUT]
            if not entry_deals and not exit_deals:
                # Fallback: first deal = entry, last = exit
                entry_deals = [deals[0]]
                exit_deals = [deals[-1]] if len(deals) > 1 else []

            if entry_deals:
                d = entry_deals[0]
                entry_price = d.price
                entry_fee = abs(d.commission) + abs(getattr(d, "fee", 0.0))
                ts = datetime.fromtimestamp(d.time).isoformat() + "Z"
            if exit_deals:
                d = exit_deals[0]
                exit_price = d.price
                exit_fee = abs(d.commission) + abs(getattr(d, "fee", 0.0))
                exit_time = datetime.fromtimestamp(d.time).isoformat() + "Z"

        # Fallback to signals.db entry price if MT5 unavailable
        if entry_price is None:
            try:
                entry_price = float(entry_str) if entry_str != "market" else 0.0
            except (ValueError, TypeError):
                entry_price = 0.0

        # Entry execution
        if entry_price > 0:
            executions.append(_build_execution(
                exec_id=str(uuid.uuid4()),
                symbol=symbol,
                side=side,
                qty=lot,
                price=entry_price,
                timestamp=ts,
                fee=entry_fee,
                comment=f"signal:{t['msg_id']}",
                position_id=position_id
            ))

        # Exit execution (if we have exit data)
        if exit_price is not None and exit_price > 0 and exit_time:
            executions.append(_build_execution(
                exec_id=str(uuid.uuid4()),
                symbol=symbol,
                side=exit_side,
                qty=lot,
                price=exit_price,
                timestamp=exit_time,
                fee=exit_fee,
                comment=f"signal:{t['msg_id']} exit",
                position_id=position_id
            ))

    return executions


def write_export(export_path: str = OUT_FILE) -> Dict[str, Any]:
    """Write executions to JSON file for trade-journal import."""
    os.makedirs(OUT_DIR, exist_ok=True)
    executions = export_trades()
    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(executions, f, indent=2)
    return {
        "path": export_path,
        "executions_count": len(executions),
        "trades_processed": len(_fetch_executed_trades()),
        "format": "journal-core executions array (compatible with parseAuto generic mapper)"
    }


if __name__ == "__main__":
    result = write_export()
    print(json.dumps(result, indent=2))
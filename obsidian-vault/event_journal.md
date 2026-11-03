---
slug: event_journal
type: note
graph: gitnexus
---

"""Read-only event journal for the signal-relay workspace.

Returns the last 12 events as a list of {time, event, detail} dicts.

Source: signals.db persisted `events`, with the actual `trades` ledger used
only when no event table exists. Read-only; no inferred log-based fills.
`journal()` distinguishes unavailable from confirmed empty and includes source
and timestamp provenance. `get_events()` preserves the legacy list interface.
"""

from __future__ import annotations

import os
import re
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE, "signals.db")
LOG_PATH = os.path.join(BASE, "daemon.log")
LIMIT = 12

_LOG_TS_RE = re.compile(r"^(\d{2}:\d{2}:\d{2})\s+(BE|TRL)\b")


def _trade_events() -> list[dict]:
    """Read the newest trades from signals.db (read-only, never blocks)."""
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error:
        return []
    try:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT ts, symbol, side, status, detail FROM trades "
            "ORDER BY id DESC LIMIT ?",
            (LIMIT,),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()

    events = []
    for r in rows:
        status = (r["status"] or "").strip() or "unknown"
        events.append(
            {
                "time": r["ts"] or "",
                "event": f"trade {status}",
                "detail": f"{r['symbol'] or ''} {r['side'] or ''} - {r['detail'] or ''}".strip(" -"),
            }
        )
    return events


def _timestamp_basis(stamp) -> str:
    from datetime import datetime
    try:
        value = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
        if value.tzinfo is not None:
            return "source includes UTC offset"
    except (TypeError, ValueError):
        pass
    return "source as recorded; timezone unspecified"


def journal(limit: int = LIMIT) -> dict:
    """Persistent events first, real ledger fallback; no inferred log actions.

    Return availability separately from an honestly empty store. Ordering is
    database arrival order, not a guessed comparison of mixed timezone strings.
    P/L samples are excluded at read time only; nothing is deleted.
    """
    import json
    from datetime import datetime, timezone
    result = {"available": False, "events": [], "data_source": "signals.db",
              "captured_at": datetime.now(timezone.utc).isoformat()}
    try:
        limit = max(1, min(500, int(limit)))
        with sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=2) as con:
            con.row_factory = sqlite3.Row
            names = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "events" in names:
                rows = con.execute(
                    "SELECT event_id, ts, type, source, payload, trace_id FROM events "
                    "WHERE type != 'pnl_update' ORDER BY rowid DESC LIMIT ?", (limit,)).fetchall()
                events = []
                for row in rows:
                    try:
                        payload = json.loads(row["payload"])
                        valid_payload = isinstance(payload, dict)
                    except (TypeError, ValueError):
                        payload, valid_payload = None, False
                    detail = payload.get("detail") if valid_payload else None
                    if detail is None and valid_payload:
                        detail = json.dumps(payload, ensure_ascii=False)
                    events.append({"time": row["ts"], "event": row["type"],
                                   "detail": str(detail) if detail is not None else "Payload unavailable",
                                   "event_id": row["event_id"], "trace_id": row["trace_id"],
                                   "source": row["source"], "data_source": "signals.db:events",
                                   "payload_available": valid_payload,
                                   "timestamp_basis": _timestamp_basis(row["ts"])})
                return {**result, "available": True, "events": events,
                        "data_source": "signals.db:events", "order": "database arrival, newest first"}
            if "trades" in names:
                rows = con.execute("SELECT ts, symbol, side, status, detail FROM trades "
                                   "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
                events = [{"time": r["ts"], "event": f"trade {r['status'] or 'unknown'}",
                           "detail": " ".join(str(r[k]) for k in ("symbol", "side", "detail") if r[k] is not None),
                           "data_source": "signals.db:trades",
                           "timestamp_basis": _timestamp_basis(r["ts"])} for r in rows]
                return {**result, "available": True, "events": events, "data_source": "signals.db:trades",
                        "note": "Event table absent; actual trade ledger only, not broker fill confirmation"}
            return {**result, "reason": "No event or trade ledger table"}
    except (sqlite3.Error, OSError, TypeError, ValueError) as exc:
        return {**result, "reason": f"Journal unavailable: {type(exc).__name__}"}


def get_events(limit: int = LIMIT) -> list[dict]:
    """Legacy list API; use journal() when availability must be distinguished."""
    return journal(limit)["events"]


__all__ = ["get_events", "journal"]

## Links from
- [[cockpit]]
- [[test_real_data_views]]

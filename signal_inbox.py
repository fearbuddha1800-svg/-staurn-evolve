"""Read-only inbox view of signals.db plus configured channel names.

Returns a list of {time, symbol, setup, source, status} dicts from the
signals.db 'trades' ledger (read-only URI, timeout=2s) and the channel
names/IDs listed in config.json. Never crashes: a missing or locked DB
yields an empty list; a missing/unreadable config yields an empty list.
"""
import json
import os
import sqlite3

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "signals.db")
CONFIG = os.path.join(BASE, "config.json")

_STATUS_MAP = {
    "executed": "Validated",
    "skipped": "Journalled",
}


def _map_status(status):
    if status is None:
        return "New"
    return _STATUS_MAP.get(str(status).strip().lower(), "New")


def load_inbox(limit=200):
    """Return [{time, symbol, setup, source, status}, ...] from signals.db.

    setup maps to the signal side (buy/sell), source to the originating
    message id. status is normalized: executed -> Validated, skipped ->
    Journalled, anything else -> New. Returns [] on any DB error.
    """
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=2)
        try:
            rows = con.execute(
                "SELECT ts, symbol, side, msg_id, status FROM trades "
                "ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        finally:
            con.close()
    except Exception:  # missing/locked/unreadable DB -> empty, never crashes
        return []
    return [
        {"time": r[0], "symbol": r[1], "setup": r[2], "source": r[3],
         "status": _map_status(r[4])}
        for r in rows
    ]


def channels():
    """Return channel names/IDs from config.json 'channels' ([] on error)."""
    try:
        with open(CONFIG, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except Exception:
        return []
    channels_ = cfg.get("channels", [])
    return list(channels_) if isinstance(channels_, list) else []


def inbox(limit=200):
    """Convenience: {'signals': [...], 'channels': [...]}."""
    return {"signals": load_inbox(limit), "channels": channels()}

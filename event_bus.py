"""Central pub/sub nervous system for the signal-relay workspace.

Every component (daemon, executor, manage, strategy engines, cockpit, neural
harness) publishes to and subscribes from one in-process EventBus. Events are
persisted to signals.db (table `events`) so the bus survives restarts and
/api/events can replay the signal -> intent -> order -> position -> close
chain by trace_id.

Standard envelope: {event_id, ts, type, source, payload, trace_id}
"""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Callable

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.environ.get("SIGNAL_RELAY_EVENT_DB", os.path.join(BASE, "signals.db"))

EVENT_TYPES = frozenset({
    "signal_received", "zone_parsed", "risk_approved", "order_placed",
    "order_filled", "position_opened", "position_closed", "pnl_update",
    "neural_prediction", "channel_score_update", "engine_status", "alert",
    "halt_triggered", "pine_signal", "breakout_signal",
    "luxalgo_regime_shift", "luxalgo_whale_options", "luxalgo_edge_stats",
    "signal_logged",
    "signal_validated",
})

try:  # scalp360.events is the canonical envelope home; keep the two in sync

    from scalp360.events import BUS_EVENT_TYPES as _S360_TYPES  # type: ignore

    if _S360_TYPES:
        EVENT_TYPES = frozenset(_S360_TYPES | {"signal_logged", "signal_validated"})

except Exception:  # noqa: BLE001 - scalp360 package may not be on the path
    pass

def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def new_trace_id() -> str:
    return uuid.uuid4().hex


def make_event(type: str, source: str, payload=None, trace_id=None,
               event_id: str | None = None, ts: str | None = None) -> dict:
    """Build a standard event envelope with missing fields filled in."""
    return {
        "event_id": event_id or uuid.uuid4().hex,
        "ts": ts or _iso_now(),
        "type": type,
        "source": source or "",
        "payload": payload if payload is not None else {},
        "trace_id": trace_id or new_trace_id(),
    }


class EventBus:
    """In-memory pub/sub with persistent SQLite fallback.

    publish() persists to SQLite first, then fires subscribers synchronously.
    A crashing subscriber never stops other subscribers or the persist.
    """

    def __init__(self, db: str = DB, max_memory: int = 10000):
        self.db = db
        self._max_memory = max_memory
        self._subs: dict[str, list[Callable]] = {}
        self._memory: deque = deque(maxlen=max_memory)
        self._lock = threading.RLock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db, timeout=30)
        con.execute("PRAGMA journal_mode=WAL")
        return con

    def _ensure_schema(self) -> None:
        con = self._connect()
        try:
            con.execute(
                """CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    ts TEXT NOT NULL,
                    type TEXT NOT NULL,
                    source TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    trace_id TEXT NOT NULL)"""
            )
            con.execute("CREATE INDEX IF NOT EXISTS idx_events_trace ON events(trace_id)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON events(type)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts)")
            con.commit()
        finally:
            con.close()

    def subscribe(self, event_type: str, callback: Callable) -> None:
        with self._lock:
            self._subs.setdefault(event_type, []).append(callback)

    def publish(self, event: dict) -> str:
        """Publish one envelope dict {type, source, payload, trace_id?}.

        Fills event_id/ts, persists to SQLite, then fires subscribers
        synchronously. Returns event_id. Never raises because of a subscriber.
        """
        if not isinstance(event, dict):
            raise TypeError("event must be a dict envelope {type, source, payload, trace_id}")
        etype = event.get("type")
        if etype not in EVENT_TYPES:
            raise ValueError(f"unknown event type {etype!r} (known: {sorted(EVENT_TYPES)})")
        envelope = {
            "event_id": event.get("event_id") or uuid.uuid4().hex,
            "ts": event.get("ts") or _iso_now(),
            "type": etype,
            "source": event.get("source") or "",
            "payload": event.get("payload") or {},
            "trace_id": event.get("trace_id") or new_trace_id(),
        }
        with self._lock:
            self._memory.append(envelope)
            self._persist(envelope)
            callbacks = list(self._subs.get(etype, []))
        for cb in callbacks:
            try:
                cb(envelope)
            except Exception as e:  # noqa: BLE001 - one bad callback must not break the bus
                print(f"event bus callback failed for {etype}: {type(e).__name__}: {e}")
        return envelope["event_id"]

    def _persist(self, envelope: dict) -> None:
        try:
            con = self._connect()
            try:
                con.execute(
                    "INSERT OR REPLACE INTO events(event_id,ts,type,source,payload,trace_id) "
                    "VALUES(?,?,?,?,?,?)",
                    (envelope["event_id"], envelope["ts"], envelope["type"],
                     envelope["source"], json.dumps(envelope["payload"], default=str),
                     envelope["trace_id"]),
                )
                con.commit()
            finally:
                con.close()
        except Exception as e:  # noqa: BLE001 - bus stays live even if SQLite is unavailable
            print(f"event bus persist failed: {type(e).__name__}: {e}")

    def intelligence_history(self, symbol: str, limit: int = 64) -> list[dict]:
        """Bounded cross-process edge read model; never use stale memory fallback.

        Match the exact broker symbol inside JSON. Arrival order (rowid), not a
        producer-supplied timestamp, lets recovery/unavailable revoke old flags.
        A short read timeout avoids delaying deterministic entry guards.
        """
        try:
            con = sqlite3.connect(f"file:{self.db}?mode=ro", uri=True, timeout=0.25)
            try:
                rows = con.execute(
                    "SELECT event_id,ts,type,source,payload,trace_id FROM events "
                    "WHERE type='luxalgo_edge_stats' AND source='luxalgo_orchestrator' "
                    "AND json_valid(payload) AND json_extract(payload,'$.edge_data.symbol')=? "
                    "ORDER BY rowid DESC LIMIT ?", (symbol, max(1, min(int(limit), 64)))
                ).fetchall()
            finally:
                con.close()
            return [dict(zip(("event_id", "ts", "type", "source", "payload", "trace_id"),
                             (*r[:4], json.loads(r[4]), r[5]))) for r in rows]
        except (sqlite3.Error, ValueError, TypeError):
            return []

    def history(self, limit: int = 100, trace_id: str | None = None,
                type: str | None = None, source: str | None = None,
                exclude: str | None = None) -> list[dict]:
        """Last `limit` envelopes newest-first. Optional filters: trace_id (the
        end-to-end chain id), type, source, and exclude (drop one high-volume
        type, e.g. pnl_update, so signal-bearing events stay visible).
        Falls back to memory when SQLite is unreadable."""
        try:
            con = sqlite3.connect(f"file:{self.db}?mode=ro", uri=True, timeout=10)
            try:
                q = "SELECT event_id, ts, type, source, payload, trace_id FROM events"
                params: list = []
                conds = []
                if trace_id is not None:
                    conds.append("trace_id=?"); params.append(trace_id)
                if type is not None:
                    conds.append("type=?"); params.append(type)
                if source is not None:
                    conds.append("source=?"); params.append(source)
                if exclude is not None:
                    conds.append("type!=?"); params.append(exclude)
                if conds:
                    q += " WHERE " + " AND ".join(conds)
                q += " ORDER BY ts DESC, event_id DESC LIMIT ?"
                params.append(int(limit))
                rows = con.execute(q, params).fetchall()
            finally:
                con.close()
            return [{"event_id": r[0], "ts": r[1], "type": r[2], "source": r[3],
                     "payload": json.loads(r[4] or "{}"), "trace_id": r[5]} for r in rows]
        except Exception:  # noqa: BLE001
            data = list(self._memory)
            if trace_id is not None:
                data = [e for e in data if e["trace_id"] == trace_id]
            if type is not None:
                data = [e for e in data if e["type"] == type]
            if source is not None:
                data = [e for e in data if e["source"] == source]
            if exclude is not None:
                data = [e for e in data if e["type"] != exclude]
            data.sort(key=lambda e: e["ts"], reverse=True)
            return data[:int(limit)]


# Module-level singleton so every component shares one bus without passing it around.
bus = EventBus()
publish = bus.publish
subscribe = bus.subscribe
history = bus.history

__all__ = ["EVENT_TYPES", "make_event", "new_trace_id", "EventBus",
           "bus", "publish", "subscribe", "history"]

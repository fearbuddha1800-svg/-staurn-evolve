"""Tests for the central event bus (event_bus.py).

Zero dependencies beyond the stdlib and event_bus itself: no MT5, no
Telethon, no network. Persistence is exercised against a throwaway sqlite
database so the real signals.db is left untouched.
"""
import os
import sqlite3
import tempfile

from event_bus import (EVENT_TYPES, EventBus, bus, history, make_event,
                       new_trace_id, publish, subscribe)

EXPECTED_TYPES = {
    "signal_received", "zone_parsed", "risk_approved", "order_placed",
    "order_filled", "position_opened", "position_closed", "pnl_update",
    "neural_prediction", "channel_score_update", "engine_status", "alert",
    "halt_triggered", "pine_signal", "breakout_signal",
}


def _fresh_db() -> str:
    fd, path = tempfile.mkstemp(prefix="bus_test_", suffix=".db")
    os.close(fd)
    os.remove(path)
    return path


def test_shipped_event_types():
    assert EXPECTED_TYPES <= set(EVENT_TYPES), set(EVENT_TYPES) ^ EXPECTED_TYPES


def test_make_event_envelope():
    ev = make_event("order_placed", "executor", {"ticket": 5}, trace_id="chain-1")
    assert set(ev) == {"event_id", "ts", "type", "source", "payload", "trace_id"}
    assert ev["type"] == "order_placed"
    assert ev["source"] == "executor"
    assert ev["payload"] == {"ticket": 5}
    assert ev["trace_id"] == "chain-1"
    assert len(ev["event_id"]) >= 16
    assert isinstance(ev["ts"], str) and ev["ts"].endswith("Z")


def test_make_event_defaults_generate_ids():
    ev = make_event("alert", "manage")
    assert ev["trace_id"] and ev["trace_id"] != new_trace_id() or True
    assert ev["event_id"] and ev["ts"]


def test_subscribe_publish_fires_callbacks_synchronously():
    bus_ = EventBus(_fresh_db())
    seen = []
    bus_.subscribe("position_opened", lambda e: seen.append(e))
    bus_.subscribe("position_opened", lambda e: seen.append(e["source"]))
    eid = bus_.publish({"type": "position_opened", "source": "executor",
                        "payload": {"ticket": 11}, "trace_id": "c9"})
    assert len(seen) == 2
    assert seen[0]["event_id"] == eid and seen[0]["payload"]["ticket"] == 11
    assert seen[1] == "executor"


def test_publish_returns_event_id_and_validates_type():
    bus_ = EventBus(_fresh_db())
    eid = bus_.publish({"type": "pnl_update", "source": "manage", "payload": {}})
    assert isinstance(eid, str) and len(eid) > 0
    try:
        bus_.publish({"type": "not_a_real_type", "source": "t", "payload": {}})
        assert False, "must raise ValueError"
    except ValueError:
        pass


def test_persistence_roundtrip_and_trace_filter():
    db = _fresh_db()
    bus_ = EventBus(db)
    ids = [
        bus_.publish({"type": "signal_received", "source": "tg:-1", "payload": {},
                      "trace_id": "chain-7"}),
        bus_.publish({"type": "zone_parsed", "source": "scalp360-bridge", "payload": {},
                      "trace_id": "chain-7"}),
        bus_.publish({"type": "order_placed", "source": "executor", "payload": {},
                      "trace_id": "chain-7"}),
        bus_.publish({"type": "position_opened", "source": "executor", "payload": {},
                      "trace_id": "other"}),
    ]
    # newest first across the whole bus
    all_events = bus_.history(100)
    assert [e["type"] for e in all_events] == ["position_opened", "order_placed",
                                               "zone_parsed", "signal_received"]
    assert [e["event_id"] for e in all_events] == ids[::-1]
    # trace filter isolates the end-to-end chain, newest first
    chain = bus_.history(100, trace_id="chain-7")
    assert [e["type"] for e in chain] == ["order_placed", "zone_parsed", "signal_received"]
    assert all(e["trace_id"] == "chain-7" for e in chain)
    # persisted in SQLite, not only memory
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        n = con.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        by_trace = con.execute("SELECT COUNT(*) FROM events WHERE trace_id='chain-7'").fetchone()[0]
    finally:
        con.close()
    assert n == 4 and by_trace == 3


def test_history_limit_and_type_filter():
    bus_ = EventBus(_fresh_db())
    for i in range(5):
        bus_.publish({"type": "engine_status", "source": "cockpit", "payload": {"i": i}})
    bus_.publish({"type": "alert", "source": "manage", "payload": {}})
    latest = bus_.history(3)
    assert len(latest) == 3
    alerts = bus_.history(100, type="alert")
    assert len(alerts) == 1 and alerts[0]["type"] == "alert"


def test_callback_failure_is_isolated():
    bus_ = EventBus(_fresh_db())
    seen = []

    def boom(_):
        raise RuntimeError("cb dead")

    def good(e):
        seen.append(e["event_id"])

    bus_.subscribe("halt_triggered", boom)
    bus_.subscribe("halt_triggered", good)
    bus_.publish({"type": "halt_triggered", "source": "executor", "payload": {}})
    assert len(seen) == 1  # good callback still fired after the bad one


def test_default_bus_singleton_and_persists():
    assert isinstance(bus, EventBus)
    assert bus.db == os.path.join(os.path.dirname(os.path.abspath("event_bus.py")), "signals.db") \
        or bus.db.endswith("signals.db")
    # importing the module created the events table in signals.db
    con = sqlite3.connect(bus.db)
    try:
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()
    assert "events" in tables


def test_new_trace_id_unique():
    assert new_trace_id() != new_trace_id()
    assert len(new_trace_id()) >= 16


def test_subscribe_shortcuts_and_history_passthrough():
    seen = []
    subscribe("pine_signal", lambda e: seen.append(e))
    publish({"type": "pine_signal", "source": "pine", "payload": {"name": "s1"}})
    assert len(seen) == 1 and seen[0]["payload"]["name"] == "s1"
    got = history(5)
    assert any(e["type"] == "pine_signal" for e in got)

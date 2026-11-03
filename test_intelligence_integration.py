"""Offline contracts only: fake MT5, isolated SQLite, no network/orders."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import types
from datetime import datetime, timezone

import pytest

ROOT = Path(__file__).resolve().parent


@pytest.fixture
def relay(tmp_path, monkeypatch):
    monkeypatch.setenv("SIGNAL_RELAY_EVENT_DB", str(tmp_path / "singleton.db"))
    fake = types.ModuleType("MetaTrader5")
    fake.order_send = lambda *a, **k: pytest.fail("order_send forbidden")
    monkeypatch.setitem(sys.modules, "MetaTrader5", fake)
    eb = importlib.import_module("event_bus")
    ex = importlib.import_module("executor")
    monkeypatch.setattr(ex, "mt5", fake)
    isolated = eb.EventBus(str(tmp_path / "events.db"))
    monkeypatch.setattr(ex, "bus", isolated)
    monkeypatch.setattr(ex, "DB", str(tmp_path / "trades.db"))
    return ex, isolated, eb


def decay_event(eb, now=None, symbol="XAUUSD", **changes):
    stamp = datetime.fromtimestamp(time.time() if now is None else now, timezone.utc).isoformat()
    data = {"symbol": symbol, "preset": "validated-fixture", "alpha_decay": True,
            "evidence": {"validated": True, "after_costs": True, "n": 50, "reference_n": 50,
                         "baseline_expectancy_r": 0.2, "current_expectancy_r": -0.2,
                         "confidence": 0.95, "method": "offline validated fixture",
                         "source": "fixture://holdout-report"}}
    data.update(changes)
    return eb.make_event("luxalgo_edge_stats", "luxalgo_orchestrator",
                         {"available": True, "observed_at": stamp, "edge_data": data}, ts=stamp)


def test_import_with_fake_mt5_in_fresh_process(tmp_path):
    env = dict(os.environ, PYTHONPATH="", SIGNAL_RELAY_EVENT_DB=str(tmp_path / "import.db"))
    code = "import sys,types; sys.modules['MetaTrader5']=types.ModuleType('MetaTrader5'); import executor; print('import-ok')"
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    assert "import-ok" in result.stdout


@pytest.mark.parametrize("kind", ["luxalgo_regime_shift", "luxalgo_whale_options", "luxalgo_edge_stats"])
def test_each_event_persists_and_replays(relay, kind):
    _, bus, eb = relay
    calls = []
    bus.subscribe(kind, calls.append)
    event = eb.make_event(kind, "luxalgo_orchestrator", {"available": False, "reason": "fixture"})
    bus.publish(event)
    fresh = eb.EventBus(bus.db)
    assert fresh.history(type=kind)[0] == event
    assert calls == [event]
    from scalp360.events import BUS_EVENT_TYPES
    assert eb.EVENT_TYPES == BUS_EVENT_TYPES


def test_real_second_process_refresh_and_recovery(relay):
    ex, bus, eb = relay
    assert ex.intelligence_block_reason("XAUUSD") is None
    env = dict(os.environ, PYTHONPATH="", SIGNAL_RELAY_EVENT_DB=bus.db)
    code = "import json,sys; from event_bus import bus; bus.publish(json.loads(sys.argv[1]))"
    event = decay_event(eb)
    for block in (True, False):
        event["event_id"] = eb.new_trace_id()
        event["payload"]["edge_data"]["alpha_decay"] = block
        result = subprocess.run([sys.executable, "-c", code, json.dumps(event)], cwd=ROOT, env=env,
                                capture_output=True, text=True, timeout=15)
        assert result.returncode == 0, result.stderr
        assert bool(ex.intelligence_block_reason("XAUUSD")) is block
    assert not bus._memory  # parent received no in-process callbacks/publication


def test_expiry_exact_symbol_and_unavailable_recovery(relay):
    ex, bus, eb = relay
    now = time.time()
    bus.publish(decay_event(eb, now=now))
    assert ex.intelligence_block_reason("XAUUSD", now=now + 1)
    assert ex.intelligence_block_reason("XAUUSD", now=now + 301) is None
    assert ex.intelligence_block_reason("XAU", now=now + 1) is None
    assert ex.intelligence_block_reason("XAUUSD.r", now=now + 1) is None
    event = decay_event(eb)
    event["payload"]["available"] = False
    bus.publish(event)
    assert ex.intelligence_block_reason("XAUUSD") is None
    bus.publish(decay_event(eb))
    assert ex.intelligence_block_reason("XAUUSD")


@pytest.mark.parametrize("change", [
    {"alpha_decay": None}, {"alpha_decay": "true"}, {"evidence": {}},
    {"evidence": {"validated": True}}, {"evidence": []},
    {"evidence": {"n": 1000, "lo": 0.49, "hi": 0.50}},
])
def test_invalid_informational_missing_never_block(relay, change):
    ex, bus, eb = relay
    bus.publish(decay_event(eb, **change))
    assert ex.intelligence_block_reason("XAUUSD") is None


@pytest.mark.parametrize("field,value", [("n", 29), ("reference_n", 0), ("n", True),
    ("confidence", float("nan")), ("confidence", 0.9), ("after_costs", False),
    ("current_expectancy_r", 0.1), ("source", ""), ("method", ""), ("validated", "true")])
def test_evidence_thresholds(relay, field, value):
    ex, bus, eb = relay
    event = decay_event(eb)
    event["payload"]["edge_data"]["evidence"][field] = value
    bus.publish(event)
    assert ex.intelligence_block_reason("XAUUSD") is None


def test_bad_and_future_timestamps_and_missing_db(relay, monkeypatch, tmp_path):
    ex, bus, eb = relay
    for stamp in ("bad", "2026-01-01", datetime.fromtimestamp(time.time()+600, timezone.utc).isoformat()):
        event = decay_event(eb)
        event["payload"]["observed_at"] = stamp
        bus.publish(event)
        assert ex.intelligence_block_reason("XAUUSD") is None
    monkeypatch.setattr(bus, "db", str(tmp_path / "missing.db"))
    assert ex.intelligence_block_reason("XAUUSD") is None


def test_guard_explicit_block_and_existing_halt(relay, monkeypatch):
    ex, bus, eb = relay
    bus.publish(decay_event(eb))
    assert ex._guards({}, "XAUUSD", .01, None)[0] is False
    bus.publish(decay_event(eb, alpha_decay=False))
    monkeypatch.setattr(ex, "halted", lambda: True)
    assert ex._guards({}, "XAUUSD", .01, None) == (False, "HALT file present - trading paused")

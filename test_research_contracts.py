"""Offline research contract regressions. No expected failures.
Run explicitly: PYTHONPATH= python -B test_research_contracts.py
Never discover test_loop.py. Fake MT5/event bus; only temporary DBs/candles.
"""
from contextlib import closing
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import math
import os
import random
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
SCRATCH = Path.home() / ".hermes/cache/scratch"
SCRATCH.mkdir(parents=True, exist_ok=True)
sys.dont_write_bytecode = True


def load_source(name, relative, dependencies=None):
    spec = importlib.util.spec_from_file_location(name, BASE / relative)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {name: module, **(dependencies or {})}):
        spec.loader.exec_module(module)
    return module


def fake_mt5():
    m = types.ModuleType("MetaTrader5")
    for name in ("M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"):
        setattr(m, "TIMEFRAME_" + name, name)
    m.terminal_info = lambda: None
    m.initialize = lambda: False
    m.shutdown = lambda: None
    # Deliberately has no order_send: an accidental broker call must fail.
    return m


class ResearchContracts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="research-contracts-", dir=SCRATCH)
        self.addCleanup(self.tmp.cleanup)
        self.db = str(Path(self.tmp.name) / "labels.db")
        self.nlc = load_source("audit_nlc", "neural_label_collector.py")
        self.mt5 = fake_mt5()
        self.pinets = load_source("audit_pinets", "pinets_runner.py", {"MetaTrader5": self.mt5})
        self.pine = load_source("audit_pine", "pine_runner.py", {"pinets_runner": self.pinets})
        event_bus = types.ModuleType("event_bus")
        event_bus.bus = types.SimpleNamespace(publish=lambda *a, **k: None)
        self.neural = load_source("audit_neural", "scalp360/neural.py", {"event_bus": event_bus})
        self.market = {"rsi14": 50.0, "atr14": 2.0, "spread": None,
                       "spread_points": None, "bars_used": 80}

    def entry(self, ticket=1, ts=1000):
        with patch.object(self.nlc, "_capture_market_features", return_value=self.market), \
                patch.object(self.nlc, "_load_config", return_value={}):
            return self.nlc.record_entry(ticket, "XAUUSD", "buy", 100, 90, None,
                                         None, 20261014, entry_ts=ts, db=self.db)

    def test_label_idempotence_and_first_close_wins(self):
        first = self.entry()
        self.assertEqual(first, self.entry())
        self.assertEqual(1, self.nlc.record_close(1, 0.2, db=self.db))
        self.assertEqual(1, self.nlc.record_close(1, -1.0, db=self.db))
        self.assertEqual({"total": 1, "complete": 1, "pending": 0}, self.nlc.label_counts(self.db))

    def test_features_are_chronological_and_25_dimensional(self):
        self.entry(1, 2000)
        self.entry(2, 1000)
        self.nlc.record_close(1, 1, db=self.db)
        self.nlc.record_close(2, -1, db=self.db)
        X, y = self.nlc.get_training_data(self.db)
        self.assertEqual([0, 1], y)
        self.assertTrue(all(len(row) == 25 and all(math.isfinite(v) for v in row) for row in X))

    def test_insufficient_sample_gate_never_trains(self):
        def forbidden(_):
            raise AssertionError("small sample trained")
        report = self.neural.evaluate([(0.0,)] * 299, [1] * 299, model_factory=forbidden)
        self.assertIn("insufficient labels", report.decision)
        self.assertEqual(0, report.n_test)

    def test_candle_fetch_drops_forming_bar(self):
        rates = [(100 + i, 1, 2, 0, 1.5, 10) for i in range(4)]
        with patch.object(self.mt5, "copy_rates_from_pos", create=True, return_value=rates):
            candles = self.pinets.fetch_candles("XAUUSD", "H1", 3)
        self.assertEqual(3, len(candles))
        self.assertEqual(102000, candles[-1]["openTime"])

    def test_pine_record_is_paper_only(self):
        with patch.object(self.pine, "paper_mode", return_value=True):
            self.pine.record_signal({"name": "unit", "action": "buy", "price": 100}, db=self.db)
        with closing(sqlite3.connect(self.db)) as con:
            row = con.execute("SELECT status,ticket FROM trades").fetchone()
        self.assertEqual(("pine_signal", None), row)
        self.assertFalse(hasattr(self.mt5, "order_send"))

    def test_auc_ties_must_have_half_credit(self):
        self.assertEqual(0.5, self.neural._auc([0.5] * 4, [0, 1, 0, 1]))

    def test_auc_tied_ranks_match_pairwise_oracle(self):
        rng = random.Random(19)
        for _ in range(50):
            scores = [rng.choice([0.1, 0.5, 0.9]) for _ in range(20)]
            labels = [0, 1] * 10
            pos = [s for s, y in zip(scores, labels) if y]
            neg = [s for s, y in zip(scores, labels) if not y]
            expected = sum(1 if p > n else 0.5 if p == n else 0
                           for p in pos for n in neg) / (len(pos) * len(neg))
            self.assertAlmostEqual(expected, self.neural._auc(scores, labels))
        self.assertEqual(1, self.neural._auc([0, 1], [0, 1]))
        self.assertEqual(0, self.neural._auc([1, 0], [0, 1]))
        self.assertEqual(0.5, self.neural._auc([1, 1], [1, 1]))

    def test_auc_rejects_nonfinite_or_misaligned_inputs(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.assertRaises(ValueError):
                self.neural._auc([0.5, value], [0, 1])
        with self.assertRaises(ValueError):
            self.neural._auc([0.5], [0, 1])

    def test_nonfinite_realized_r_is_not_a_label(self):
        self.entry()
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.nlc.record_close(1, value, db=self.db)
            self.assertEqual(1, self.nlc.label_counts(self.db)["pending"])
        self.assertEqual(0, self.nlc.record_close(1, 0.0, db=self.db))

    def test_backfill_excludes_bar_not_closed_at_entry(self):
        epoch = 100000
        bars = [{"time": epoch - (20 - i) * 900, "high": 2, "low": 0, "close": 1}
                for i in range(21)]
        m = types.SimpleNamespace(TIMEFRAME_M15=15, copy_rates_from=lambda *args: bars)
        with patch.object(self.nlc, "_mt5_mod", return_value=m):
            selected = self.nlc._bars_at("XAUUSD", epoch)
        self.assertTrue(all(b["time"] + 900 <= epoch for b in selected))

    def test_backfill_fetch_anchor_is_entry_not_old_lookback(self):
        calls = []
        m = types.SimpleNamespace(TIMEFRAME_M15=15,
                                  copy_rates_from=lambda *args: calls.append(args))
        with patch.object(self.nlc, "_mt5_mod", return_value=m):
            self.nlc._bars_at("XAUUSD", 100000)
        self.assertEqual(100000, calls[0][2])

    def test_backfill_m15_close_boundary_and_recent_count(self):
        bars = [{"time": 900 * i} for i in range(121)]
        calls = []
        def copy_rates(sym, tf, anchor, count):
            calls.append((anchor, count))
            return [b for b in bars if b["time"] <= anchor][-count:]
        m = types.SimpleNamespace(TIMEFRAME_M15=15, copy_rates_from=copy_rates)
        with patch.object(self.nlc, "_mt5_mod", return_value=m):
            for epoch, last_open in ((90000, 89100), (89999, 88200), (90001, 89100)):
                with self.subTest(epoch=epoch):
                    selected = self.nlc._bars_at("XAUUSD", epoch)
                    self.assertEqual(80, len(selected))
                    self.assertEqual(last_open, selected[-1]["time"])
                    self.assertTrue(all(b["time"] + 900 <= epoch for b in selected))
                    self.assertEqual((epoch, 81), calls[-1])

    def test_simultaneous_closes_preserve_first_committed_outcome(self):
        self.entry()
        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(lambda r: self.nlc.record_close(1, r, db=self.db),
                                     [1, -1] * 8))
        self.assertEqual(1, len(set(outcomes)))
        with closing(sqlite3.connect(self.db)) as con:
            outcome, features = con.execute("SELECT outcome,features FROM neural_labels").fetchone()
        self.assertEqual(outcome, int(json.loads(features)["profit_r"] > 0))

    def test_runner_handles_non_dict_bridge_result(self):
        entry = {"symbol": "XAUUSD", "timeframe": "H1", "path": str(BASE / "strategies/ema_cross.pine")}
        for value in (None, [], [1], "bad", 7, {"ok": True, "latest_signal": [1]}):
            with self.subTest(value=value), \
                    patch.object(self.pine, "_resolve", return_value=entry), \
                    patch.object(self.pinets, "run_pine_strategy", return_value=value):
                result = self.pine.run_strategy("unit")
            self.assertFalse(result["ok"])
            self.assertTrue(result["error"])

    def test_pine_duplicate_bar_signal_is_idempotent(self):
        signal = {"name": "unit", "action": "buy", "price": 100, "ts": "same-bar"}
        with patch.object(self.pine, "paper_mode", return_value=True):
            self.pine.record_signal(signal, db=self.db)
            self.pine.record_signal(signal, db=self.db)
        with closing(sqlite3.connect(self.db)) as con:
            count = con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        self.assertEqual(1, count)

    def test_existing_mt5_attachment_is_not_shutdown(self):
        with patch.object(self.mt5, "terminal_info", return_value=object()), \
                patch.object(self.mt5, "shutdown") as shutdown, \
                patch.object(self.pinets, "fetch_candles", return_value=[]):
            self.pinets.run_pine_strategy("unused.pine")
        shutdown.assert_not_called()

    def test_signal_identity_survives_new_poll_timestamp_and_concurrent_writers(self):
        entry = {"symbol": "XAUUSD", "timeframe": "H1", "path": str(BASE / "strategies/ema_cross.pine")}
        result = {"ok": True, "latest_signal": {"type": "long", "time": 1700000000000, "price": 100}}
        with patch.object(self.pine, "_resolve", return_value=entry), \
                patch.object(self.pinets, "run_pine_strategy", return_value=result), \
                patch.object(self.pine, "_now_iso", side_effect=["poll-a", "poll-b"]):
            first, second = self.pine.run_strategy("unit"), self.pine.run_strategy("unit")
        self.assertEqual(first["signal_time"], second["signal_time"])
        with patch.object(self.pine, "paper_mode", return_value=True):
            with ThreadPoolExecutor(max_workers=8) as pool:
                ids = list(pool.map(lambda s: self.pine.record_signal(s, db=self.db), [first, second] * 8))
            self.assertEqual(1, len(set(ids)))
            variants = [dict(first, signal_time=1700003600000), dict(first, action="sell"),
                        dict(first, symbol="EURUSD"), dict(first, timeframe="M15"), dict(first, name="other")]
            for s in variants:
                self.assertNotEqual(ids[0], self.pine.record_signal(s, db=self.db))
        with closing(sqlite3.connect(self.db)) as con:
            self.assertEqual(6, con.execute("SELECT COUNT(*) FROM trades").fetchone()[0])
            self.assertEqual(0, con.execute("SELECT COUNT(*) FROM trades WHERE ticket IS NOT NULL").fetchone()[0])

    def test_attachment_ownership_on_fetch_error_and_initialization_failure(self):
        for attached in (True, False):
            with self.subTest(attached=attached), \
                    patch.object(self.mt5, "terminal_info", return_value=object() if attached else None), \
                    patch.object(self.mt5, "initialize", return_value=True) as initialize, \
                    patch.object(self.mt5, "shutdown") as shutdown, \
                    patch.object(self.pinets, "fetch_candles", side_effect=RuntimeError("synthetic")):
                with self.assertRaises(RuntimeError):
                    self.pinets.run_pine_strategy("unused.pine")
                self.assertEqual(0 if attached else 1, shutdown.call_count)
                self.assertEqual(0 if attached else 1, initialize.call_count)
        with patch.object(self.mt5, "shutdown") as shutdown:
            self.assertFalse(self.pinets.run_pine_strategy("unused.pine")["ok"])
            shutdown.assert_not_called()

    def test_bridge_response_validation_and_temp_cleanup(self):
        candle = {"openTime": 1700000000000, "open": 100, "high": 102, "low": 99, "close": 101}
        paths = []
        def completed(args, **kwargs):
            paths.append(args[3])
            self.assertTrue(Path(args[3]).exists())
            return types.SimpleNamespace(returncode=0, stdout="null", stderr="")
        for attached in (True, False):
            with self.subTest(attached=attached), \
                    patch.object(self.mt5, "terminal_info", return_value=object() if attached else None), \
                    patch.object(self.mt5, "initialize", return_value=True), \
                    patch.object(self.mt5, "shutdown") as shutdown, \
                    patch.object(self.pinets, "fetch_candles", return_value=[candle]), \
                    patch.object(self.pinets.subprocess, "run", side_effect=completed):
                self.assertFalse(self.pinets.run_pine_strategy("unused.pine")["ok"])
                self.assertEqual(0 if attached else 1, shutdown.call_count)
        self.assertTrue(all(not Path(p).exists() for p in paths))

    def node_bridge(self, bridge):
        if not shutil.which("node"):
            self.skipTest("Node unavailable")
        if not (BASE.parent / "luxalgo/PineTS/dist/pinets.min.cjs").exists():
            self.skipTest("PineTS built runtime unavailable")
        pine = Path(self.tmp.name) / "indicator.pine"
        pine.write_text('//@version=5\nindicator("Audit", overlay=true)\nplot(close, title="Close")\n', encoding="utf-8")
        candles = Path(self.tmp.name) / "candles.json"
        candles.write_text(json.dumps([{"openTime": 1700000000000 + i * 3600000,
                                       "open": 100 + i, "high": 102 + i,
                                       "low": 99 + i, "close": 101 + i, "volume": 10}
                                      for i in range(20)]), encoding="utf-8")
        result = subprocess.run(["node", str(BASE / bridge), str(pine), str(candles), "XAUUSD", "60"],
                                capture_output=True, text=True, timeout=40, cwd=BASE)
        self.assertEqual(0, result.returncode, result.stderr[:300])
        data = json.loads(result.stdout)
        self.assertTrue(data["ok"], data.get("error"))
        return data

    def test_actual_node_series_bridge_returns_plot_values(self):
        data = self.node_bridge("pine_series_bridge.js")
        self.assertEqual(20, data["bars"])
        self.assertEqual(list(range(101, 121)), data["series"]["Close"]["values"])

    def test_signal_bridge_must_not_drop_object_plot_points(self):
        data = self.node_bridge("pinets_bridge.js")
        self.assertIn("Close", data["plots"])
        self.assertEqual(120, data["plots"]["Close"]["latest"])
        self.assertEqual(list(range(111, 121)), data["plots"]["Close"]["recent"])
        self.assertEqual(20, data["plots"]["Close"]["count"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

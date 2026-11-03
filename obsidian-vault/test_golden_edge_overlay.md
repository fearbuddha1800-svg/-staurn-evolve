---
slug: test_golden_edge_overlay
type: note
graph: gitnexus
---

"""Offline regression fixtures, NOT training labels or trading performance."""
import json
import math
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from ai_overlay import AIOverlay, FEATURE_VERSION, PLOT_ALIASES, StubNeuralModel, extract_features


class GoldenEdgeTests(unittest.TestCase):
    def test_neutral_is_independent_of_activity_and_threshold(self):
        for active in (True, False):
            result = AIOverlay(min_confidence=.99).evaluate(
                {"action": "BUY", "active": active, "confidence": .99}, {})
            self.assertEqual(result.setup_confidence, .5)
            self.assertEqual(result.direction, "LONG")
            self.assertEqual(result.model_status, "untrained")
            self.assertFalse(result.passes_threshold)
            self.assertEqual(result.mode, "shadow")

    def test_plot_titles_match_source(self):
        source = Path(__file__).with_name("strategies").joinpath("golden_eye_trend_regime.pine").read_text(encoding="utf-8")
        for name in ("regime", "strength", "consensus", "persistence", "acceleration",
                     "disagreement", "dmi_plus", "dmi_minus", "adx", "mtf_agreement", "displacement_atr", "er"):
            self.assertTrue(any('"' + alias + '"' in source for alias in PLOT_ALIASES[name]), name)

    def test_full_payload_and_short_alignment(self):
        eye = dict(regime=1, strength=.8, consensus=1, persistence=.7,
                   acceleration=-.2, disagreement_index=.1, dmi_plus=10,
                   dmi_minus=30, adx=25, mtf_agreement=.75, displacement_atr=-2, er=.6)
        ctx = dict(rsi=45, atr=2, spread=.2, policy_allowed=True,
                   bar_close_time="2026-01-01T08:00:00-05:00", session="new_york",
                   symbol="XAUUSD", policy="golden_edge_v1", timeframe="M15", setup_id="edge_pullback")
        result = AIOverlay().evaluate({"action": "SELL", "golden_eye": eye}, {}, ctx)
        self.assertEqual(result.regime, "trend")
        self.assertAlmostEqual(result.regime_bias, -.5)
        self.assertAlmostEqual(result.features["dmi_alignment"], .5)
        self.assertAlmostEqual(result.features["spread_atr"], .1)
        self.assertEqual(result.features["displacement_atr_aligned"], 2)
        self.assertEqual(result.features["hour"], 13)
        self.assertEqual(result.missing_features, [])
        self.assertEqual(result.categories["policy"], "golden_edge_v1")

    def test_plot_shapes_and_missing_last(self):
        plots = {"TrendStrength (uncalibrated)": {"latest": .8},
                 "TrendConsensus (3-group agreement)": {"data": [{"value": .6}]},
                 "TrendPersistence": [.4, .5], "TrendAcceleration": {"value": -.2},
                 "QG19 Efficiency Ratio": {"data": [.9, None]}}
        f, _, missing = extract_features({"direction": "long"}, {"plots": plots})
        self.assertEqual(f["strength"], .8)
        self.assertEqual(f["consensus"], .6)
        self.assertEqual(f["persistence"], .5)
        self.assertEqual(f["acceleration_aligned"], -.2)
        self.assertIn("er", missing)
        self.assertEqual(f["er_missing"], 1)

    def test_invalid_values_never_leak_nonfinite(self):
        f, _, missing = extract_features({}, {}, dict(
            atr=0, spread=-1, rsi=101, hour=24, regime=1.5,
            strength=float("nan"), adx=float("inf"), consensus=2, dmi_plus=-10))
        for key in ("atr", "spread", "rsi", "hour", "regime", "strength", "adx", "consensus", "dmi_plus"):
            self.assertIn(key, missing)
        self.assertTrue(all(math.isfinite(x) for x in f.values()))
        json.dumps(f, allow_nan=False)

    def test_schema_is_fixed_and_does_not_read_outcomes(self):
        empty = extract_features({}, {})[0]
        full = extract_features({"action": "BUY", "profit": 123, "label": 1}, {"plots": {"random": 5}})[0]
        self.assertEqual(set(empty), set(full))
        self.assertNotIn("profit", full)
        self.assertNotIn("label", full)
        self.assertEqual(set(StubNeuralModel().feature_names()), set(empty))

    def test_context_precedence_and_no_stale_fallback(self):
        f, _, _ = extract_features({"golden_eye": {"strength": .6}},
                                  {"plots": {"strength": .7}}, {"strength": None})
        self.assertEqual(f["strength_missing"], 1)
        self.assertEqual(extract_features({}, {}, {"bar_close_time": "2026-01-01T12:00:00"})[0]["hour_missing"], 1)

    def test_dmi_zero_denominator_and_unknown_regime(self):
        p = AIOverlay().evaluate({"action": "BUY"}, {}, {"dmi_plus": 0, "dmi_minus": 0})
        self.assertEqual(p.regime_bias, 0)
        self.assertEqual(p.regime, "unknown")
        self.assertEqual(p.features["dmi_balance_missing"], 1)

    def test_model_adapter_and_error_paths(self):
        class Model:
            is_trained = True
            feature_version = FEATURE_VERSION
            def predict_setup(self, features, categories):
                self.categories = categories
                return {"confidence": .7, "direction": "SHORT"}
        model = Model()
        p = AIOverlay(model, .6).evaluate({"action": "BUY", "symbol": "EURUSD"}, {})
        self.assertEqual(p.confidence, .7)
        self.assertEqual(p.direction, "LONG")  # Never reverse the rules signal.
        self.assertTrue(p.passes_threshold)
        self.assertEqual(p.model_status, "trained_shadow")
        self.assertEqual(model.categories["symbol"], "EURUSD")
        model.feature_version = "old"
        self.assertEqual(AIOverlay(model).evaluate({}, {}).model_status, "invalid")
        model.feature_version = FEATURE_VERSION
        for value in (float("nan"), float("inf"), -1, 1.1, None):
            with patch.object(model, "predict_setup", return_value={"confidence": value}):
                p = AIOverlay(model).evaluate({}, {})
                self.assertEqual(p.confidence, .5)
                self.assertFalse(p.passes_threshold)
                self.assertEqual(p.model_status, "invalid")
        with patch.object(model, "predict_setup", side_effect=RuntimeError("broken")):
            self.assertEqual(AIOverlay(model).evaluate({}, {}).confidence, .5)

    def test_watcher_envelope_without_broker_or_database(self):
        import importlib.util
        from unittest.mock import MagicMock
        modules = {name: MagicMock() for name in (
            "MetaTrader5", "pinets_runner", "watch_assignments", "event_bus", "alert_dispatcher")}
        modules["pinets_runner"].run_pine_strategy.return_value = {
            "ok": True, "bars": 500, "golden_eye": {"regime": 1, "dmi_plus": 30, "dmi_minus": 10}}
        modules["pinets_runner"].extract_signal.return_value = {"action": "BUY", "price": 2000}
        path = Path(__file__).with_name("signal_watcher.py")
        spec = importlib.util.spec_from_file_location("golden_edge_watcher_test", path)
        watcher = importlib.util.module_from_spec(spec)
        with patch.dict("sys.modules", modules):
            spec.loader.exec_module(watcher)
        assignment = SimpleNamespace(id="test", symbol="XAUUSD", timeframe="M15",
                                     strategy_id="golden_eye_trend_regime", last_signal_hash=None)
        event = watcher._poll_assignment(assignment, AIOverlay(), True)
        self.assertEqual(event["ai"]["setup_confidence"], .5)
        self.assertEqual(event["ai"]["regime_bias"], .5)
        self.assertEqual(event["ai"]["categories"]["symbol"], "XAUUSD")
        self.assertEqual(event["ai"]["feature_version"], FEATURE_VERSION)
        json.dumps(event, allow_nan=False)
        assignment.last_signal_hash = event["signal_hash"]
        self.assertIsNone(watcher._poll_assignment(assignment, AIOverlay(), True))
        assignment.last_signal_hash = None
        self.assertEqual(watcher._poll_assignment(assignment, None, False)["ai"]["rationale"], "ai_disabled")
        modules["event_bus"].publish.assert_not_called()
        modules["MetaTrader5"].initialize.assert_not_called()

    def test_untrained_model_cannot_smuggle_confidence(self):
        model = SimpleNamespace(is_trained=False, predict=lambda f: {"confidence": .99})
        self.assertEqual(AIOverlay(model).evaluate({}, {}).confidence, .5)
        for threshold in (-1, 2, float("nan")):
            with self.assertRaises(ValueError):
                AIOverlay(min_confidence=threshold)


if __name__ == "__main__":
    unittest.main()


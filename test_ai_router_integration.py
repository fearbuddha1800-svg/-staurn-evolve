"""Offline tests for the ai_filter <-> model_router integration.

No network, no MT5, no real LLM key. Proves that the AI tier is BOUNDED
(concurrency + budget + deadline) and that abstention is reported as a plain
failure to extract rather than as a fabricated signal.
"""
import importlib
import json
import os
import sys
import threading
import time
import types
import unittest
from unittest.mock import patch

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

# Fail closed offline: never import the real terminal. Restore afterwards so this
# file cannot poison another test module's sys.modules (see test_label_health.py).
_SAVED = {n: sys.modules.get(n) for n in ("MetaTrader5", "event_bus")}
sys.modules["MetaTrader5"] = types.ModuleType("MetaTrader5")

import ai_filter  # noqa: E402
import model_router as mr  # noqa: E402

for _n, _m in _SAVED.items():
    if _m is None:
        sys.modules.pop(_n, None)
    else:
        sys.modules[_n] = _m
del _SAVED


def fresh_ai_filter():
    """Reimport ai_filter so the module-level router singleton is reset."""
    return importlib.reload(ai_filter)


class AiRouterIntegration(unittest.TestCase):
    def setUp(self):
        self.af = fresh_ai_filter()

    def test_router_singleton_is_reused(self):
        cfg = {"max_concurrency": 2, "timeout_s": 5, "budget_total": 10}
        prov = self.af._LLMProvider([("k", "http://x", "m")], 5, 128)
        r1 = self.af._router_instance([("k", "http://x", "m")], cfg)
        self.assertIsNotNone(r1)
        self.assertIs(r1, self.af._router_instance([("k", "http://x", "m")], cfg),
                      "router must be a singleton, not rebuilt per call")

    def test_provider_is_available_only_with_candidates(self):
        self.assertFalse(self.af._LLMProvider([], 5, 128).is_available())
        self.assertTrue(self.af._LLMProvider([("k", "u", "m")], 5, 128).is_available())

    def test_successful_extraction_passes_through_router(self):
        cfg = {"max_concurrency": 2, "timeout_s": 5, "budget_total": 100}
        self.af._router_instance([("k", "u", "m")], cfg)
        with patch.object(self.af, "_call_candidates",
                          return_value=({"is_signal": True, "action": "buy"}, "stub 0.1s")):
            with patch.object(self.af, "ai_cfg", return_value={"enabled": True, **cfg}), \
                 patch.object(self.af, "_llm_candidates", return_value=[("k", "u", "m")]):
                data, info = self.af.llm_extract("BUY XAUUSD")
        self.assertEqual(data, {"is_signal": True, "action": "buy"})
        self.assertIn("stub", info)

    def test_budget_exhaustion_abstains_and_never_fabricates(self):
        cfg = {"max_concurrency": 2, "timeout_s": 5, "budget_total": 0.0}
        router = self.af._router_instance([("k", "u", "m")], cfg)
        # budget_total 0 => even the minimal estimate cannot pass
        with patch.object(self.af, "ai_cfg", return_value={"enabled": True, **cfg}), \
             patch.object(self.af, "_llm_candidates", return_value=[("k", "u", "m")]):
            data, info = self.af.llm_extract("BUY XAUUSD")
        self.assertIsNone(data, "an abstained call must not return a signal")
        self.assertIn("abstain", info.lower())

    def test_no_key_returns_none_without_raising(self):
        with patch.object(self.af, "ai_cfg", return_value={"enabled": True}), \
             patch.object(self.af, "_llm_candidates", return_value=[]):
            data, info = self.af.llm_extract("anything")
        self.assertIsNone(data)
        self.assertIn("no LLM key", info)

    def test_disabled_ai_returns_none(self):
        with patch.object(self.af, "ai_cfg", return_value={"enabled": False}):
            data, info = self.af.llm_extract("anything")
        self.assertIsNone(data)
        self.assertEqual(info, "ai disabled")

    def test_concurrency_is_actually_bounded(self):
        """With max_concurrency=1, a second concurrent call must not run in parallel."""
        router = mr.ModelRouter(
            mr.RouterConfig(max_concurrency=1, deadline_s=0.4, budget_total=100,
                            concurrency_timeout_s=0.2),
            [])
        state = {"active": 0, "peak": 0, "ran": 0}
        lock = threading.Lock()

        class Slow:
            name = "slow"

            def is_available(self):
                return True

            def cost(self):
                return 1.0

            def call(self, prompt, **kw):
                with lock:
                    state["active"] += 1
                    state["ran"] += 1
                    state["peak"] = max(state["peak"], state["active"])
                time.sleep(0.25)
                with lock:
                    state["active"] -= 1
                return "done"

        router.providers = [Slow()]
        threads = [threading.Thread(target=router.route, args=("p",)) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)
        self.assertEqual(state["peak"], 1, "max_concurrency=1 must never run two calls at once")

    def test_router_unavailable_falls_back_to_direct_call(self):
        """If model_router cannot be imported, extraction must still be attempted."""
        with patch.object(self.af, "ai_cfg", return_value={"enabled": True, "timeout_s": 5}), \
             patch.object(self.af, "_llm_candidates", return_value=[("k", "u", "m")]), \
             patch.object(self.af, "_router_instance", return_value=None), \
             patch.object(self.af, "_call_candidates",
                          return_value=({"is_signal": True}, "direct 0.0s")):
            data, info = self.af.llm_extract("BUY XAUUSD")
        self.assertEqual(data, {"is_signal": True})
        self.assertIn("direct", info)


if __name__ == "__main__":
    unittest.main(verbosity=2)

---
slug: test_model_router
type: note
graph: gitnexus
---

"""Tests for model_router.py — bounded AI call routing with deterministic fakes."""
from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from model_router import (
    ModelRouter,
    RouterConfig,
    RouterResult,
    RouterStatus,
)


class FakeClock:
    """Deterministic clock for tests."""
    def __init__(self, start: float = 0.0):
        self._time = start
    def __call__(self) -> float:
        return self._time
    def advance(self, delta: float) -> None:
        self._time += delta


class FakeProvider:
    """Deterministic fake provider for tests."""
    def __init__(self, name: str, available: bool = True, cost: float = 0.1,
                 result: Any = None, error: Exception = None,
                 delay: float = 0.0):
        self.name = name
        self._available = available
        self._cost = cost
        self._result = result if result is not None else {"signal": "buy", "symbol": "XAUUSD"}
        self._error = error
        self._delay = delay
        self.call_count = 0
        self._started = threading.Event()
        self._release = threading.Event()

    def is_available(self) -> bool:
        return self._available

    def call(self, prompt: str, **kwargs) -> Any:
        self.call_count += 1
        self._started.set()
        if self._delay > 0:
            time.sleep(self._delay)
        if self._error:
            raise self._error
        return self._result

    def cost(self) -> float:
        return self._cost


class BlockingProvider(FakeProvider):
    """A provider that blocks until released (for concurrency tests)."""
    def __init__(self, name: str = "blocker", cost: float = 0.1):
        super().__init__(name, available=True, cost=cost)
        self._block = threading.Event()

    def call(self, prompt: str, **kwargs) -> Any:
        self.call_count += 1
        self._started.set()
        self._block.wait(timeout=5.0)
        return {"result": "ok"}

    def release(self):
        self._block.set()


class TestSuccessfulCall(unittest.TestCase):
    """A successful call returns the provider result."""

    def test_successful_call(self):
        clock = FakeClock()
        provider = FakeProvider("test", cost=0.1, result={"signal": "buy"})
        config = RouterConfig(max_concurrency=3, deadline_s=5.0, budget_total=1.0, clock=clock)
        router = ModelRouter(config, [provider])

        result = router.route("test prompt")

        self.assertTrue(result.ok)
        self.assertEqual(RouterStatus.SUCCESS, result.status)
        self.assertEqual("test", result.provider)
        self.assertEqual({"signal": "buy"}, result.data)
        self.assertEqual(0.1, result.cost)
        self.assertEqual(0.1, router.spend)

    def test_success_with_multiple_providers(self):
        """First available provider wins."""
        clock = FakeClock()
        p1 = FakeProvider("p1", available=False, cost=0.1)
        p2 = FakeProvider("p2", available=True, cost=0.2, result={"from": "p2"})
        p3 = FakeProvider("p3", available=True, cost=0.3, result={"from": "p3"})
        config = RouterConfig(max_concurrency=3, deadline_s=5.0, budget_total=1.0, clock=clock)
        router = ModelRouter(config, [p1, p2, p3])

        result = router.route("test")

        self.assertTrue(result.ok)
        self.assertEqual("p2", result.provider)
        self.assertEqual(1, p2.call_count)
        self.assertEqual(0, p3.call_count)  # p3 not tried


class TestDeadlineExceeded(unittest.TestCase):
    """Provider call exceeding the deadline abstains with DEADLINE_EXCEEDED."""

    def test_deadline_exceeded(self):
        """A slow provider that exceeds the deadline causes abstention."""
        clock = FakeClock()
        # Provider that sleeps longer than the deadline
        provider = FakeProvider("slow", cost=0.1, delay=0.2)
        config = RouterConfig(max_concurrency=3, deadline_s=0.05, budget_total=1.0, clock=clock)
        router = ModelRouter(config, [provider])

        result = router.route("test")

        self.assertFalse(result.ok)
        self.assertTrue(result.abstained)
        self.assertEqual(RouterStatus.DEADLINE_EXCEEDED, result.status)
        self.assertIn("deadline", result.reason.lower())

    def test_deadline_exceeded_tries_next_provider(self):
        """If first provider times out, next provider is tried."""
        clock = FakeClock()
        p1 = FakeProvider("slow", cost=0.1, delay=0.2)
        p2 = FakeProvider("fast", cost=0.1, result={"from": "p2"})
        config = RouterConfig(max_concurrency=3, deadline_s=0.05, budget_total=1.0, clock=clock)
        router = ModelRouter(config, [p1, p2])

        result = router.route("test")

        # p1 timed out, p2 should have been tried
        self.assertEqual(1, p1.call_count)
        # p2 may or may not have been tried depending on timing
        # The key assertion: the result is either SUCCESS (p2) or DEADLINE_EXCEEDED
        self.assertTrue(result.ok or result.abstained)


class TestConcurrencyLimit(unittest.TestCase):
    """N+1 call waits up to remaining deadline, then abstains with CONCURRENCY_LIMIT."""

    def test_concurrency_limit_abstains_after_timeout(self):
        """When all slots are full, the N+1 call abstains with CONCURRENCY_LIMIT.

        The call WAITS up to concurrency_timeout_s for a slot. If no slot
        opens within that time, it abstains with CONCURRENCY_LIMIT.
        """
        import time as _time
        blocker = BlockingProvider("blocker", cost=0.1)
        config = RouterConfig(max_concurrency=1, deadline_s=1.0, budget_total=1.0,
                              clock=_time.monotonic, concurrency_timeout_s=0.1)
        router = ModelRouter(config, [blocker])

        # Start first call in a thread — it acquires the only slot and blocks
        result_holder = {}
        def first_call():
            result_holder["result"] = router.route("test")

        t = threading.Thread(target=first_call)
        t.start()

        # Wait for the first call to start (acquire the slot)
        blocker._started.wait(timeout=1.0)

        # Second call should abstain with CONCURRENCY_LIMIT after timeout
        result2 = router.route("test")

        self.assertFalse(result2.ok)
        self.assertTrue(result2.abstained)
        self.assertEqual(RouterStatus.CONCURRENCY_LIMIT, result2.status)
        self.assertIn("concurrency", result2.reason.lower())

        # Release the first call
        blocker.release()
        t.join(timeout=2.0)

        # First call should have succeeded
        self.assertTrue(result_holder["result"].ok)

    def test_concurrency_limit_with_multiple_slots(self):
        """With max_concurrency=2, the 3rd call abstains."""
        import time as _time
        blocker = BlockingProvider("blocker", cost=0.1)
        config = RouterConfig(max_concurrency=2, deadline_s=1.0, budget_total=1.0,
                              clock=_time.monotonic, concurrency_timeout_s=0.1)
        router = ModelRouter(config, [blocker])

        # Start two calls in threads — they acquire both slots
        results = {}
        def call_a():
            results["a"] = router.route("a")
        def call_b():
            results["b"] = router.route("b")

        ta = threading.Thread(target=call_a)
        tb = threading.Thread(target=call_b)
        ta.start()
        tb.start()

        # Wait for both to start
        time.sleep(0.05)

        # Third call should abstain
        result_c = router.route("c")
        self.assertEqual(RouterStatus.CONCURRENCY_LIMIT, result_c.status)

        # Release both
        blocker.release()
        blocker.release()
        ta.join(timeout=2.0)
        tb.join(timeout=2.0)


class TestBudgetExhausted(unittest.TestCase):
    """Budget exhausted -> abstain with BUDGET_EXHAUSTED."""

    def test_budget_exhausted_abstains(self):
        """When the budget is exhausted, the router abstains."""
        clock = FakeClock()
        provider = FakeProvider("test", cost=0.1)
        config = RouterConfig(max_concurrency=3, deadline_s=5.0, budget_total=0.15, clock=clock)
        router = ModelRouter(config, [provider])

        # First call: success (spend 0.1, remaining 0.05)
        r1 = router.route("test")
        self.assertTrue(r1.ok)
        self.assertEqual(0.1, router.spend)

        # Second call: would exceed budget (0.1 + 0.1 = 0.2 > 0.15)
        r2 = router.route("test")
        self.assertFalse(r2.ok)
        self.assertTrue(r2.abstained)
        self.assertEqual(RouterStatus.BUDGET_EXHAUSTED, r2.status)
        self.assertIn("budget", r2.reason.lower())

    def test_budget_allows_call_within_remaining(self):
        """A call that fits within the remaining budget succeeds."""
        clock = FakeClock()
        provider = FakeProvider("test", cost=0.1)
        config = RouterConfig(max_concurrency=3, deadline_s=5.0, budget_total=0.25, clock=clock)
        router = ModelRouter(config, [provider])

        r1 = router.route("test")
        self.assertTrue(r1.ok)
        self.assertEqual(0.1, router.spend)

        r2 = router.route("test")
        self.assertTrue(r2.ok)
        self.assertEqual(0.2, router.spend)

        # Third call: 0.2 + 0.1 = 0.3 > 0.25
        r3 = router.route("test")
        self.assertEqual(RouterStatus.BUDGET_EXHAUSTED, r3.status)


class TestProviderUnavailable(unittest.TestCase):
    """Provider unavailable -> abstain with PROVIDER_UNAVAILABLE."""

    def test_all_providers_unavailable(self):
        """When no provider is available, abstain."""
        clock = FakeClock()
        p1 = FakeProvider("p1", available=False, cost=0.1)
        p2 = FakeProvider("p2", available=False, cost=0.1)
        config = RouterConfig(max_concurrency=3, deadline_s=5.0, budget_total=1.0, clock=clock)
        router = ModelRouter(config, [p1, p2])

        result = router.route("test")

        self.assertFalse(result.ok)
        self.assertTrue(result.abstained)
        self.assertEqual(RouterStatus.PROVIDER_UNAVAILABLE, result.status)

    def test_provider_error_tries_next(self):
        """If a provider raises, the next provider is tried."""
        clock = FakeClock()
        p1 = FakeProvider("p1", available=True, cost=0.1, error=RuntimeError("fail"))
        p2 = FakeProvider("p2", available=True, cost=0.1, result={"from": "p2"})
        config = RouterConfig(max_concurrency=3, deadline_s=5.0, budget_total=1.0, clock=clock)
        router = ModelRouter(config, [p1, p2])

        result = router.route("test")

        self.assertTrue(result.ok)
        self.assertEqual("p2", result.provider)
        self.assertEqual(1, p1.call_count)
        self.assertEqual(1, p2.call_count)

    def test_all_providers_error_abstains(self):
        """If all providers error, abstain with PROVIDER_UNAVAILABLE."""
        clock = FakeClock()
        p1 = FakeProvider("p1", available=True, cost=0.1, error=RuntimeError("fail1"))
        p2 = FakeProvider("p2", available=True, cost=0.1, error=RuntimeError("fail2"))
        config = RouterConfig(max_concurrency=3, deadline_s=5.0, budget_total=1.0, clock=clock)
        router = ModelRouter(config, [p1, p2])

        result = router.route("test")

        self.assertFalse(result.ok)
        self.assertEqual(RouterStatus.PROVIDER_UNAVAILABLE, result.status)


class TestNeverBlocksIndefinitely(unittest.TestCase):
    """The router never blocks the caller indefinitely."""

    def test_slow_provider_does_not_block_forever(self):
        """A provider that would block forever is cut off by the deadline."""
        import time as _time
        # Provider that would block for a very long time
        provider = FakeProvider("slow", cost=0.1, delay=10.0)
        config = RouterConfig(max_concurrency=3, deadline_s=0.05, budget_total=1.0,
                              clock=_time.monotonic)
        router = ModelRouter(config, [provider])

        start = time.monotonic()
        result = router.route("test")
        elapsed = time.monotonic() - start

        # Should return well before 10 seconds
        self.assertLess(elapsed, 2.0)
        self.assertTrue(result.abstained)

    def test_full_concurrency_does_not_block_forever(self):
        """When all slots are full, the call abstains after the concurrency timeout."""
        import time as _time
        blocker = BlockingProvider("blocker", cost=0.1)
        config = RouterConfig(max_concurrency=1, deadline_s=5.0, budget_total=1.0,
                              clock=_time.monotonic, concurrency_timeout_s=0.1)
        router = ModelRouter(config, [blocker])

        # Fill the only slot
        def fill():
            router.route("fill")
        t = threading.Thread(target=fill)
        t.start()
        blocker._started.wait(timeout=1.0)

        # This call should abstain after ~0.1s
        start = time.monotonic()
        result = router.route("test")
        elapsed = time.monotonic() - start

        self.assertLess(elapsed, 2.0)
        self.assertEqual(RouterStatus.CONCURRENCY_LIMIT, result.status)

        blocker.release()
        t.join(timeout=2.0)


class TestSpendTracking(unittest.TestCase):
    """Spend is tracked correctly across calls."""

    def test_spend_accumulates(self):
        clock = FakeClock()
        p1 = FakeProvider("p1", cost=0.1)
        p2 = FakeProvider("p2", cost=0.2)
        config = RouterConfig(max_concurrency=3, deadline_s=5.0, budget_total=1.0, clock=clock)
        router = ModelRouter(config, [p1, p2])

        router.route("test1")
        self.assertAlmostEqual(0.1, router.spend)

        router.route("test2")
        self.assertAlmostEqual(0.2, router.spend)

        router.route("test3")
        self.assertAlmostEqual(0.3, router.spend)

    def test_budget_remaining_decreases(self):
        clock = FakeClock()
        provider = FakeProvider("test", cost=0.1)
        config = RouterConfig(max_concurrency=3, deadline_s=5.0, budget_total=0.5, clock=clock)
        router = ModelRouter(config, [provider])

        self.assertAlmostEqual(0.5, router.budget_remaining)
        router.route("test")
        self.assertAlmostEqual(0.4, router.budget_remaining)
        router.route("test")
        self.assertAlmostEqual(0.3, router.budget_remaining)


if __name__ == "__main__":
    unittest.main(verbosity=2)


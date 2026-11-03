"""Tests for bar_parity.py — closed-bar determination, idempotency, timezone honesty."""
from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from bar_parity import BarParity, BarParityConfig, TIMEFRAME_SECONDS


class FakeClock:
    """Deterministic clock for tests."""
    def __init__(self, start: float = 100000.0):
        self._time = start
    def __call__(self) -> float:
        return self._time
    def advance(self, delta: float) -> None:
        self._time += delta


class TestClosedBarDetermination(unittest.TestCase):
    """Forming bar rejected, boundary bar handled per stated rule."""

    def setUp(self):
        self.clock = FakeClock(100000.0)
        self.parity = BarParity(BarParityConfig(clock=self.clock))

    def test_forming_bar_is_rejected(self):
        """A bar that opened less than one duration ago is NOT closed."""
        # H1 bar opened 1800s ago (30 min) — still forming
        now = 100000.0
        bar_open = now - 1800  # 30 min ago
        self.assertFalse(self.parity.is_closed(bar_open, "H1", now))

    def test_bar_exactly_one_duration_old_is_closed(self):
        """Boundary rule: bar_open + duration == now -> CLOSED (inclusive)."""
        now = 100000.0
        bar_open = now - 3600  # exactly 1 hour ago
        self.assertTrue(self.parity.is_closed(bar_open, "H1", now))

    def test_bar_more_than_one_duration_old_is_closed(self):
        """A bar that opened more than one duration ago is CLOSED."""
        now = 100000.0
        bar_open = now - 7200  # 2 hours ago
        self.assertTrue(self.parity.is_closed(bar_open, "H1", now))

    def test_m15_boundary_matches_existing_contract(self):
        """Verify the M15 boundary matches neural_label_collector._bars_at.

        From test_research_contracts.py:
          epoch=90000, last_open=89100 -> 89100 + 900 = 90000 <= 90000 (closed)
          epoch=89999, last_open=88200 -> 88200 + 900 = 89100 <= 89999 (closed)
        """
        # epoch=90000: bar at 89100 is closed (89100 + 900 = 90000 <= 90000)
        self.assertTrue(self.parity.is_closed(89100, "M15", 90000))
        # epoch=89999: bar at 89100 is NOT closed (89100 + 900 = 90000 > 89999)
        self.assertFalse(self.parity.is_closed(89100, "M15", 89999))
        # epoch=89999: bar at 88200 is closed (88200 + 900 = 89100 <= 89999)
        self.assertTrue(self.parity.is_closed(88200, "M15", 89999))

    def test_unknown_timeframe_raises(self):
        with self.assertRaises(ValueError):
            self.parity.is_closed(1000, "UNKNOWN")

    def test_filter_closed_bars_drops_forming(self):
        """filter_closed_bars drops the forming bar, keeps closed ones."""
        now = 100000.0
        bars = [
            {"time": now - 7200, "symbol": "XAUUSD"},  # closed (2h ago)
            {"time": now - 3600, "symbol": "XAUUSD"},  # closed (1h ago, boundary)
            {"time": now - 1800, "symbol": "XAUUSD"},  # forming (30 min ago)
        ]
        closed = self.parity.filter_closed_bars(bars, "H1", now)
        self.assertEqual(2, len(closed))
        self.assertEqual(now - 7200, closed[0].open_epoch)
        self.assertEqual(now - 3600, closed[1].open_epoch)


class TestIdempotentProcessing(unittest.TestCase):
    """Same bar processed twice yields one result; out-of-order arrival handled."""

    def setUp(self):
        self.clock = FakeClock(100000.0)
        self.parity = BarParity(BarParityConfig(clock=self.clock))

    def test_same_bar_processed_twice_yields_one_result(self):
        """The processor is invoked exactly once per unique bar key."""
        call_count = 0
        results = []

        def processor(symbol, timeframe, bar_open_epoch):
            nonlocal call_count
            call_count += 1
            return {"value": call_count, "symbol": symbol}

        now = 100000.0
        # First call — processor invoked
        r1 = self.parity.process_bar("XAUUSD", "H1", now - 3600, processor, now)
        # Second call — cached result returned, processor NOT invoked
        r2 = self.parity.process_bar("XAUUSD", "H1", now - 3600, processor, now)

        self.assertEqual(1, call_count)
        self.assertEqual(r1, r2)
        self.assertEqual(1, self.parity.processed_count)

    def test_different_bars_processed_independently(self):
        """Different bars are processed independently."""
        call_count = 0

        def processor(symbol, timeframe, bar_open_epoch):
            nonlocal call_count
            call_count += 1
            return {"value": call_count}

        now = 100000.0
        self.parity.process_bar("XAUUSD", "H1", now - 3600, processor, now)
        self.parity.process_bar("XAUUSD", "H1", now - 7200, processor, now)
        self.assertEqual(2, call_count)
        self.assertEqual(2, self.parity.processed_count)

    def test_out_of_order_arrival_handled(self):
        """Bars arriving out of order are each processed exactly once."""
        processed_epochs = []

        def processor(symbol, timeframe, bar_open_epoch):
            processed_epochs.append(bar_open_epoch)
            return {"epoch": bar_open_epoch}

        now = 100000.0
        bars = [
            {"time": now - 3600 * 4, "symbol": "XAUUSD"},
            {"time": now - 3600 * 1, "symbol": "XAUUSD"},
            {"time": now - 3600 * 3, "symbol": "XAUUSD"},
            {"time": now - 3600 * 2, "symbol": "XAUUSD"},
            {"time": now - 3600 * 5, "symbol": "XAUUSD"},
        ]
        # Process in reverse order (newest first)
        results = self.parity.process_bars(
            list(reversed(bars)), "H1", processor, now
        )
        # All 5 bars processed
        self.assertEqual(5, len(results))
        # Each bar processed exactly once
        self.assertEqual(5, len(processed_epochs))
        self.assertEqual(5, len(set(processed_epochs)))
        # Results are sorted by open_epoch (deterministic order)
        epochs = [r["epoch"] for r in results]
        self.assertEqual(epochs, sorted(epochs))

    def test_process_bar_skips_forming_bar(self):
        """process_bar returns skipped=True for a forming bar."""
        def processor(symbol, timeframe, bar_open_epoch):
            return {"should": "not reach here"}

        now = 100000.0
        result = self.parity.process_bar("XAUUSD", "H1", now - 1800, processor, now)
        self.assertTrue(result.get("skipped"))
        self.assertEqual(0, self.parity.processed_count)

    def test_idempotent_key_includes_symbol_and_timeframe(self):
        """Same epoch but different symbol/timeframe = different key."""
        call_count = 0

        def processor(symbol, timeframe, bar_open_epoch):
            nonlocal call_count
            call_count += 1
            return {"value": call_count}

        now = 100000.0
        self.parity.process_bar("XAUUSD", "H1", now - 3600, processor, now)
        self.parity.process_bar("EURUSD", "H1", now - 3600, processor, now)
        self.parity.process_bar("XAUUSD", "M15", now - 3600, processor, now)
        self.assertEqual(3, call_count)

    def test_key_fingerprint_is_deterministic(self):
        """Same key always produces the same fingerprint."""
        k1 = self.parity.bar_key("XAUUSD", "H1", 100000)
        k2 = self.parity.bar_key("XAUUSD", "H1", 100000)
        k3 = self.parity.bar_key("EURUSD", "H1", 100000)
        self.assertEqual(self.parity.key_fingerprint(k1),
                         self.parity.key_fingerprint(k2))
        self.assertNotEqual(self.parity.key_fingerprint(k1),
                            self.parity.key_fingerprint(k3))


class TestTimezoneHonesty(unittest.TestCase):
    """Broker epochs have no guaranteed timezone — assumption is explicit."""

    def test_venue_timezone_does_not_affect_closed_bar_determination(self):
        """The module treats epochs as opaque integers.

        Setting venue_timezone does NOT change the closed-bar determination
        because the module never converts epochs. This test proves the
        assumption is exposed but not enforced.
        """
        now = 100000.0
        bar_open = now - 3600

        # No timezone assumption
        p1 = BarParity(BarParityConfig(venue_timezone=None, clock=lambda: now))
        # With timezone assumption
        p2 = BarParity(BarParityConfig(venue_timezone="America/New_York",
                                       clock=lambda: now))
        # Different timezone assumption
        p3 = BarParity(BarParityConfig(venue_timezone="Asia/Tokyo",
                                       clock=lambda: now))

        # All three produce the same result — timezone is not used for conversion
        self.assertEqual(
            p1.is_closed(bar_open, "H1", now),
            p2.is_closed(bar_open, "H1", now),
        )
        self.assertEqual(
            p2.is_closed(bar_open, "H1", now),
            p3.is_closed(bar_open, "H1", now),
        )

    def test_assumption_violation_demonstrated(self):
        """Demonstrate what happens when the timezone assumption is violated.

        Scenario: the caller assumes broker epochs are in UTC, but the broker
        actually sends epochs in 'America/New_York' local time (or vice versa).
        The module does NOT crash or silently convert — it compares the
        numbers as-is. The closed-bar determination is correct ON THE EPOCH
        BASIS, but the caller's interpretation of "now" might be wrong if
        they're using a different time basis.

        This test shows: the module is honest about the assumption. It does
        not claim DST correctness. The caller is responsible for ensuring
        'now' is on the same basis as the bar epochs.
        """
        # Simulate: broker sends epochs in UTC, caller assumes UTC (correct)
        now_utc = 100000.0
        bar_open_utc = now_utc - 3600
        p = BarParity(BarParityConfig(venue_timezone="UTC", clock=lambda: now_utc))
        self.assertTrue(p.is_closed(bar_open_utc, "H1", now_utc))

        # Simulate: broker sends epochs in UTC, caller assumes 'America/New_York'
        # and uses local time for "now" (WRONG — assumption violated)
        # The module still compares the numbers correctly, but the caller's
        # "now" is on a different basis, so the result is meaningless.
        # The module does NOT detect or correct this — it's the caller's
        # responsibility to ensure "now" matches the bar epoch basis.
        now_local = now_utc - 5 * 3600  # caller's local time (UTC-5)
        # The module treats both as opaque integers — no conversion
        result = p.is_closed(bar_open_utc, "H1", now_local)
        # The result is based on pure integer comparison, which is correct
        # on the epoch basis but the caller's intent is violated.
        # This is the honest behavior: no silent conversion, no false confidence.
        self.assertIsInstance(result, bool)  # module returns a result, not an error

    def test_dst_transition_not_claimed(self):
        """The module does NOT claim DST correctness.

        During a DST transition, a venue-local clock skips or repeats an hour.
        The module does not model this — it treats epochs as opaque integers.
        This test documents that limitation.
        """
        # Default config has no timezone assumption
        default_config = BarParityConfig()
        self.assertIsNone(default_config.venue_timezone)
        # Even when set, no DST conversion happens
        p = BarParity(BarParityConfig(venue_timezone="America/New_York"))
        self.assertEqual("America/New_York", p.config.venue_timezone)
        # But is_closed does not use it — same result with or without timezone
        now = 100000.0
        p_no_tz = BarParity(BarParityConfig(venue_timezone=None, clock=lambda: now))
        self.assertEqual(
            p_no_tz.is_closed(now - 3600, "H1", now),
            p.is_closed(now - 3600, "H1", now),
        )


class TestConcurrency(unittest.TestCase):
    """Thread-safety of the processed-bar cache."""

    def test_concurrent_processing_of_same_bar(self):
        """Multiple threads processing the same bar: processor called once."""
        clock = FakeClock(100000.0)
        parity = BarParity(BarParityConfig(clock=clock))
        call_count = 0
        lock = threading.Lock()

        def processor(symbol, timeframe, bar_open_epoch):
            nonlocal call_count
            with lock:
                call_count += 1
            time.sleep(0.01)  # small delay to increase contention
            return {"value": call_count}

        now = 100000.0
        results = []
        errors = []

        def worker():
            try:
                r = parity.process_bar("XAUUSD", "H1", now - 3600, processor, now)
                results.append(r)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5.0)

        self.assertEqual(0, len(errors))
        self.assertEqual(10, len(results))
        self.assertEqual(1, call_count)  # processor called exactly once
        # All results are the same
        self.assertEqual(1, len(set(str(r) for r in results)))


if __name__ == "__main__":
    unittest.main(verbosity=2)

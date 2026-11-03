"""bar_parity.py — closed-bar determination and idempotent bar processing.

Broker-supplied bar epochs have NO guaranteed timezone. This module treats
them as opaque integers on a single basis and never silently converts to UTC.
The caller must supply a 'now' on the same basis as the bar epochs.

DST/venue-timezone correctness is NOT claimed. The venue_timezone parameter
is exposed as an explicit assumption for callers who need timezone-aware
operations, but no DST transition logic is applied.

Closed-bar rule: a bar is CLOSED when bar_open_epoch + timeframe_duration <= now.
The boundary (bar_open + duration == now) is INCLUSIVE — the bar is closed.

Idempotency: each unique (symbol, timeframe, bar_open_epoch) is processed
at most once. The first processing wins; subsequent attempts return the
cached result.
"""
from __future__ import annotations

import hashlib
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

# Timeframe durations in seconds (MT5 standard)
TIMEFRAME_SECONDS: Dict[str, int] = {
    "M1": 60, "M5": 300, "M15": 900, "M30": 1800,
    "H1": 3600, "H4": 14400, "D1": 86400, "W1": 604800, "MN1": 2592000,
}


@dataclass(frozen=True)
class BarKey:
    """Idempotent key for a closed bar: (symbol, timeframe, bar_open_epoch)."""
    symbol: str
    timeframe: str
    bar_open_epoch: int


@dataclass
class ClosedBar:
    """A verified closed bar with its key and metadata."""
    key: BarKey
    open_epoch: int
    close_epoch: int  # open_epoch + duration
    is_closed: bool   # always True for instances returned by filter_closed_bars


@dataclass
class BarParityConfig:
    """Configuration for bar parity operations.

    venue_timezone: IANA timezone name (e.g. 'America/New_York') for the
        trading venue. This is an EXPLICIT ASSUMPTION — broker epochs are
        not guaranteed to be in this timezone, and no DST transition logic
        is applied. When None, epochs are treated as opaque integers.
        The module NEVER converts epochs using this value; it is purely
        documentary / for callers who need to interpret results.
    clock: callable returning current time (epoch seconds). Defaults to time.time.
    """
    venue_timezone: Optional[str] = None
    clock: Callable[[], float] = time.time


class BarParity:
    """Closed-bar determination and idempotent processing.

    A bar is CLOSED when: bar_open_epoch + timeframe_duration <= now
    The boundary (exactly one duration old) is INCLUSIVE.

    Idempotency: each unique (symbol, timeframe, bar_open_epoch) is processed
    at most once. The first processing wins; subsequent attempts return the
    cached result.

    Thread-safe: the processed-bar cache is guarded by a lock.
    """

    def __init__(self, config: Optional[BarParityConfig] = None):
        self.config = config or BarParityConfig()
        self._processed: Dict[BarKey, Any] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Closed-bar determination
    # ------------------------------------------------------------------
    def is_closed(self, bar_open_epoch: int, timeframe: str,
                  now: Optional[float] = None) -> bool:
        """Check if a bar is closed (not forming).

        A bar is closed when bar_open_epoch + duration <= now.
        The boundary (exactly one duration old) is INCLUSIVE.
        """
        duration = TIMEFRAME_SECONDS.get(timeframe)
        if duration is None:
            raise ValueError(f"Unknown timeframe: {timeframe}")
        if now is None:
            now = self.config.clock()
        return bar_open_epoch + duration <= now

    def filter_closed_bars(self, bars: List[dict], timeframe: str,
                           now: Optional[float] = None) -> List[ClosedBar]:
        """Filter a list of bars to only closed ones.

        Bars are dicts with at least a 'time' key (bar open epoch).
        Returns list of ClosedBar instances sorted by open_epoch.
        """
        duration = TIMEFRAME_SECONDS.get(timeframe)
        if duration is None:
            raise ValueError(f"Unknown timeframe: {timeframe}")
        if now is None:
            now = self.config.clock()
        result: List[ClosedBar] = []
        for bar in bars:
            open_epoch = int(bar["time"])
            if self.is_closed(open_epoch, timeframe, now):
                key = BarKey(
                    symbol=bar.get("symbol", ""),
                    timeframe=timeframe,
                    bar_open_epoch=open_epoch,
                )
                result.append(ClosedBar(
                    key=key,
                    open_epoch=open_epoch,
                    close_epoch=open_epoch + duration,
                    is_closed=True,
                ))
        result.sort(key=lambda b: b.open_epoch)
        return result

    # ------------------------------------------------------------------
    # Idempotent processing
    # ------------------------------------------------------------------
    def process_bar(self, symbol: str, timeframe: str, bar_open_epoch: int,
                    processor: Callable[[str, str, int], Any],
                    now: Optional[float] = None) -> Any:
        """Process a closed bar exactly once.

        Idempotent by (symbol, timeframe, bar_open_epoch). The first call
        for a given key invokes the processor and caches the result.
        Subsequent calls return the cached result without re-invoking.

        Returns the processor result, or a dict with 'skipped': True if
        the bar is not yet closed.
        """
        if not self.is_closed(bar_open_epoch, timeframe, now):
            return {"skipped": True, "reason": "bar not closed"}

        key = BarKey(symbol=symbol, timeframe=timeframe,
                     bar_open_epoch=bar_open_epoch)

        with self._lock:
            if key in self._processed:
                return self._processed[key]
            result = processor(symbol, timeframe, bar_open_epoch)
            self._processed[key] = result
            return result

    def process_bars(self, bars: List[dict], timeframe: str,
                     processor: Callable[[str, str, int], Any],
                     now: Optional[float] = None) -> List[Any]:
        """Process multiple bars, each exactly once.

        Handles out-of-order arrival: bars are sorted by open_epoch before
        processing, but idempotency is by key so order doesn't affect
        correctness.
        """
        closed = self.filter_closed_bars(bars, timeframe, now)
        results: List[Any] = []
        for bar in closed:
            result = self.process_bar(
                bar.key.symbol, bar.key.timeframe, bar.key.bar_open_epoch,
                processor, now,
            )
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Key utilities
    # ------------------------------------------------------------------
    def bar_key(self, symbol: str, timeframe: str, bar_open_epoch: int) -> BarKey:
        """Build an idempotent key for a bar."""
        return BarKey(symbol=symbol, timeframe=timeframe,
                      bar_open_epoch=bar_open_epoch)

    def key_fingerprint(self, key: BarKey) -> str:
        """Deterministic fingerprint for a bar key (for logging/dedup)."""
        raw = f"{key.symbol}|{key.timeframe}|{key.bar_open_epoch}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------
    @property
    def processed_count(self) -> int:
        """Number of unique bars processed so far."""
        return len(self._processed)

    def is_processed(self, symbol: str, timeframe: str, bar_open_epoch: int) -> bool:
        """Check if a bar has already been processed."""
        key = BarKey(symbol=symbol, timeframe=timeframe,
                     bar_open_epoch=bar_open_epoch)
        return key in self._processed

    def clear(self) -> None:
        """Clear all processed bar records. For testing."""
        with self._lock:
            self._processed.clear()

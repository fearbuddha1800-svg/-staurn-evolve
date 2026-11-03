"""EMA Cross strategy — Python transposition of strategies/ema_cross.pine.

Semantics:  Fast EMA(9) crosses above Slow EMA(21) → LONG entry.
            Fast EMA(9) crosses below Slow EMA(21) → SHORT entry.
No order-send. Offline condition evaluation only.
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

# Compatibility surface — MT5 access provided by caller at runtime.
# Do NOT import MT5, read credentials, or connect at module level;
# the sandbox prevents it. The caller (executor/manager) injects mt5.
mt5 = None  # type: ignore[assignment]

# Price validator helper
def _prices(values):
    """Convert a price series to a list of floats, validating finiteness."""
    result = []
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError("prices must be finite numbers")
        try:
            number = float(v)
        except (OverflowError, ValueError) as exc:
            raise ValueError("prices must be finite numbers") from exc
        if not math.isfinite(number):
            raise ValueError("prices must be finite numbers")
        result.append(number)
    return result


def ema(values, period):
    """Bar-aligned EMA. Returns list of same length as input; first
    (period-1) values are computed from available data (Pine-style SMA warmup)."""
    period = int(period)
    if period < 1:
        raise ValueError("period must be positive")
    values = _prices(values)
    if len(values) < period:
        # Pine-style: fill with NaN-equivalent until warmup complete
        out = [None] * len(values)
        # Simple SMA of first available values as seed
        sma = sum(values) / len(values) if values else 0
        for i in range(len(values)):
            out[i] = sma  # placeholder; real warmup uses cumulative average
        return out
    # Standard EMA: first value = SMA of first 'period' values
    alpha = 1.0 / period
    sma = sum(values[:period]) / period
    out = [None] * (period - 1) + [sma]
    for i in range(period, len(values)):
        out.append(alpha * values[i] + (1 - alpha) * out[i - 1])
    return out


def crossover(fast, slow):
    """True only when fast crosses above slow on the latest bar."""
    if fast is None or slow is None:
        return False
    if len(fast) != len(slow):
        raise ValueError("crossing series must have equal lengths")
    if len(fast) < 2:
        return False
    previous_fast, current_fast = fast[-2], fast[-1]
    previous_slow, current_slow = slow[-2], slow[-1]
    if any(v is None for v in [previous_fast, current_fast, previous_slow, current_slow]):
        return False
    return current_fast > current_slow and previous_fast <= previous_slow


def crossunder(fast, slow):
    """True only when fast crosses below slow on the latest bar."""
    if fast is None or slow is None:
        return False
    if len(fast) != len(slow):
        raise ValueError("crossing series must have equal lengths")
    if len(fast) < 2:
        return False
    previous_fast, current_fast = fast[-2], fast[-1]
    previous_slow, current_slow = slow[-2], slow[-1]
    if any(v is None for v in [previous_fast, current_fast, previous_slow, current_slow]):
        return False
    return current_fast < current_slow and previous_fast >= previous_slow


def evaluate(close_prices, fast_len=9, slow_len=21):
    """Evaluate EMA cross conditions for the latest bar.

    Returns dict with signal, entry flags, and EMA values.
    """
    closes = _prices(close_prices)
    fast = ema(closes, fast_len)
    slow = ema(closes, slow_len)
    long_entry = crossover(fast, slow)
    short_entry = crossunder(fast, slow)
    return {
        "signal": "LONG" if long_entry else ("SHORT" if short_entry else None),
        "long_entry": long_entry,
        "short_entry": short_entry,
        "fast_ema": fast[-1] if fast else None,
        "slow_ema": slow[-1] if slow else None,
    }
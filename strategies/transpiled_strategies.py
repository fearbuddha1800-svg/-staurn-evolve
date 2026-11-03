"""Offline Pine adapters; no bridge invocation or live execution.

Semantics target the installed SMA-seeded PineTS runtime, not independently
verified TradingView parity. Missing OHLC never fabricates ATR/SL/TP.
"""
from __future__ import annotations

import math
from pine_transpiled import atr as _atr, ema as _ema, rsi as _rsi


def _period(value):
    if type(value) is not int or value < 1:
        raise ValueError('indicator periods must be positive integers')
    return value


def _prices(values):
    result = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError('prices must be finite numbers')
        try:
            number = float(value)
        except (OverflowError, ValueError) as exc:
            raise ValueError('prices must be finite numbers') from exc
        if not math.isfinite(number):
            raise ValueError('prices must be finite numbers')
        result.append(number)
    return result


def ema(values, period):
    """Bar-aligned EMA; None during the installed-PineTS SMA warmup."""
    return _ema(_prices(values), _period(period))


def _latest_cross(fast, slow, up):
    if fast is None or slow is None:
        return False
    if len(fast) != len(slow):
        raise ValueError('crossing series must have equal lengths')
    if len(fast) < 2:
        return False
    values = (fast[-2], fast[-1], slow[-2], slow[-1])
    if any(value is None for value in values):
        return False
    previous_fast, current_fast, previous_slow, current_slow = _prices(values)
    if up:
        return current_fast > current_slow and previous_fast <= previous_slow
    return current_fast < current_slow and previous_fast >= previous_slow


def crossover(fast, slow):
    """True only when fast crosses above slow on the latest bar."""
    return _latest_cross(fast, slow, True)


def crossunder(fast, slow):
    """True only when fast crosses below slow on the latest bar."""
    return _latest_cross(fast, slow, False)


def ema_cross_strategy(close_prices, fast_len=9, slow_len=21):
    """Latest-bar EMA crossing conditions; does not send orders."""
    closes = _prices(close_prices)
    fast, slow = _ema(closes, _period(fast_len)), _ema(closes, _period(slow_len))
    long_entry, short_entry = crossover(fast, slow), crossunder(fast, slow)
    return {'signal': 'LONG' if long_entry else ('SHORT' if short_entry else None),
            'long_entry': long_entry, 'short_entry': short_entry,
            'fast_ema': fast, 'slow_ema': slow}


def rsi(series, period):
    """Latest Wilder RSI; None until period changes have been observed."""
    values = _rsi(_prices(series), _period(period))
    return values[-1] if values else None


def rsi_ema_trend_strategy(close_prices, rsi_len=14, ema_len=50, atr_len=14,
                           *, high_prices=None, low_prices=None):
    """Aligned RSI crossings and trend conditions from rsi_ema_trend.pine.

    Close-only mode reports conditions with unknown ATR/SL/TP. Both highs and
    lows enable source-Pine 2xATR stop and 3xATR limit calculations for offline
    replay. This is not a live execution policy or a live-readiness claim.
    """
    closes = _prices(close_prices)
    rsi_len, ema_len, atr_len = map(_period, (rsi_len, ema_len, atr_len))
    em, rs = _ema(closes, ema_len), _rsi(closes, rsi_len)
    has_ohlc = high_prices is not None or low_prices is not None
    if has_ohlc:
        if high_prices is None or low_prices is None:
            raise ValueError('supply both high_prices and low_prices')
        highs, lows = _prices(high_prices), _prices(low_prices)
        if len(highs) != len(closes) or len(lows) != len(closes):
            raise ValueError('OHLC series must have equal lengths')
        if any(not low <= close <= high for close, high, low in zip(closes, highs, lows)):
            raise ValueError('OHLC ranges must contain each close')
        at = _atr([dict(close=c, high=h, low=l) for c, h, l in zip(closes, highs, lows)], atr_len)
    else:
        at = [None] * len(closes)
    signals = []
    for i, close in enumerate(closes):
        current = rs[max(0, i - 1):i + 1]
        ready = em[i] is not None and (not has_ohlc or at[i] is not None)
        long_entry = bool(ready and close > em[i] and crossover(current, [35.0] * len(current)))
        short_entry = bool(ready and close < em[i] and crossunder(current, [65.0] * len(current)))
        sl = tp = None
        if at[i] is not None:
            if long_entry:
                sl, tp = close - at[i] * 2, close + at[i] * 3
            elif short_entry:
                sl, tp = close + at[i] * 2, close - at[i] * 3
        signals.append(dict(close=close, ema=em[i], rsi=rs[i], atr=at[i],
                            long_entry=long_entry, short_entry=short_entry, sl=sl, tp=tp))
    return {'signals': signals, 'ema_values': em, 'rsi_values': rs, 'atr_values': at,
            'mode': 'offline_ohlc' if has_ohlc else 'signal_only'}
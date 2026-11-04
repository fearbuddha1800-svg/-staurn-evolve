"""Synthetic closed-bar oracle evaluator; never executes a trading runtime."""
from __future__ import annotations

from typing import Any


def evaluate(case: dict[str, Any]) -> list[dict[str, Any]]:
    """Evaluate the candidate SMA(2) contract on trusted fixture bars."""
    duration = case["duration"]
    window: list[float] = []
    previous: tuple[float, float] | None = None
    prior_bar: dict[str, Any] | None = None
    records = []
    for bar in sorted(case["bars"], key=lambda item: item["open"]):
        decision = bar["open"] + duration
        if decision > case["asof"]:
            continue
        if prior_bar is not None and (
            bar["open"] != prior_bar["open"] + duration
            or bar["session"] != prior_bar["session"]
        ):
            window, previous = [], None
        close = bar["close"]
        average = None
        signal = "HOLD"
        if close is None:
            window, previous = [], None
        else:
            window.append(close)
            window = window[-2:]
            if len(window) == 2:
                average = sum(window) / 2
                if previous is not None:
                    old_close, old_average = previous
                    if old_close <= old_average and close > average:
                        signal = "BUY"
                    elif old_close >= old_average and close < average:
                        signal = "SELL"
                previous = close, average
        confirmed = [item for item in case["htf"]
                     if item["open"] + case["htf_duration"] <= decision]
        latest = max(confirmed, key=lambda item: item["open"], default=None)
        records.append({"open": bar["open"], "sma": average, "signal": signal,
                        "htf_close": latest["close"] if latest else None})
        prior_bar = bar
    return records

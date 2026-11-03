---
slug: portfolio_selector
type: note
graph: gitnexus
---

"""Offline-only selector: no external dependencies, no ML training."""

from __future__ import annotations


class StrategySelector:
    """Select a symbol and position size from a list of strategy dicts using simple rules.

    This module is *offline-only*: it never imports from external packages and
    performs no machine‑learning training.  Selection is rule‑based on the
    ``confidence`` field of each strategy dict.
    """

    def select(self, strategies: list[dict]) -> tuple[str | None, float]:
        """Pick the best strategy and return its symbol and position size.

        Args:
            strategies: A list of dictionaries, each expected to contain
                ``symbol`` (str), ``confidence`` (float in [0,1]), and optionally
                ``features`` (any).  Dicts missing required keys are skipped.

        Returns:
            A ``(symbol, position_size)`` tuple.  If no strategy meets the
            minimum confidence threshold ``0.5`` the symbol is ``None`` and
            position_size is ``0.0``.
        """
        best: dict | None = None
        best_conf = 0.0

        for stg in strategies:
            try:
                conf = float(stg["confidence"])
            except (KeyError, TypeError, ValueError):
                continue
            if conf > best_conf:
                best_conf = conf
                best = stg

        if best is None or best_conf < 0.5:
            return None, 0.0

        symbol = best.get("symbol")
        position_size = round(best_conf * 10, 2)
        return symbol, position_size


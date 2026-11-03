"""Strategy identity registry: stable unique IDs + versions for every strategy,
tied to broker magic numbers. Loaded from config.json strategy_identities.

Backward compatible: legacy magic 20261014 (signal relay), 20261015 (algo),
0 (manual/other) are explicitly registered and keep working exactly as before.

Usage:
    from strategy_identity import resolve_magic, attribution_report, filter_attribution

    identity = resolve_magic(20261014)
    # StrategyIdentity(id='signal-relay', version='1.0.0', kind='signal', ...)

    report = attribution_report(deals)  # deals from mt5.history_deals_get()
    filtered = filter_attribution(deals, strategy_id='algo-engine')
    filtered = filter_attribution(deals, version='1.0.0')
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Iterable, Optional

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.json")

# Legacy magic numbers — kept as constants for backward compatibility
MAGIC_SIGNAL_RELAY = 20261014
MAGIC_ALGO_ENGINE = 20261015
MAGIC_MANUAL = 0


@dataclass(frozen=True)
class StrategyIdentity:
    """Immutable strategy identity: stable id + version + kind + human label."""
    id: str
    version: str
    kind: str
    label: str
    magic: int
    note: str = ""


# Explicit unknown identity — never guesses
UNKNOWN_IDENTITY = StrategyIdentity(
    id="unknown",
    version="0.0.0",
    kind="unknown",
    label="Unknown",
    magic=-1,
    note="Unrecognized magic number — not registered in strategy_identities",
)


def load_registry(config_path: Optional[str] = None) -> dict[int, StrategyIdentity]:
    """Load magic -> StrategyIdentity from config.json strategy_identities block.

    Returns a dict mapping magic numbers to their identities.
    Unknown/unregistered magics are NOT in the map — resolve_magic handles them.
    """
    path = config_path or CONFIG
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError):
        return {}

    block = cfg.get("strategy_identities")
    if not isinstance(block, dict):
        return {}

    registry: dict[int, StrategyIdentity] = {}
    for sid, rec in block.items():
        if not isinstance(rec, dict):
            continue
        magic = rec.get("magic")
        if magic is None:
            continue
        try:
            magic = int(magic)
        except (TypeError, ValueError):
            continue
        identity = StrategyIdentity(
            id=str(rec.get("id") or sid),
            version=str(rec.get("version") or "0.0.0"),
            kind=str(rec.get("kind") or "unknown"),
            label=str(rec.get("label") or sid),
            magic=magic,
            note=str(rec.get("note") or ""),
        )
        registry[magic] = identity
    return registry


def resolve_magic(
    magic: int, registry: Optional[dict[int, StrategyIdentity]] = None
) -> StrategyIdentity:
    """Resolve a magic number to its StrategyIdentity.

    Known magic -> registered identity.
    Unknown magic -> UNKNOWN_IDENTITY (id='unknown', kind='unknown').
    Never guesses or falls back to a default strategy.
    """
    if registry is None:
        registry = load_registry()
    try:
        magic_int = int(magic)
    except (TypeError, ValueError):
        return UNKNOWN_IDENTITY
    return registry.get(magic_int, UNKNOWN_IDENTITY)


def resolve_all_magics(
    registry: Optional[dict[int, StrategyIdentity]] = None,
) -> dict[int, StrategyIdentity]:
    """Return the full magic -> identity map from config."""
    if registry is None:
        registry = load_registry()
    return dict(registry)


def _deal_pl(deal: Any) -> float:
    """Extract P&L from a deal dict or object (profit + commission + swap + fee)."""
    if isinstance(deal, dict):
        profit = float(deal.get("profit") or 0)
        commission = float(deal.get("commission") or 0)
        swap = float(deal.get("swap") or 0)
        fee = float(deal.get("fee") or 0)
    else:
        profit = float(getattr(deal, "profit", 0) or 0)
        commission = float(getattr(deal, "commission", 0) or 0)
        swap = float(getattr(deal, "swap", 0) or 0)
        fee = float(getattr(deal, "fee", 0) or 0)
    return profit + commission + swap + fee


def _deal_magic(deal: Any) -> int:
    """Extract magic from a deal dict or object."""
    if isinstance(deal, dict):
        return int(deal.get("magic") or 0)
    return int(getattr(deal, "magic", 0) or 0)


def attribution_report(
    deals: Iterable[Any],
    registry: Optional[dict[int, StrategyIdentity]] = None,
) -> dict[str, Any]:
    """Per-identity P&L and counts from a list of deals.

    Each deal is a dict or object with: magic, profit, commission, swap, fee.
    Returns:
        {
            "total": {"count": N, "pl": X},
            "by_identity": {
                "<id>": {
                    "id": ..., "version": ..., "kind": ..., "label": ...,
                    "magic": ..., "count": N, "pl": X,
                },
                ...
            },
            "unknown_magic": [list of unrecognized magic numbers],
        }
    """
    if registry is None:
        registry = load_registry()

    by_identity: dict[str, dict[str, Any]] = {}
    unknown_magics: set[int] = set()
    total_count = 0
    total_pl = 0.0

    for deal in deals:
        magic = _deal_magic(deal)
        pl = _deal_pl(deal)
        total_count += 1
        total_pl += pl

        identity = registry.get(magic)
        if identity is None:
            unknown_magics.add(magic)
            identity = UNKNOWN_IDENTITY

        key = identity.id
        if key not in by_identity:
            by_identity[key] = {
                "id": identity.id,
                "version": identity.version,
                "kind": identity.kind,
                "label": identity.label,
                "magic": identity.magic,
                "count": 0,
                "pl": 0.0,
            }
        by_identity[key]["count"] += 1
        by_identity[key]["pl"] = round(by_identity[key]["pl"] + pl, 2)

    return {
        "total": {"count": total_count, "pl": round(total_pl, 2)},
        "by_identity": by_identity,
        "unknown_magic": sorted(unknown_magics),
    }


def filter_attribution(
    deals: Iterable[Any],
    strategy_id: Optional[str] = None,
    version: Optional[str] = None,
    registry: Optional[dict[int, StrategyIdentity]] = None,
) -> dict[str, Any]:
    """Filter attribution by strategy_id and/or version.

    Returns the same shape as attribution_report but only including deals
    matching the filter criteria. If both are None, returns all.
    """
    if registry is None:
        registry = load_registry()

    filtered_deals = []
    for deal in deals:
        magic = _deal_magic(deal)
        identity = registry.get(magic)

        if identity is None:
            # Unknown magic — only include if filtering for unknown
            if strategy_id is not None and strategy_id != "unknown":
                continue
            if version is not None and version != "0.0.0":
                continue
        else:
            if strategy_id is not None and identity.id != strategy_id:
                continue
            if version is not None and identity.version != version:
                continue

        filtered_deals.append(deal)

    return attribution_report(filtered_deals, registry)

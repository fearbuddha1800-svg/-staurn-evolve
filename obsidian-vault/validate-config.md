---
slug: validate-config
type: note
graph: gitnexus
---

#!/usr/bin/env python3
"""Quant HQ configuration validator.

Validates config.json schema and reports any issues. Run before first launch.
Exit codes: 0 = valid, 1 = invalid.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
CONFIG = BASE / "config.json"

REQUIRED_KEYS = {
    "mode": str,
    "channels": list,
    "risk": dict,
    "sizing": dict,
    "manage": dict,
    "news_filter": dict,
    "algo": dict,
}

REQUIRED_RISK_KEYS = {
    "max_lot_per_trade": (int, float),
    "max_open_positions": int,
    "max_trades_per_day": int,
    "require_sl": bool,
    "daily_loss_limit": (int, float),
}

REQUIRED_MANAGE_KEYS = {
    "be_at_r": (int, float),
    "trail_from_r": (int, float),
    "trail_dist_r": (int, float),
    "interval_s": (int, float),
}

REQUIRED_ALGO_KEYS = {
    "symbols": list,
    "risk_pct": (int, float),
    "atr_sl_mult": (int, float),
    "use_tp": bool,
}


def _type_ok(value, expected):
    if isinstance(expected, tuple):
        return isinstance(value, expected)
    return isinstance(value, expected)


def validate(config):
    errors = []
    warnings = []

    # Top-level keys
    for key, expected_type in REQUIRED_KEYS.items():
        if key not in config:
            errors.append(f"Missing required key: {key}")
        elif not _type_ok(config[key], expected_type):
            errors.append(f"Key '{key}' must be {expected_type}, got {type(config[key]).__name__}")

    # Risk section
    risk = config.get("risk", {})
    for key, expected_type in REQUIRED_RISK_KEYS.items():
        if key not in risk:
            errors.append(f"Missing required key: risk.{key}")
        elif not _type_ok(risk[key], expected_type):
            errors.append(f"Key 'risk.{key}' must be {expected_type}, got {type(risk[key]).__name__}")

    # Manage section
    manage = config.get("manage", {})
    for key, expected_type in REQUIRED_MANAGE_KEYS.items():
        if key not in manage:
            errors.append(f"Missing required key: manage.{key}")
        elif not _type_ok(manage[key], expected_type):
            errors.append(f"Key 'manage.{key}' must be {expected_type}, got {type(manage[key]).__name__}")

    # Algo section
    algo = config.get("algo", {})
    for key, expected_type in REQUIRED_ALGO_KEYS.items():
        if key not in algo:
            errors.append(f"Missing required key: algo.{key}")
        elif not _type_ok(algo[key], expected_type):
            errors.append(f"Key 'algo.{key}' must be {expected_type}, got {type(algo[key]).__name__}")

    # Business rules
    if risk.get("require_sl") is True and algo.get("use_tp") is True:
        warnings.append("Both require_sl and use_tp are enabled — ensure TP/SL consistency")

    if algo.get("atr_sl_mult", 0) < 1.0:
        warnings.append("atr_sl_mult < 1.0 may result in very tight stops")

    if len(config.get("channels", [])) == 0:
        warnings.append("No Telegram channels configured — no signals will be ingested")

    return errors, warnings


def main():
    if not CONFIG.exists():
        print(f"[ERROR] {CONFIG} not found")
        return 1

    try:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[ERROR] Invalid JSON in {CONFIG}: {e}")
        return 1

    errors, warnings = validate(config)

    if errors:
        print(f"[ERROR] Configuration invalid — {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    if warnings:
        print(f"[WARNING] Configuration valid — {len(warnings)} warning(s):")
        for w in warnings:
            print(f"  - {w}")
    else:
        print("[OK] Configuration valid — no errors or warnings")

    return 0


if __name__ == "__main__":
    sys.exit(main())


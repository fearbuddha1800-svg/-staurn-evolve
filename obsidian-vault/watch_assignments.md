---
slug: watch_assignments
type: note
graph: gitnexus
---

"""Watch Assignments: map Pine strategies to symbol × timeframe combos.

Each assignment tells the signal watcher: "run this Pine strategy on this
symbol at this timeframe, and alert when a new signal appears."

Lives in watch_assignments.json (created on first run with defaults).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
ASSIGNMENTS_FILE = BASE / "watch_assignments.json"

DEFAULT_ASSIGNMENTS = [
    # strategy_id, symbol, timeframe, enabled
    ("ema_cross", "XAUUSD", "H1", True),
    ("ema_cross", "EURUSD", "H1", True),
    ("ema_cross", "GBPUSD", "H1", True),
    ("ema_cross", "XAUUSD", "M15", True),
    ("rsi_ema_trend", "XAUUSD", "H1", True),
    ("rsi_ema_trend", "EURUSD", "H1", True),
    ("rsi_ema_trend", "GBPUSD", "H1", True),
    ("rsi_ema_trend", "XAUUSD", "M15", True),
    *[(strategy, symbol, timeframe, True)
      for strategy in ("golden_eye_scalper", "golden_eye_trend_wrap")
      for symbol in ("XAUUSD", "EURUSD", "GBPUSD")
      for timeframe in ("H1", "M15")],
]


@dataclass
class WatchAssignment:
    id: str
    strategy_id: str
    symbol: str
    timeframe: str
    enabled: bool = True
    last_signal_hash: str | None = None
    last_signal_ts: str | None = None
    signal_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def _assignment_id(strategy_id: str, symbol: str, timeframe: str) -> str:
    return f"{strategy_id}-{symbol}-{timeframe}".replace(" ", "-")


def _load() -> list[dict]:
    if not ASSIGNMENTS_FILE.exists():
        save(DEFAULT_ASSIGNMENTS)
        return [asdict(WatchAssignment(
            id=_assignment_id(s, sym, tf), strategy_id=s, symbol=sym,
            timeframe=tf, enabled=e
        )) for s, sym, tf, e in DEFAULT_ASSIGNMENTS]
    with open(ASSIGNMENTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def save(entries: list[tuple] | list[dict]) -> None:
    if entries and isinstance(entries[0], tuple):
        data = [asdict(WatchAssignment(
            id=_assignment_id(s, sym, tf), strategy_id=s, symbol=sym,
            timeframe=tf, enabled=e
        )) for s, sym, tf, e in entries]
    else:
        data = entries
    ASSIGNMENTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def list_assignments() -> list[WatchAssignment]:
    return [WatchAssignment(**e) for e in _load()]


def get_assignment(assignment_id: str) -> WatchAssignment | None:
    for e in _load():
        if e.get("id") == assignment_id:
            return WatchAssignment(**e)
    return None


def update_signal(assignment_id: str, signal_hash: str, ts: str) -> None:
    data = _load()
    for e in data:
        if e.get("id") == assignment_id:
            e["last_signal_hash"] = signal_hash
            e["last_signal_ts"] = ts
            e["signal_count"] = e.get("signal_count", 0) + 1
            break
    ASSIGNMENTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def add_assignment(strategy_id: str, symbol: str, timeframe: str,
                   enabled: bool = True) -> WatchAssignment:
    data = _load()
    aid = _assignment_id(strategy_id, symbol, timeframe)
    if any(e.get("id") == aid for e in data):
        raise ValueError(f"assignment {aid} already exists")
    entry = asdict(WatchAssignment(
        id=aid, strategy_id=strategy_id, symbol=symbol,
        timeframe=timeframe, enabled=enabled
    ))
    data.append(entry)
    save(data)
    return WatchAssignment(**entry)


def remove_assignment(assignment_id: str) -> bool:
    data = _load()
    new_data = [e for e in data if e.get("id") != assignment_id]
    if len(new_data) == len(data):
        return False
    save(new_data)
    return True


def set_enabled(assignment_id: str, enabled: bool) -> bool:
    data = _load()
    for e in data:
        if e.get("id") == assignment_id:
            e["enabled"] = enabled
            save(data)
            return True
    return False


__all__ = [
    "WatchAssignment", "list_assignments", "get_assignment", "add_assignment",
    "remove_assignment", "set_enabled", "update_signal", "save",
]

## Links from
- [[signal_watcher]]

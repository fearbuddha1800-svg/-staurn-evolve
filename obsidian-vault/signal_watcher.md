---
slug: signal_watcher
type: note
graph: gitnexus
---

"""Signal Watcher Daemon.

Polls MT5 for new closed bars on each enabled watch assignment, runs the
assigned Pine strategy via PineTS, and when a NEW signal appears:

  1. Evaluates it through the AI confidence overlay
  2. Emits a `pine_signal` event on the event bus (persisted to signals.db)
  3. Dispatches alerts (Telegram + cockpit event)

Run directly:  python signal_watcher.py          (foreground, Ctrl-C to stop)
               python signal_watcher.py --once   (single poll pass, exit)

Each assignment is polled every POLL_INTERVAL seconds. MT5 connection is
acquired/released per pass to avoid holding the terminal lock.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

import MetaTrader5 as mt5  # noqa: E402

from pinets_runner import run_pine_strategy, extract_signal  # noqa: E402
from watch_assignments import (  # noqa: E402
    list_assignments, get_assignment, update_signal, WatchAssignment,
)
from event_bus import publish, make_event, bus  # noqa: E402
from ai_overlay import AIOverlay  # noqa: E402
from empire_framework import log_signal  # noqa: E402

POLL_INTERVAL = 30.0  # seconds between full poll passes
CANDLE_COUNT = 500

EVENT_TYPE = "pine_signal"
SOURCE = "signal_watcher"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _signal_hash(symbol: str, timeframe: str, strategy: str,
                 signal: dict[str, Any]) -> str:
    """Content hash to deduplicate the same signal firing repeatedly."""
    payload = f"{symbol}|{timeframe}|{strategy}|{signal.get('action')}|{signal.get('price')}|{signal.get('time')}"
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _mt5_connected() -> bool:
    info = mt5.terminal_info()
    return info is not None and info.connected


def _ensure_mt5() -> bool:
    if _mt5_connected():
        return True
    return mt5.initialize()


def _poll_assignment(assignment: WatchAssignment, overlay: AIOverlay,
                     ai_enabled: bool) -> dict[str, Any] | None:
    """Run one assignment: fetch candles, run PineTS, detect new signal.

    Returns an event payload dict if a new signal was detected, else None.
    """
    pine_file = BASE / "strategies" / f"{assignment.strategy_id}.pine"
    if not pine_file.exists():
        return {"error": f"strategy file not found: {pine_file}"}

    result = run_pine_strategy(
        str(pine_file),
        symbol=assignment.symbol,
        timeframe=assignment.timeframe,
        count=CANDLE_COUNT,
    )
    if not result.get("ok"):
        return {"error": result.get("error", "pine run failed")}

    signal = extract_signal(result)
    if not signal:
        return None  # no actionable signal on latest bar

    sig_hash = _signal_hash(assignment.symbol, assignment.timeframe,
                            assignment.strategy_id, signal)
    if sig_hash == assignment.last_signal_hash:
        return None  # already seen this signal

    # AI confidence overlay
    ai_prediction = None
    if ai_enabled:
        try:
            ai_prediction = overlay.evaluate(signal, result, context={
                "symbol": assignment.symbol,
                "timeframe": assignment.timeframe,
                "setup_id": assignment.strategy_id,
            })
        except Exception as exc:  # noqa: BLE001
            ai_prediction = None

    payload = {
        "assignment_id": assignment.id,
        "strategy_id": assignment.strategy_id,
        "strategy_name": getattr(assignment, "strategy_name", assignment.strategy_id),
        "symbol": assignment.symbol,
        "timeframe": assignment.timeframe,
        "action": signal["action"],
        "price": signal.get("price"),
        "sl": signal.get("sl"),
        "tp": signal.get("tp"),
        "reason": signal.get("reason", "pineTS signal"),
        "signal_hash": sig_hash,
        "ts": _iso_now(),
        "bars": result.get("bars"),
        "plots": result.get("plots", {}),
        "ai": {
            **asdict(ai_prediction),
            "setup_confidence": ai_prediction.setup_confidence,
        } if ai_prediction else {"direction": None, "confidence": None, "rationale": "ai_disabled"},
    }
    return payload


from alert_dispatcher import dispatch as dispatch_alert  # noqa: E402


def run_once(ai_enabled: bool = True) -> list[dict[str, Any]]:
    """Single poll pass over all enabled assignments. Returns emitted events."""
    if not _ensure_mt5():
        print("MT5 not available — cannot poll")
        return []

    overlay = AIOverlay() if ai_enabled else None
    emitted: list[dict[str, Any]] = []

    try:
        assignments = [a for a in list_assignments() if a.enabled]
        for assignment in assignments:
            try:
                payload = _poll_assignment(assignment, overlay, ai_enabled)
            except Exception as exc:  # noqa: BLE001
                print(f"assignment {assignment.id} error: {type(exc).__name__}: {exc}")
                continue
            if payload is None:
                continue
            if isinstance(payload, dict) and "error" in payload:
                print(f"assignment {assignment.id}: {payload['error']}")
                continue

            # Emit event on the bus
            event = make_event(
                type=EVENT_TYPE,
                source=SOURCE,
                payload=payload,
            )
            publish(event)

            # Persist signal to audit ledger
            try:
                log_signal(
                    strategy=payload["strategy_name"],
                    symbol=payload["symbol"],
                    signal_type=payload["action"],
                    price=payload["price"],
                    confidence=payload["ai"]["confidence"],
                    sl=payload["sl"],
                    tp=payload["tp"],
                    metadata={
                        "assignment_id": payload["assignment_id"],
                        "strategy_id": payload["strategy_id"],
                        "timeframe": payload["timeframe"],
                        "signal_hash": payload["signal_hash"],
                        "reason": payload["reason"],
                        "ai_rationale": payload["ai"]["rationale"],
                        "bars": payload["bars"],
                    },
                )
            except Exception as exc:  # noqa: BLE001
                print(f"audit ledger write failed: {exc}")

            # Update assignment so we don't re-fire the same signal
            update_signal(assignment.id, payload["signal_hash"], payload["ts"])

            # Alert
            dispatch_alert(payload)

            emitted.append(payload)
            print(f"[{payload['ts']}] NEW SIGNAL {assignment.id}: "
                  f"{payload['action']} {payload['symbol']} @ {payload['price']} "
                  f"(AI conf={payload['ai']['confidence']})")

        if not emitted:
            print(f"[{_iso_now()}] poll complete — no new signals "
                  f"({len(assignments)} assignments)")
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass

    return emitted


def run_forever(ai_enabled: bool = True, interval: float = POLL_INTERVAL) -> None:
    print(f"Signal watcher started — {interval}s poll interval, AI={'on' if ai_enabled else 'off'}")
    try:
        while True:
            run_once(ai_enabled=ai_enabled)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nSignal watcher stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-chart PineTS signal watcher")
    parser.add_argument("--once", action="store_true",
                        help="run a single poll pass and exit")
    parser.add_argument("--no-ai", action="store_true",
                        help="disable AI confidence overlay")
    parser.add_argument("--interval", type=float, default=POLL_INTERVAL,
                        help="poll interval in seconds (default 30)")
    args = parser.parse_args()

    if args.once:
        events = run_once(ai_enabled=not args.no_ai)
        print(f"Single pass complete — {len(events)} new signal(s)")
    else:
        run_forever(ai_enabled=not args.no_ai, interval=args.interval)


if __name__ == "__main__":
    main()


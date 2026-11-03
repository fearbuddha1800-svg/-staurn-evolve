---
slug: pine_runner
type: note
graph: gitnexus
---

"""Pine Script strategy runner for the signal-relay workspace.

Executes native TradingView Pine Script strategies on live MT5 data via
LuxAlgo's PineTS bridge (pinets_runner.run_pine_strategy -> pinets_bridge.js
-> Node.js).

DRY RUN BY CONSTRUCTION. This module never imports executor.py and never calls
any MT5 order function. record_signal() writes one row to signals.db (trades
table, status='pine_signal', msg_id='pine_<name>_<ts>') and nothing else.
paper_mode (config flag, default true) only documents the mode; there is no
live-order code path to switch off.
"""
from __future__ import annotations

import json
import hashlib
import os
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(BASE, "config.json")
DB = os.path.join(BASE, "signals.db")
STRATEGY_DIR = os.path.join(BASE, "strategies")
LOCK_FILE = os.path.join(BASE, "pine.lock")
HALT_FILE = os.path.join(BASE, "HALT")
PAUSE_FILE = os.path.join(BASE, "PAUSE")
STOP_FILE = os.path.join(BASE, "STOP")

DEFAULT_SYMBOL = "XAUUSD"
DEFAULT_TIMEFRAME = "H1"
STALE_LOCK_MINUTES = 30
SLEEP_CHUNK_S = 2  # interruptible sleep granularity for HALT/PAUSE/STOP checks

try:
    import pinets_runner  # imports MetaTrader5; unavailable without a live terminal
except ImportError:  # pragma: no cover - environment without MT5
    pinets_runner = None


def _load_config() -> dict[str, Any]:
    try:
        with open(CONFIG, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def paper_mode() -> bool:
    """Global paper-mode flag from config.json (default true)."""
    return bool(_load_config().get("paper_mode", True))


def loop_interval_s() -> int:
    try:
        return int(_load_config().get("pine_loop_interval_s", 60))
    except (TypeError, ValueError):
        return 60


def load_strategy_config() -> list[dict[str, Any]]:
    """Read config.pine_strategies.

    Accepts a list of {name, enabled, paper, path, symbol, timeframe} records
    (strings treated as name-only) or a {name: {...}} map. Returns [] when the
    block is absent or empty — safe default while the user has no .pine files.
    """
    block = _load_config().get("pine_strategies")
    out: list[dict[str, Any]] = []

    def norm(name: str, rec: dict[str, Any]) -> dict[str, Any]:
        rec = rec if isinstance(rec, dict) else {}
        return {
            "name": str(name),
            "enabled": bool(rec.get("enabled", False)),
            "paper": bool(rec.get("paper", True)),
            "path": str(rec.get("path") or rec.get("file") or ""),
            "symbol": str(rec.get("symbol") or DEFAULT_SYMBOL),
            "timeframe": str(rec.get("timeframe") or DEFAULT_TIMEFRAME),
        }

    if isinstance(block, list):
        for i, rec in enumerate(block):
            if isinstance(rec, dict):
                out.append(norm(str(rec.get("name") or rec.get("id") or f"strategy-{i + 1}"), rec))
            elif isinstance(rec, str):
                out.append(norm(rec, {}))
    elif isinstance(block, dict):
        for name, rec in block.items():
            out.append(norm(str(name), rec))
    return out


def _resolve(name: str) -> dict[str, Any] | None:
    for entry in load_strategy_config():
        if entry["name"] == name:
            return entry
    fallback = os.path.join(STRATEGY_DIR, f"{name}.pine")
    if os.path.exists(fallback):
        return {
            "name": name,
            "enabled": True,
            "paper": True,
            "path": fallback,
            "symbol": DEFAULT_SYMBOL,
            "timeframe": DEFAULT_TIMEFRAME,
        }
    return None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_strategy(name: str) -> dict[str, Any]:
    """Run one named strategy and return its latest_signal, enriched.

    Fields: name, ok, action (buy|sell|None), price, sl, tp, reason, symbol,
    timeframe, error, ts. Returns the latest_signal content plus the name so
    record_signal() can build msg_id='pine_<name>_<ts>'.
    """
    out: dict[str, Any] = {
        "name": name,
        "ok": False,
        "action": None,
        "price": None,
        "sl": None,
        "tp": None,
        "reason": None,
        "symbol": None,
        "timeframe": None,
        "error": None,
        "ts": _now_iso(),
    }

    entry = _resolve(name)
    if entry is None:
        out["error"] = (
            f"strategy '{name}' not found in config.pine_strategies "
            f"or strategies/{name}.pine"
        )
        return out

    out["symbol"] = entry["symbol"]
    out["timeframe"] = entry["timeframe"]

    if pinets_runner is None:
        out["error"] = "PineTS runner unavailable (MetaTrader5 not installed)"
        return out

    pine_file = entry["path"]
    if not os.path.isabs(pine_file):
        pine_file = os.path.join(BASE, pine_file)
    if not os.path.exists(pine_file):
        out["error"] = f"pine file not found: {pine_file}"
        return out

    try:
        result = pinets_runner.run_pine_strategy(
            pine_file, entry["symbol"], entry["timeframe"]
        )
    except Exception as exc:  # keep one strategy's failure from killing the rest
        out["error"] = f"runner raised {type(exc).__name__}: {exc}"
        return out

    if not isinstance(result, dict) or not result.get("ok"):
        out["error"] = (result.get("error", "pineTS run returned no result")
                        if isinstance(result, dict) else "pineTS run returned non-object result")
        return out

    sig = result.get("latest_signal") or {}
    if not isinstance(sig, dict):
        out["error"] = "pineTS latest_signal is not an object"
        return out
    sig_type = str(sig.get("type") or "").lower()
    if sig_type in ("long", "buy"):
        action = "buy"
    elif sig_type in ("short", "sell"):
        action = "sell"
    else:
        action = None

    out.update(
        ok=True,
        action=action,
        price=sig.get("price"),
        sl=sig.get("sl"),
        tp=sig.get("tp"),
        signal_time=sig.get("time"),
        reason=sig.get("reason")
        or f"pineTS strategy signal at {sig.get('time')}",
    )
    return out


def backtest_strategy(pine_file: str, *, symbol: str = DEFAULT_SYMBOL,
                      timeframe: str = DEFAULT_TIMEFRAME, count: int = 500) -> dict[str, Any]:
    """Explicit trusted-owner research run; never record a signal or send an order.

    Returns the real PineTS bridge result (including stats and closed_trades),
    not a signal projection. Engine output may contain a truncated trade tail.
    """
    if not isinstance(count, int) or isinstance(count, bool) or not 20 <= count <= 1500:
        raise ValueError('Backtest candle count must be between 20 and 1500')
    if timeframe not in ('M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'):
        raise ValueError('Unsupported backtest timeframe')
    if not isinstance(symbol, str) or not symbol or len(symbol) > 40:
        raise ValueError('Invalid backtest symbol')
    if pinets_runner is None:
        return {'ok': False, 'error': 'PineTS runner unavailable (MetaTrader5 not installed)'}
    return pinets_runner.run_pine_strategy(pine_file, symbol, timeframe, count)


def run_all_strategies() -> dict[str, dict[str, Any]]:
    """Run every enabled strategy; returns {name: signal}."""
    signals: dict[str, dict[str, Any]] = {}
    for entry in load_strategy_config():
        if not entry.get("enabled"):
            continue
        signals[entry["name"]] = run_strategy(entry["name"])
    return signals


def record_signal(signal: dict[str, Any], db: str | None = None) -> str:
    """Log a pine signal to signals.db.trades. Dry run: no MT5 order.

    msg_id = pine_<name>_<ts>, status = 'pine_signal'. Column set matches the
    existing trades table; the table is created if missing (safe on a scratch
    DB copy — never alters the live schema path used by other tools).
    Returns the msg_id written.
    """
    db = db or DB
    name = str(signal.get("name", "pine"))
    ts = signal.get("ts") or _now_iso()
    # Poll time is not signal identity: an open Pine trade repeats across polls.
    identity = [name, signal.get("symbol"), signal.get("timeframe"),
                signal.get("action"), signal.get("signal_time") or ts]
    stamp = hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()
    msg_id = f"pine_{name}_{stamp}"
    detail = f"paper={paper_mode()} " + str(signal.get("reason") or "")

    con = sqlite3.connect(db, timeout=30)
    try:
        con.execute("PRAGMA busy_timeout=10000")
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            "CREATE TABLE IF NOT EXISTS trades ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, msg_id TEXT, ts TEXT, "
            "symbol TEXT, side TEXT, lot REAL, entry TEXT, sl REAL, tp REAL, "
            "order_type TEXT, ticket INTEGER, status TEXT, detail TEXT)"
        )
        if con.execute("SELECT 1 FROM trades WHERE msg_id=? AND status='pine_signal'",
                       (msg_id,)).fetchone():
            return msg_id
        con.execute(
            "INSERT INTO trades (msg_id, ts, symbol, side, lot, entry, sl, tp, "
            "order_type, ticket, status, detail) VALUES (?, ?, ?, ?, ?, ?, ?, "
            "?, ?, ?, ?, ?)",
            (
                msg_id,
                ts,
                signal.get("symbol"),
                signal.get("action"),
                None,
                signal.get("price"),
                signal.get("sl"),
                signal.get("tp"),
                "market",
                None,
                "pine_signal",
                detail,
            ),
        )
        con.commit()
    finally:
        con.close()
    return msg_id


# --------------------------------------------------------------------------- #
# single-instance lock + halt/pause/stop files
# --------------------------------------------------------------------------- #
class PineLock:
    """Single-instance guard via pine.lock (O_EXCL creation). Stale locks older
    than STALE_LOCK_MINUTES are reaped automatically."""

    def __init__(self, path: str = LOCK_FILE) -> None:
        self.path = path
        self.fd: int | None = None

    def __enter__(self) -> "PineLock":
        if os.path.exists(self.path):
            try:
                age = time.time() - os.path.getmtime(self.path)
                if age > STALE_LOCK_MINUTES * 60:
                    os.unlink(self.path)
                else:
                    raise RuntimeError(
                        "pine_runner already running (pine.lock held by another instance)"
                    )
            except OSError:
                try:
                    os.unlink(self.path)
                except OSError:
                    raise RuntimeError(
                        "pine_runner already running (pine.lock held by another instance)"
                    )
        try:
            self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except OSError:
            raise RuntimeError(
                "pine_runner already running (pine.lock held by another instance)"
            )
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(f"{os.getpid()}\n")
        return self

    def __exit__(self, *exc: Any) -> None:
        if self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            try:
                os.unlink(self.path)
            except OSError:
                pass


def halt_requested() -> bool:
    return os.path.exists(HALT_FILE) or os.path.exists(STOP_FILE)


def paused() -> bool:
    return os.path.exists(PAUSE_FILE)


def run_forever(interval_s: int | None = None, once: bool = False) -> str:
    """Loop every interval_s seconds (default 60 from config), running enabled
    strategies and recording any actionable signal. Exits when HALT/STOP appears.
    PAUSE skips a pass. `once` runs a single pass and returns."""
    interval_s = loop_interval_s() if interval_s is None else int(interval_s)
    with PineLock():
        while True:
            if halt_requested():
                return "halted"
            if not paused():
                for _name, signal in run_all_strategies().items():
                    if halt_requested():
                        return "halted"
                    if signal.get("ok") and signal.get("action"):
                        record_signal(signal)
            if once:
                return "done"
            deadline = time.time() + interval_s
            while time.time() < deadline:
                if halt_requested():
                    return "halted"
                time.sleep(min(SLEEP_CHUNK_S, deadline - time.time()))


def main(argv: list[str] | None = None) -> int:
    import sys

    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] not in ("--once", "--interval", "-i"):
        name = argv[0]
        signal = run_strategy(name)
        print(json.dumps(signal, indent=2))
        return 0 if signal.get("ok") else 1

    interval_s = loop_interval_s()
    i = 0
    while i < len(argv):
        if argv[i] in ("--interval", "-i") and i + 1 < len(argv):
            try:
                interval_s = int(argv[i + 1])
            except ValueError:
                print(f"invalid interval: {argv[i + 1]}")
                return 2
            i += 2
        elif argv[i] == "--once":
            return 0 if run_forever(interval_s, once=True) == "done" else 1
        else:
            i += 1
    print(f"pine_runner: loop {interval_s}s (paper_mode={paper_mode()}). Create HALT/STOP to exit, PAUSE to skip passes.")
    return 0 if run_forever(interval_s) == "halted" else 0


if __name__ == "__main__":
    raise SystemExit(main())

## Links from
- [[strategy_registry]]
- [[test_pine_runner]]
- [[test_strategy_registry]]

---
slug: pine_transpiled
type: note
graph: gitnexus
---

"""Python transpositions of the two bundled Pine v5 strategies.

Indicator calculations and order conditions execute in Python. Only broker
simulation (fills, reversals, sizing, stops/limits and accounting) is delegated
to the existing pinets_bridge.js via a generated, indicator-free order tape.
No MT5 connection, orders, external packages or live data are needed.

Replay and verify the cached data:
    python pine_transpiled.py --verify

This reproduces this installed PineTS runtime, not a claim of TradingView parity.
The bridge exposes only the last 20 closed trades/ledger entries.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from typing import Any

BASE = Path(__file__).resolve().parent
BRIDGE = BASE / "pinets_bridge.js"
DIST = BASE.parent / "luxalgo/PineTS/dist/pinets.min.cjs"
DEFAULT_CSV = BASE / "strategy2_data_XAUUSD.csv"


def _period(n: int) -> int:
    if isinstance(n, bool) or not isinstance(n, int) or n < 1:
        raise ValueError("indicator periods must be positive integers")
    return n


def ema(values: list[float], period: int) -> list[float | None]:
    """Installed PineTS: SMA seed, then raw EMA state, 10dp outputs."""
    period = _period(period)
    out: list[float | None] = []
    total = 0.0
    state = None
    alpha = 2 / (period + 1)
    for i, value in enumerate(values):
        if i < period:
            total += value
            if i == period - 1:
                state = total / period
        else:
            state = value * alpha + state * (1 - alpha)
        out.append(None if state is None else round(state, 10))
    return out


def rsi(values: list[float], period: int) -> list[float | None]:
    """Wilder gain/loss smoothing, first output after period changes."""
    period = _period(period)
    out: list[float | None] = [None] * len(values)
    gain_sum = loss_sum = 0.0
    gain_avg = loss_avg = 0.0
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gain, loss = max(delta, 0), max(-delta, 0)
        if i <= period:
            gain_sum += gain
            loss_sum += loss
            if i < period:
                continue
            gain_avg, loss_avg = gain_sum / period, loss_sum / period
        else:
            gain_avg = (gain_avg * (period - 1) + gain) / period
            loss_avg = (loss_avg * (period - 1) + loss) / period
        out[i] = round(100.0 if loss_avg == 0 else 100 - 100 / (1 + gain_avg / loss_avg), 10)
    return out


def atr(candles: list[dict[str, Any]], period: int) -> list[float | None]:
    period = _period(period)
    out: list[float | None] = []
    total = 0.0
    state = None
    for i, c in enumerate(candles):
        tr = c["high"] - c["low"]
        if i:
            previous = candles[i - 1]["close"]
            tr = max(tr, abs(c["high"] - previous), abs(c["low"] - previous))
        if i < period:
            total += tr
            if i == period - 1:
                state = total / period
        else:
            state = (state * (period - 1) + tr) / period
        out.append(None if state is None else round(state, 10))
    return out


def cross(a: list, b: list, i: int, up: bool = True) -> bool:
    if i == 0 or any(v is None for v in (a[i], a[i - 1], b[i], b[i - 1])):
        return False
    return (a[i] > b[i] and a[i - 1] <= b[i - 1]) if up else (a[i] < b[i] and a[i - 1] >= b[i - 1])


class EMACross:
    name = "ema_cross"
    declaration = 'strategy("EMA Cross Signals", overlay=true)'

    def __init__(self, fast_len: int = 9, slow_len: int = 21):
        self.fast_len, self.slow_len = _period(fast_len), _period(slow_len)

    def evaluate(self, candles: list[dict[str, Any]]) -> dict[str, Any]:
        closes = [c["close"] for c in candles]
        fast, slow = ema(closes, self.fast_len), ema(closes, self.slow_len)
        orders = []
        for i in range(len(candles)):
            if cross(fast, slow, i):
                orders.append(dict(bar_index=i, direction="long", entry_id="Long", sl=None, tp=None))
            if cross(fast, slow, i, False):
                orders.append(dict(bar_index=i, direction="short", entry_id="Short", sl=None, tp=None))
        return {"plots": {"Fast EMA": fast, "Slow EMA": slow}, "orders": orders}


class RSIEMATrend:
    name = "rsi_ema_trend"
    declaration = ('strategy("RSI + EMA Trend", overlay=true, '
                   'default_qty_type=strategy.percent_of_equity, default_qty_value=100)')

    def __init__(self, rsi_len: int = 14, ema_len: int = 50, atr_len: int = 14):
        self.rsi_len, self.ema_len, self.atr_len = map(_period, (rsi_len, ema_len, atr_len))

    def evaluate(self, candles: list[dict[str, Any]]) -> dict[str, Any]:
        closes = [c["close"] for c in candles]
        rs, em, at = rsi(closes, self.rsi_len), ema(closes, self.ema_len), atr(candles, self.atr_len)
        lower, upper = [35.0] * len(closes), [65.0] * len(closes)
        orders = []
        for i, close in enumerate(closes):
            if em[i] is None or at[i] is None:
                continue
            if close > em[i] and cross(rs, lower, i):
                orders.append(dict(bar_index=i, direction="long", entry_id="Long",
                                   sl=close - at[i] * 2, tp=close + at[i] * 3))
            if close < em[i] and cross(rs, upper, i, False):
                orders.append(dict(bar_index=i, direction="short", entry_id="Short",
                                   sl=close + at[i] * 2, tp=close - at[i] * 3))
        return {"plots": {"RSI": rs, "EMA": em, "ATR": at}, "orders": orders}


def validate_candles(candles: list[dict[str, Any]]) -> None:
    if not candles:
        raise ValueError("no candles")
    previous = -1
    for c in candles:
        if not all(isinstance(c[k], (int, float)) and math.isfinite(c[k]) for k in
                   ("openTime", "open", "high", "low", "close", "volume")):
            raise ValueError("candles require finite OHLCV and timestamp")
        if c["openTime"] <= previous or c["volume"] < 0:
            raise ValueError("candles must be ordered, unique, with nonnegative volume")
        if c["low"] > min(c["open"], c["close"]) or c["high"] < max(c["open"], c["close"]):
            raise ValueError("invalid OHLC range")
        previous = c["openTime"]


def load_csv(path: Path, count: int = 500) -> tuple[list[dict[str, Any]], int]:
    if count < 1:
        raise ValueError("count must be positive")
    with path.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if len(rows) < count:
        raise ValueError(f"requested {count} bars but CSV has {len(rows)}")
    candles = [{"openTime": int(r["time"]) * 1000,
                **{k: float(r[k]) for k in ("open", "high", "low", "close")},
                "volume": float(r["tick_volume"])} for r in rows[-count:]]
    validate_candles(candles)
    return candles, len(rows)


def order_tape(strategy: Any, evaluation: dict[str, Any]) -> str:
    """Serialize Python-computed orders only; no indicator logic runs in Pine."""
    lines = ["//@version=5", strategy.declaration]
    for order in evaluation["orders"]:
        entry, direction = order["entry_id"], order["direction"]
        lines.extend([f'if bar_index == {order["bar_index"]}',
                      f'    strategy.entry("{entry}", strategy.{direction})'])
        if order["sl"] is not None:
            lines.append(f'    strategy.exit("{entry} Exit", "{entry}", '
                         f'stop={order["sl"]!r}, limit={order["tp"]!r})')
    # An empty-order strategy still has a valid executable body.
    lines.append('plot(close, "Close")')
    return "\n".join(lines) + "\n"


def run_bridge(pine_file: Path, candles: list[dict[str, Any]], symbol: str = "XAUUSD",
               timeframe: str = "60", bridge: Path = BRIDGE) -> dict[str, Any]:
    validate_candles(candles)
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is required")
    if not bridge.is_file():
        raise FileNotFoundError(bridge)
    # Existing bridge hardcodes H1 closeTime. Refuse misleading other intervals.
    if timeframe != "60":
        raise ValueError("this existing bridge is verified for H1 (60) only")
    scratch = Path(os.environ.get("TMPDIR") or Path.home() / ".hermes/cache/scratch")
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pine_transposed_", dir=scratch) as tmp:
        data = Path(tmp) / "candles.json"
        data.write_text(json.dumps(candles, allow_nan=False), encoding="utf-8")
        proc = subprocess.run([node, str(bridge), str(pine_file.resolve()), str(data), symbol, timeframe],
                              capture_output=True, text=True, timeout=30, cwd=bridge.parent, shell=False)
    if proc.returncode:
        raise RuntimeError(f"bridge exit {proc.returncode}: {proc.stderr[:500]}")
    result = json.loads(proc.stdout)
    if not isinstance(result, dict) or result.get("ok") is not True:
        raise RuntimeError(f"bridge failure: {result}")
    if result.get("bars") != len(candles):
        raise RuntimeError("bridge returned incorrect bar count")
    return result


def run_transpiled(strategy: Any, candles: list[dict[str, Any]]) -> tuple[dict, dict]:
    validate_candles(candles)
    evaluation = strategy.evaluate(candles)
    scratch = Path(os.environ.get("TMPDIR") or Path.home() / ".hermes/cache/scratch")
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="pine_order_tape_", dir=scratch) as tmp:
        script = Path(tmp) / "orders.pine"
        script.write_text(order_tape(strategy, evaluation), encoding="utf-8")
        result = run_bridge(script, candles)
    return result, evaluation


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(csv_path: Path = DEFAULT_CSV, count: int = 500) -> dict:
    candles, row_count = load_csv(csv_path, count)
    checks = []
    results = {}
    for strategy in (EMACross(), RSIEMATrend()):
        source = BASE / "strategies" / (strategy.name + ".pine")
        original = run_bridge(source, candles)
        translated, evaluation = run_transpiled(strategy, candles)
        # Equality covers every exposed execution field, not just the last signal.
        fields = ("bars", "last_close", "open_trades", "closed_trades", "ledger", "position", "stats", "latest_signal")
        for field in fields:
            checks.append({"name": f"{strategy.name}.{field}", "passed": original[field] == translated[field]})
        for title, series in evaluation["plots"].items():
            valid = [v for v in series if v is not None]
            observed = original.get("plots", {}).get(title, {})
            recent = observed.get("recent", [])
            matches = bool(valid) and len(recent) == min(10, len(valid)) and all(
                math.isclose(a, b, abs_tol=1e-8, rel_tol=0) for a, b in zip(valid[-10:], recent))
            checks.append({"name": f"{strategy.name}.indicator.{title}", "passed": matches})
        results[strategy.name] = {"source_sha256": _sha(source), "python_order_count": len(evaluation["orders"]),
                                  "python_orders": evaluation["orders"], "original": original, "transposed": translated}
    ema_result = results["ema_cross"]["transposed"]
    expected = {"open_trades": 1, "closed_trades": 20, "direction": "long", "entry_price": 4145.62,
                "netprofit": -310.28, "max_drawdown": 393.01, "equity": 999712.87}
    observations = {"open_trades": len(ema_result["open_trades"]),
                    "closed_trades": len(ema_result["closed_trades"]),
                    "direction": ema_result["position"]["direction"],
                    "entry_price": ema_result["position"]["avg_price"],
                    **{k: round(ema_result["stats"][k], 2) for k in ("netprofit", "max_drawdown", "equity")}}
    for key, value in expected.items():
        checks.append({"name": f"delivery_ledger.{key}", "passed": observations[key] == value})
    return {"ok": all(c["passed"] for c in checks), "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "architecture": "Python indicators/entry/exit conditions; PineTS order-tape execution/accounting via existing pinets_bridge.js",
            "data": {"path": str(csv_path.resolve()), "sha256": _sha(csv_path), "rows": row_count, "bars": len(candles),
                     "symbol": "XAUUSD", "timeframe": "H1", "first_open_time_ms": candles[0]["openTime"],
                     "last_open_time_ms": candles[-1]["openTime"], "last_close": candles[-1]["close"],
                     "provenance": "Existing local MT5-format historical CSV supplied by workspace; not independently vendor-authenticated."},
            "runtime": {"bridge_sha256": _sha(BRIDGE), "pinets_dist_sha256": _sha(DIST)},
            "delivery_ledger": {"expected": expected, "observed": observations}, "checks": checks, "strategies": results,
            "limitations": ["Bridge truncates closed_trades/ledger to last 20; EMA reports exactly 20 here and Python emits 21 reversal entries.",
                            "No live MT5 access or trading; no TradingView performance/equivalence claim.",
                            "Python calculations match installed PineTS SMA-seeded EMA, not first-price EMA.",
                            "Node timeout is not a hostile-code security sandbox; use only trusted local strategy source."]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true", help="compare both native Python order tapes against original Pine")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--report", type=Path, default=BASE / "pine_transpiled_verification.json")
    args = parser.parse_args()
    if not args.verify:
        parser.error("use --verify to replay both strategies")
    report = verify(args.csv, args.count)
    args.report.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "report": str(args.report), "checks": len(report["checks"]),
                      "failed": [c["name"] for c in report["checks"] if not c["passed"]],
                      "observed": report["delivery_ledger"]["observed"]}, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

## Links from
- [[strategies.transpiled_strategies]]
- [[test_transpiled_strategies_offline]]

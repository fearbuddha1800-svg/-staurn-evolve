---
slug: pinets_runner
type: note
graph: gitnexus
---

"""PineTS Runner: execute real TradingView Pine Script strategies on live MT5 data.
Uses LuxAlgo's PineTS runtime (Node.js) via pinets_bridge.js.
Python fetches MT5 candles -> JSON file -> Node.js runs the .pine strategy -> JSON signals back.
"""
from __future__ import annotations
from broker_lifecycle import initialize_existing
import json, os, subprocess, tempfile, time
from typing import Optional, Dict, Any, List, Tuple

import MetaTrader5 as mt5

BASE = os.path.dirname(os.path.abspath(__file__))
PINETS_DIST = os.path.join(os.path.dirname(BASE), "luxalgo", "PineTS", "dist", "pinets.min.cjs")
BRIDGE = os.path.join(BASE, "pinets_bridge.js")

TF_MAP = {
    "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1, "MN1": mt5.TIMEFRAME_MN1,
}
# PineTS timeframe strings
PINETS_TF = {"M1": "1", "M5": "5", "M15": "15", "M30": "30", "H1": "60", "H4": "240", "D1": "D"}


def fetch_candles(symbol: str, timeframe: str = "H1", count: int = 500) -> List[Dict[str, Any]]:
    """Fetch closed candles from MT5 as PineTS-compatible JSON."""
    tf = TF_MAP.get(timeframe.upper(), mt5.TIMEFRAME_H1)
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count + 1)
    if rates is None or len(rates) < 2:
        return []
    rates = rates[:-1]  # drop the still-forming bar
    candles = []
    for r in rates:
        candles.append({
            "openTime": int(r[0]) * 1000,  # epoch ms
            "open": float(r[1]),
            "high": float(r[2]),
            "low": float(r[3]),
            "close": float(r[4]),
            "volume": float(r[5]),
        })
    return candles


def run_pine_strategy(pine_file: str, symbol: str = "XAUUSD",
                      timeframe: str = "H1", count: int = 500) -> Dict[str, Any]:
    """Run a Pine Script strategy file on live MT5 data via PineTS.
    Returns {ok, plots, trades, latest_signal, last_close, error}."""
    # Only release attachments acquired by this call, including on early errors.
    owns_attachment = not bool(mt5.terminal_info())
    if owns_attachment and not initialize_existing(mt5):
        return {"ok": False, "error": "MT5 not attached"}
    candles_path = None
    try:
        candles = fetch_candles(symbol, timeframe, count)
        if not candles:
            return {"ok": False, "error": f"no {timeframe} candles for {symbol}"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False,
                                          dir=os.environ.get("TMPDIR") or os.path.join(
                                              os.path.expanduser("~"), ".hermes", "cache", "scratch"),
                                          prefix="pinets_candles_") as f:
            candles_path = f.name
            json.dump(candles, f)

        # run the Node.js bridge
        tf_str = PINETS_TF.get(timeframe.upper(), "60")
        result = subprocess.run(
            ["node", BRIDGE, pine_file, candles_path, symbol, tf_str],
            capture_output=True, text=True, timeout=30,
            cwd=BASE,
            env={**os.environ, "NODE_PATH": os.path.dirname(PINETS_DIST)},
        )
        if result.returncode != 0:
            return {"ok": False, "error": f"pineTS exit {result.returncode}: {result.stderr[:300]}"}
        try:
            decoded = json.loads(result.stdout.strip())
            return decoded if isinstance(decoded, dict) else {
                "ok": False, "error": "bridge output is not an object"}
        except json.JSONDecodeError:
            return {"ok": False, "error": f"bridge output not JSON: {result.stdout[:200]}"}
    finally:
        try:
            if candles_path is not None:
                os.unlink(candles_path)
        except OSError:
            pass
        if owns_attachment:
            mt5.shutdown()


def extract_signal(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract the actionable signal from a PineTS result.
    Returns {action: buy|sell, lots: float, sl: float|None, tp: float|None, reason: str}
    or None if no signal."""
    if not isinstance(result, dict) or not result.get("ok"):
        return None
    sig = result.get("latest_signal")
    if not isinstance(sig, dict) or not sig:
        return None
    action = "buy" if (sig.get("type") or "").lower() in ("long", "buy") else \
             "sell" if (sig.get("type") or "").lower() in ("short", "sell") else None
    if not action:
        return None
    return {
        "action": action,
        "price": sig.get("price"),
        "sl": sig.get("sl"),
        "tp": sig.get("tp"),
        "reason": f"pineTS strategy signal at {sig.get('time')}",
    }


def run_and_signal(pine_file: str, symbol: str = "XAUUSD",
                   timeframe: str = "H1") -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """Convenience: run the strategy and extract the signal in one call."""
    result = run_pine_strategy(pine_file, symbol, timeframe)
    return result, extract_signal(result)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pinets_runner.py <pine_file> [symbol] [timeframe]")
        print("  Runs a TradingView Pine Script strategy on live MT5 data.")
        sys.exit(0)
    pine_file = sys.argv[1]
    symbol = sys.argv[2] if len(sys.argv) > 2 else "XAUUSD"
    timeframe = sys.argv[3] if len(sys.argv) > 3 else "H1"
    result, signal = run_and_signal(pine_file, symbol, timeframe)
    if result.get("ok"):
        print(f"OK: {result['bars']} bars, {len(result.get('plots', {}))} plots, "
              f"{len(result.get('trades', []))} trades, close={result.get('last_close')}")
        if signal:
            print(f"SIGNAL: {signal['action']} @ {signal['price']} SL={signal['sl']} TP={signal['tp']}")
        else:
            print("No actionable signal on the last bar.")
    else:
        print(f"ERROR: {result.get('error')}")

## Links from
- [[pine_runner]]
- [[signal_watcher]]
- [[test_pine_runner]]
- [[test_strategy_registry]]

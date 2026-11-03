---
slug: test_pine_runner
type: note
graph: gitnexus
---

"""Acceptance tests for pine_runner.py — 4 tests, exit 0 = all pass.

The host has no live MetaTrader 5 terminal, so MetaTrader5 is stubbed before
importing pinets_runner/pine_runner and run_pine_strategy is monkeypatched in
the strategy test; no bridge, node, or MT5 call ever fires here. record_signal
writes to a scratch copy of signals.db so the live ledger is never touched.
"""
import json
import os
import sqlite3
import sys
import sysconfig
import tempfile
import types
from pathlib import Path

BASE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = Path.home() / ".hermes/cache/scratch"
SCRATCH.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, BASE)

# --- stub MetaTrader5 so pinets_runner imports without a live terminal -------
if "MetaTrader5" not in sys.modules:
    _mt5 = types.ModuleType("MetaTrader5")
    for _name, _val in (
        ("TIMEFRAME_M1", 1), ("TIMEFRAME_M5", 5), ("TIMEFRAME_M15", 15),
        ("TIMEFRAME_M30", 30), ("TIMEFRAME_H1", 60), ("TIMEFRAME_H4", 240),
        ("TIMEFRAME_D1", "D"), ("TIMEFRAME_W1", "W"), ("TIMEFRAME_MN1", "MN"),
    ):
        setattr(_mt5, _name, _val)
    _mt5.terminal_info = lambda: None
    _mt5.initialize = lambda: False
    _mt5.shutdown = lambda: None
    sys.modules["MetaTrader5"] = _mt5

import pinets_runner  # noqa: E402
import pine_runner  # noqa: E402

fails = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global fails
    print(("PASS" if ok else "FAIL"), name, detail)
    if not ok:
        fails += 1


# ------------------------------------------------------------------ test 1 #
cfg = json.load(open(os.path.join(BASE, "config.json"), encoding="utf-8"))
block = cfg.get("pine_strategies")
check(
    "config block loads",
    isinstance(block, list),
    f"pine_strategies={block!r} ({len(block) if isinstance(block, list) else 'n/a'} entries)",
)
check(
    "paper_mode config flag present",
    "paper_mode" in cfg and cfg["paper_mode"] is True,
    f"paper_mode={cfg.get('paper_mode')!r}",
)

# ------------------------------------------------------------------ test 2 #
reg = pine_runner.load_strategy_config()
check("registry loads", isinstance(reg, list))
check(
    "registry entries well-formed (empty OK)",
    all(
        isinstance(e, dict)
        and e.get("name")
        and (os.path.exists(os.path.join(BASE, e["path"])) if e.get("path") else True)
        and e.get("symbol")
        and e.get("timeframe")
        for e in reg
    ),
    f"registry={reg!r}",
)

# ------------------------------------------------------------------ test 3 #
pine_file = os.path.join(BASE, "strategies", "ema_cross.pine")
captured: dict[str, object] = {}

orig_run = pinets_runner.run_pine_strategy


def fake_run(pine_file_arg, symbol="XAUUSD", timeframe="H1", count=500):
    captured["file"] = pine_file_arg
    captured["symbol"] = symbol
    captured["timeframe"] = timeframe
    return {
        "ok": True,
        "latest_signal": {
            "type": "long",
            "price": 2650.5,
            "sl": 2640.0,
            "tp": 2660.0,
            "time": "2026-10-16T00:00:00Z",
        },
    }


pinets_runner.run_pine_strategy = fake_run
try:
    sig = pine_runner.run_strategy("ema_cross")
finally:
    pinets_runner.run_pine_strategy = orig_run

check("run_strategy returns dict", isinstance(sig, dict))
check("run_strategy name carried over", sig.get("name") == "ema_cross", f"name={sig.get('name')!r}")
check("run_strategy ok=True", sig.get("ok") is True, f"ok={sig.get('ok')!r} error={sig.get('error')!r}")
check("run_strategy latest_signal structure", sig.get("action") == "buy"
      and sig.get("price") == 2650.5 and sig.get("sl") == 2640.0 and sig.get("tp") == 2660.0,
      f"{sig!r}")
check("run_strategy forwarded ema_cross.pine to bridge",
      str(captured.get("file")).endswith(os.path.join("strategies", "ema_cross.pine"))
      and captured.get("symbol") == "XAUUSD" and captured.get("timeframe") == "H1",
      f"captured={captured!r}")

# ------------------------------------------------------------------ test 4 #
_fd, scratch_db = tempfile.mkstemp(suffix=".db", prefix="pine_runner_test_", dir=SCRATCH)
os.close(_fd)
pine_runner.DB = scratch_db

test_signal = {
    "name": "ema_cross",
    "action": "buy",
    "symbol": "XAUUSD",
    "price": 2650.5,
    "sl": 2640.0,
    "tp": 2660.0,
    "reason": "pineTS strategy signal at 2026-10-16T00:00:00Z",
    "ts": "2026-10-16T00:00:00Z",
}
msg_id = pine_runner.record_signal(test_signal)

con = sqlite3.connect(scratch_db, timeout=5)
row = con.execute(
    "SELECT msg_id, status, side, symbol, entry, detail FROM trades WHERE msg_id = ?",
    (msg_id,),
).fetchone()
con.close()
os.unlink(scratch_db)

check("record_signal writes pine_signal row",
      row is not None and row[1] == "pine_signal" and row[2] == "buy"
      and row[3] == "XAUUSD" and row[4] == "2650.5",
      f"row={row!r}")
check("msg_id format pine_<name>_<ts>",
      isinstance(msg_id, str) and msg_id.startswith("pine_ema_cross_"), f"msg_id={msg_id!r}")

check("dry run: no MT5 order path (executor never imported)",
      "executor" not in sys.modules
      and not hasattr(sys.modules["MetaTrader5"], "order_send")
      and not hasattr(sys.modules["MetaTrader5"], "position_close"),
      "pine_runner imports only pinets_runner + stdlib; record_signal is a pure INSERT")

# ------------------------------------------------------------------ summary #
if __name__ == "__main__":

    print()
    if fails:
        print(f"{fails} test(s) FAILED")
        sys.exit(1)
    print("All 4 tests passed — dry run, no MT5 order.")
    sys.exit(0)


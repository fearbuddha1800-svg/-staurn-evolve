"""scalp360 integration status: reports which scalp360 subsystems are wired
into the live signal-relay, checked against the REAL signals.db and the real
package modules (no stubs).

Checks:
  1. bridge loads          import scalp360_bridge + make_bridge(); the bridge
                           runs its idempotent _ensure_schema() pass over
                           signals.db (intents, positions, event_claims,
                           neural_labels + cursors/update_claims tables)
  2. lineage tables exist  intents, positions, event_claims, neural_labels
                           present in signals.db alongside the trades ledger
  3. gold parser works     zone-aware XAUHQ parse reproduces the msg-2243
                           regression anchor: ENTRY 4184/90 -> zone
                           (4184.0, 4190.0), TP 4145/4120 -> zone kept
  4. risk governor         RiskGovernor instantiates (both fresh and via the
                           bridge) and answers a pure size() probe
  5. cursor store          CursorStore initializes on signals.db and reads
                           back a fresh source cursor
  6. daemon wiring         `import daemon` loads with the new bridge init and
                           daemon._bridge is live (SKIPped when MetaTrader5 is
                           unavailable, e.g. under a non-relay interpreter)

Exit 0 only when every check PASSes (a SKIP is not a PASS). Run with the relay
interpreter (miniconda3) so check 6 executes: python integration_status.py
"""
import os
import sqlite3
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)
DB = os.path.join(BASE, "signals.db")

results = []  # (name, status, detail); status in {PASS, FAIL, SKIP}
bridge = None


def record(name, fn):
    try:
        detail = fn()
        results.append((name, "PASS", detail))
    except Exception as e:  # noqa: BLE001
        results.append((name, "FAIL", f"{type(e).__name__}: {e}"))


# 1. bridge loads ------------------------------------------------------------
def _bridge_loads():
    global bridge
    import scalp360_bridge
    bridge = scalp360_bridge.make_bridge()  # idempotent _ensure_schema() pass
    return (f"Scalp360Bridge OK on {os.path.basename(DB)} "
            f"(risk {bridge.risk.cfg.risk_per_trade_pct}%/trade, "
            f"max {bridge.risk.cfg.max_concurrent} concurrent)")


record("bridge loads", _bridge_loads)


# 2. lineage tables exist ----------------------------------------------------
def _lineage_tables():
    need = ("intents", "positions", "event_claims", "neural_labels")
    con = sqlite3.connect(DB)
    try:
        have = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()
    missing = [t for t in need if t not in have]
    assert not missing, f"missing {missing}; signals.db has {sorted(have)}"
    assert "trades" in have, "existing trades ledger missing?!"
    return f"intents, positions, event_claims, neural_labels present alongside trades"


record("lineage tables exist", _lineage_tables)


# 3. gold parser works -------------------------------------------------------
def _gold_parser():
    from scalp360.gold_parser import parse_gold
    # msg-2243 (2026-10-14 XAUHQ export) regression anchor
    sample = ("🛡🟡 XAUUSD\n"
              "SELL NOW\n"
              "ENTRY: 4184/90\n"
              "STOP LOSS: 4195\n"
              "TP1 ->4145/4120")
    g = parse_gold(sample)
    assert g is not None, "parse_gold abstained on the anchor sample"
    assert (g.entry.low, g.entry.high) == (4184.0, 4190.0), f"entry zone {g.entry}"
    assert g.side == "SELL" and g.stop == 4195.0, f"side/stop {g.side}/{g.stop}"
    assert g.targets and g.targets[0][0] == "TP1", f"targets {g.targets}"
    tz = g.targets[0][1]
    assert (tz.low, tz.high) == (4120.0, 4145.0), f"TP zone {tz}"
    return (f"anchor OK: entry zone ({g.entry.low:g}, {g.entry.high:g}) not collapsed, "
            f"TP zone ({tz.low:g}, {tz.high:g}) preserved")


record("gold parser works", _gold_parser)


# 4. risk governor instantiates ----------------------------------------------
def _risk_governor():
    from scalp360.risk import RiskGovernor, RiskConfig, Verdict
    assert bridge is not None, "bridge not loaded (check 1 failed)"
    assert isinstance(bridge.risk, RiskGovernor), "bridge.risk is not a RiskGovernor"
    gov = RiskGovernor(RiskConfig(risk_per_trade_pct=0.5))  # fresh instantiation
    d = gov.size(balance=10_000.0, stop_distance_price=5.0,
                 value_per_lot_per_point=100.0, notional_per_lot=100_000.0)
    assert d.verdict is Verdict.APPROVE and d.quantity > 0, f"size() probe: {d.reason}"
    return (f"instantiates (fresh + via bridge); size() probe approves "
            f"{d.quantity:g} lots, risk {d.risk_amount:.2f}")


record("risk governor instantiates", _risk_governor)


# 5. cursor store initializes --------------------------------------------------
def _cursor_store():
    from scalp360.cursor import CursorStore
    assert bridge is not None, "bridge not loaded (check 1 failed)"
    assert isinstance(bridge.cursors, CursorStore), "bridge.cursors is not a CursorStore"
    con = sqlite3.connect(DB)
    try:
        have = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        con.close()
    assert "cursors" in have, "cursors table missing from signals.db"
    last = bridge.cursor_last("integration-probe")  # read-only probe
    assert last == 0, f"unexpected cursor for fresh probe source: {last}"
    return "CursorStore live on signals.db (cursors table present, fresh read OK)"


record("cursor store initializes", _cursor_store)


# 6. daemon wiring (the actual edits) ------------------------------------------
def _daemon_wiring():
    import daemon  # executes the new top-level bridge init
    assert getattr(daemon, "_bridge", None) is not None, "daemon._bridge is None"
    probe = daemon._bridge.parse_signal(
        "SELL NOW\nENTRY: 4184/90\nSTOP LOSS: 4195\nTP1 ->4145/4120",
        "integration-probe", 0)
    assert probe.kind.name == "NEW_ENTRY", f"unexpected kind {probe.kind}"
    assert hasattr(daemon, "_s360_log"), "daemon._s360_log helper missing"
    return ("import daemon OK; _bridge live; _s360_log present; "
            "zone-aware parse returns NEW_ENTRY")


try:
    record("daemon wiring", _daemon_wiring)
except Exception as e:  # noqa: BLE001
    if "MetaTrader5" in str(e):
        results.append(("daemon wiring", "SKIP",
                         "MetaTrader5 unavailable under this interpreter "
                         "(run with the relay interpreter, miniconda3)"))
    else:
        results.append(("daemon wiring", "FAIL", f"{type(e).__name__}: {e}"))


# ---- report ------------------------------------------------------------------
print(f"scalp360 integration status ({time.strftime('%Y-%m-%d %H:%M:%S')})")
for name, st, detail in results:
    print(f"  [{st}] {name}: {detail}")
n_pass = sum(1 for _, s, _ in results if s == "PASS")
n_skip = sum(1 for _, s, _ in results if s == "SKIP")
n_fail = sum(1 for _, s, _ in results if s == "FAIL")
print()
print(f"SCALP360 INTEGRATION: {n_pass}/{len(results)} wired"
      + (f" | {n_skip} skipped" if n_skip else "")
      + (f" | {n_fail} FAILED" if n_fail else ""))
sys.exit(0 if n_fail == 0 and n_skip == 0 else 1)

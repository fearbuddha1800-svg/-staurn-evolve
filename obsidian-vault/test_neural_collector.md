---
slug: test_neural_collector
type: note
graph: gitnexus
---

"""Smoke tests for neural_label_collector.py - the neural training label
pipeline. Uses a throwaway temp DB so the live signals.db is never touched.
Run: PYTHONPATH= python test_neural_collector.py
"""
import os
import sqlite3
import sys
import tempfile
import types
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
SCRATCH = Path.home() / ".hermes/cache/scratch"
SCRATCH.mkdir(parents=True, exist_ok=True)
# Fail closed offline: never import or attach the real terminal/event database.
sys.modules["MetaTrader5"] = types.ModuleType("MetaTrader5")
_events = types.ModuleType("event_bus")
_events.bus = types.SimpleNamespace(publish=lambda *a, **k: None)
sys.modules["event_bus"] = _events

import neural_label_collector as nlc  # noqa: E402
nlc._mt5_mod = lambda: None

PASS = 0
FAIL = 0


def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"PASS {name}" + (f" - {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"FAIL {name}" + (f" - {detail}" if detail else ""))


def _fresh_db():
    fd, path = tempfile.mkstemp(suffix=".db", prefix="neural_test_", dir=SCRATCH)
    os.close(fd)
    os.unlink(path)  # let the collector create the schema fresh
    return path


def test_record_entry():
    db = _fresh_db()
    try:
        rid = nlc.record_entry(
            ticket=111001, symbol="XAUUSD", side="buy", entry_price=4150.0,
            sl=4140.0, tp=None, channel_id=-1002165799093, magic=20261014,
            source="test", db=db)
        check("record_entry returns a row id", rid is not None, f"id={rid}")
        con = sqlite3.connect(db)
        n = con.execute("SELECT COUNT(*) FROM neural_labels").fetchone()[0]
        row = con.execute("SELECT outcome, features FROM neural_labels LIMIT 1").fetchone()
        con.close()
        check("record_entry inserts exactly one label", n == 1, f"rows={n}")
        check("record_entry leaves outcome NULL", row and row[0] is None, f"outcome={row[0] if row else 'no row'}")
        check("record_entry stores features JSON", bool(row and row[1]), "features present")
        # idempotent per ticket
        rid2 = nlc.record_entry(
            ticket=111001, symbol="XAUUSD", side="buy", entry_price=4150.0,
            sl=4140.0, tp=None, channel_id=-1002165799093, magic=20261014,
            source="test", db=db)
        check("record_entry is idempotent per ticket", rid2 == rid, f"{rid}=={rid2}")
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


def test_record_close():
    db = _fresh_db()
    try:
        nlc.record_entry(ticket=222002, symbol="EURUSD", side="sell", entry_price=1.12,
                         sl=1.125, tp=None, channel_id=-1001713690419, magic=20261014,
                         source="test", db=db)
        ok = nlc.record_close(222002, profit_r=1.5, db=db)
        con = sqlite3.connect(db)
        row = con.execute("SELECT outcome FROM neural_labels LIMIT 1").fetchone()
        con.close()
        check("record_close returns truthy", bool(ok), f"ok={ok}")
        check("record_close sets outcome=1 on a win", row and row[0] == 1, f"outcome={row[0] if row else 'none'}")

        nlc.record_entry(ticket=222003, symbol="EURUSD", side="sell", entry_price=1.12,
                         sl=1.125, tp=None, channel_id=-1001713690419, magic=20261014,
                         source="test", db=db)
        nlc.record_close(222003, profit_r=-1.0, db=db)
        con = sqlite3.connect(db)
        row2 = con.execute("SELECT outcome FROM neural_labels ORDER BY id DESC LIMIT 1").fetchone()
        con.close()
        check("record_close sets outcome=0 on a loss", row2 and row2[0] == 0, f"outcome={row2[0] if row2 else 'none'}")
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


def test_get_training_data():
    db = _fresh_db()
    try:
        for i in range(5):
            t = 333000 + i
            nlc.record_entry(ticket=t, symbol="XAUUSD", side="buy", entry_price=4150.0 + i,
                             sl=4140.0 + i, tp=None, channel_id=-1002165799093,
                             magic=20261014, source="test", db=db)
            nlc.record_close(t, profit_r=1.0 if i % 2 == 0 else -1.0, db=db)
        data = nlc.get_training_data(db=db)
        check("get_training_data returns a tuple", isinstance(data, tuple), f"type={type(data).__name__}")
        X, y = data[0], data[1]
        check("X and y have equal length", len(X) == len(y), f"X={len(X)} y={len(y)}")
        check("X rows are feature vectors", len(X) == 0 or hasattr(X[0], "__len__"), "vectors")
        check("y values are 0/1", all(v in (0, 1) for v in y), f"y={list(y)[:6]}")
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


def test_evaluation_rejects_small_sample():
    db = _fresh_db()
    try:
        for i in range(3):
            t = 444000 + i
            nlc.record_entry(ticket=t, symbol="XAUUSD", side="buy", entry_price=4150.0,
                             sl=4140.0, tp=None, channel_id=-1002165799093,
                             magic=20261014, source="test", db=db)
            nlc.record_close(t, profit_r=1.0, db=db)
        res = nlc.run_evaluation(db_path=db)
        # must NOT promote on 3 labels (needs >= 300)
        decision = res.decision
        check("evaluation refuses to promote on <300 labels",
              decision.startswith("REJECT: insufficient labels") and res.n_test == 0,
              f"decision={decision}")
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


if __name__ == "__main__":
    test_record_entry()
    test_record_close()
    test_get_training_data()
    test_evaluation_rejects_small_sample()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


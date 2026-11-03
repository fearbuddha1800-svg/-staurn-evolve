---
slug: test_label_health
type: note
graph: gitnexus
---

"""Tests for label_health.py — the neural label pipeline health checker.

Uses a throwaway temp DB so the live signals.db is never touched.
Run: PYTHONPATH= python test_label_health.py
"""
import json
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
# NOTE: these stubs are installed only long enough to import our own modules, then
# restored. Leaving them in sys.modules would silently poison any other test file
# that later imports the real event_bus (it would get this stub and lose EventBus).
_SAVED_MODULES = {_n: sys.modules.get(_n) for _n in ("MetaTrader5", "event_bus")}
sys.modules["MetaTrader5"] = types.ModuleType("MetaTrader5")
_events = types.ModuleType("event_bus")
_events.bus = types.SimpleNamespace(publish=lambda *a, **k: None)
sys.modules["event_bus"] = _events

import label_health as lh  # noqa: E402
import neural_label_collector as nlc  # noqa: E402

for _n, _mod in _SAVED_MODULES.items():
    if _mod is None:
        sys.modules.pop(_n, None)
    else:
        sys.modules[_n] = _mod
del _SAVED_MODULES

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
    fd, path = tempfile.mkstemp(suffix=".db", prefix="label_health_", dir=SCRATCH)
    os.close(fd)
    os.unlink(path)
    return path


def test_missing_db_reports_unknown():
    report = lh.build_report(db_path="/nonexistent/path/fake.db")
    check("missing DB: status is db_unavailable",
          report["status"] == "db_unavailable", f"status={report['status']}")
    check("missing DB: label_counts is None",
          report["label_counts"] is None)
    check("missing DB: gate distance is None",
          report["gate"]["distance_to_gate"] is None)
    check("missing DB: db_exists is False",
          report["db_exists"] is False)


def test_empty_db():
    db = _fresh_db()
    try:
        con = sqlite3.connect(db)
        con.execute(lh.NEURAL_LABELS_DDL)
        con.execute(lh.MAP_DDL)
        con.commit()
        con.close()
        report = lh.build_report(db_path=db)
        check("empty DB: status is empty", report["status"] == "empty")
        check("empty DB: total=0", report["label_counts"]["total"] == 0)
        check("empty DB: complete=0", report["label_counts"]["complete"] == 0)
        check("empty DB: gate distance=300",
              report["gate"]["distance_to_gate"] == 300)
        check("empty DB: gate not met", report["gate"]["gate_met"] is False)
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


def test_label_counts_accurate():
    db = _fresh_db()
    try:
        for i in range(5):
            nlc.record_entry(ticket=1000 + i, symbol="XAUUSD", side="buy",
                             entry_price=4150.0 + i, sl=4140.0 + i, tp=None,
                             channel_id=-1002165799093, magic=20261014,
                             source="test", db=db)
            if i < 3:
                nlc.record_close(1000 + i, profit_r=1.0 if i % 2 == 0 else -1.0, db=db)
        report = lh.build_report(db_path=db)
        lc = report["label_counts"]
        check("counts: total=5", lc["total"] == 5, f"total={lc['total']}")
        check("counts: complete=3", lc["complete"] == 3, f"complete={lc['complete']}")
        check("counts: pending=2", lc["pending"] == 2, f"pending={lc['pending']}")
        check("counts: status=accumulating", report["status"] == "accumulating")
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


def test_outcome_distribution():
    db = _fresh_db()
    try:
        for i in range(4):
            t = 2000 + i
            nlc.record_entry(ticket=t, symbol="EURUSD", side="sell",
                             entry_price=1.12, sl=1.125, tp=None,
                             channel_id=-1001713690419, magic=20261014,
                             source="test", db=db)
            nlc.record_close(t, profit_r=1.0 if i < 3 else -1.0, db=db)
        report = lh.build_report(db_path=db)
        od = report["outcome_distribution"]
        check("distribution: 3 wins", od["wins"] == 3, f"wins={od['wins']}")
        check("distribution: 1 loss", od["losses"] == 1, f"losses={od['losses']}")
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


def test_map_consistency_clean():
    db = _fresh_db()
    try:
        for i in range(3):
            t = 3000 + i
            nlc.record_entry(ticket=t, symbol="GBPUSD", side="buy",
                             entry_price=1.25, sl=1.245, tp=None,
                             channel_id=-1001713690419, magic=20261014,
                             source="test", db=db)
        report = lh.build_report(db_path=db)
        mc = report["map_consistency"]
        check("map: 3 rows", mc["map_rows"] == 3, f"rows={mc['map_rows']}")
        check("map: consistent", mc["consistent"] is True)
        check("map: no orphan tickets", len(mc["tickets_without_label"]) == 0)
        check("map: no orphan labels", len(mc["labels_without_ticket"]) == 0)
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


def test_map_orphan_ticket():
    db = _fresh_db()
    try:
        nlc.record_entry(ticket=4001, symbol="XAUUSD", side="buy",
                         entry_price=4150.0, sl=4140.0, tp=None,
                         channel_id=-1002165799093, magic=20261014,
                         source="test", db=db)
        # Manually insert an orphan map entry
        con = sqlite3.connect(db)
        con.execute("INSERT INTO neural_label_map(ticket,label_id,symbol,side,opened_at)"
                    " VALUES(99999, 99999, 'EURUSD', 'buy', 0)")
        con.commit()
        con.close()
        report = lh.build_report(db_path=db)
        mc = report["map_consistency"]
        check("orphan ticket: detected", len(mc["tickets_without_label"]) == 1)
        check("orphan ticket: consistent=False", mc["consistent"] is False)
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


def test_map_orphan_label():
    db = _fresh_db()
    try:
        nlc.record_entry(ticket=5001, symbol="XAUUSD", side="buy",
                         entry_price=4150.0, sl=4140.0, tp=None,
                         channel_id=-1002165799093, magic=20261014,
                         source="test", db=db)
        # Manually insert a label with no map entry
        con = sqlite3.connect(db)
        con.execute("INSERT INTO neural_labels(ts,symbol,side,entry,sl,tp,outcome,features)"
                    " VALUES(0, 'EURUSD', 'buy', 1.12, 1.115, NULL, 1, '{}')")
        con.commit()
        con.close()
        report = lh.build_report(db_path=db)
        mc = report["map_consistency"]
        check("orphan label: detected", len(mc["labels_without_ticket"]) == 1)
        check("orphan label: consistent=False", mc["consistent"] is False)
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


def test_feature_dims_ok():
    db = _fresh_db()
    try:
        for i in range(3):
            t = 6000 + i
            nlc.record_entry(ticket=t, symbol="XAUUSD", side="buy",
                             entry_price=4150.0, sl=4140.0, tp=None,
                             channel_id=-1002165799093, magic=20261014,
                             source="test", db=db)
        report = lh.build_report(db_path=db)
        fd = report["feature_dims"]
        check("dims: 3 checked", fd["checked"] == 3, f"checked={fd['checked']}")
        check("dims: 0 malformed", fd["malformed_count"] == 0)
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


def test_feature_dims_bad_json():
    db = _fresh_db()
    try:
        con = sqlite3.connect(db)
        con.execute(lh.NEURAL_LABELS_DDL)
        con.execute("INSERT INTO neural_labels(ts,symbol,side,entry,sl,tp,outcome,features)"
                    " VALUES(0, 'XAUUSD', 'buy', 1.0, 0.9, NULL, NULL, 'not json{')")
        con.commit()
        con.close()
        report = lh.build_report(db_path=db)
        fd = report["feature_dims"]
        check("bad json: 1 checked", fd["checked"] == 1)
        check("bad json: 1 malformed", fd["malformed_count"] == 1)
        check("bad json: dim=-1", fd["malformed"][0]["dim"] == -1)
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


def test_gate_met():
    db = _fresh_db()
    try:
        con = sqlite3.connect(db)
        con.execute(lh.NEURAL_LABELS_DDL)
        con.execute(lh.MAP_DDL)
        # Insert 300 complete labels directly
        for i in range(300):
            con.execute(
                "INSERT INTO neural_labels(ts,symbol,side,entry,sl,tp,outcome,features)"
                " VALUES(?, 'XAUUSD', 'buy', 4150.0, 4140.0, NULL, ?, '{}')",
                (1792000000.0 + i * 100, i % 2))
        con.commit()
        con.close()
        report = lh.build_report(db_path=db)
        check("gate: 300 complete", report["label_counts"]["complete"] == 300)
        check("gate: gate_met=True", report["gate"]["gate_met"] is True)
        check("gate: distance=0", report["gate"]["distance_to_gate"] == 0)
        check("gate: status=ready", report["status"] == "ready")
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


def test_accumulation_rate():
    db = _fresh_db()
    try:
        con = sqlite3.connect(db)
        con.execute(lh.NEURAL_LABELS_DDL)
        con.execute(lh.MAP_DDL)
        # 10 labels over 5 days
        for i in range(10):
            con.execute(
                "INSERT INTO neural_labels(ts,symbol,side,entry,sl,tp,outcome,features)"
                " VALUES(?, 'XAUUSD', 'buy', 4150.0, 4140.0, NULL, 1, '{}')",
                (1792000000.0 + i * 432000,))  # 5 days apart
        con.commit()
        con.close()
        report = lh.build_report(db_path=db)
        ar = report["accumulation_rate"]
        check("rate: note=ok", ar["note"] == "ok")
        # 10 labels at 5-day intervals: span = 9*5 = 45 days
        check("rate: span_days=45", ar["span_days"] == 45.0, f"span={ar['span_days']}")
        expected_rate = round(10 / 45.0, 3)
        check("rate: labels_per_day", abs(ar["labels_per_day"] - expected_rate) < 0.001,
              f"rate={ar['labels_per_day']} expected={expected_rate}")
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


def test_label_detail_rows():
    db = _fresh_db()
    try:
        nlc.record_entry(ticket=7001, symbol="XAUUSD", side="buy",
                         entry_price=4150.0, sl=4140.0, tp=None,
                         channel_id=-1002165799093, magic=20261014,
                         source="test", db=db)
        nlc.record_close(7001, profit_r=2.0, db=db)
        report = lh.build_report(db_path=db)
        labels = report["labels"]
        check("detail: 1 label", len(labels) == 1)
        check("detail: outcome=1", labels[0]["outcome"] == 1)
        check("detail: profit_r=2.0", labels[0]["profit_r"] == 2.0)
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


def test_json_output():
    db = _fresh_db()
    try:
        nlc.record_entry(ticket=8001, symbol="XAUUSD", side="buy",
                         entry_price=4150.0, sl=4140.0, tp=None,
                         channel_id=-1002165799093, magic=20261014,
                         source="test", db=db)
        report = lh.build_report(db_path=db)
        j = json.dumps(report, default=str)
        parsed = json.loads(j)
        check("json: round-trips", parsed["status"] == report["status"])
        check("json: has gate", "gate" in parsed)
    finally:
        try:
            os.unlink(db)
        except OSError:
            pass


if __name__ == "__main__":
    test_missing_db_reports_unknown()
    test_empty_db()
    test_label_counts_accurate()
    test_outcome_distribution()
    test_map_consistency_clean()
    test_map_orphan_ticket()
    test_map_orphan_label()
    test_feature_dims_ok()
    test_feature_dims_bad_json()
    test_gate_met()
    test_accumulation_rate()
    test_label_detail_rows()
    test_json_output()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)


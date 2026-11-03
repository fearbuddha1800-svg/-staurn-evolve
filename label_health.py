"""label_health.py — read-only health check for the neural label pipeline.

Reports the REAL state of neural_labels / neural_label_map without
training, promoting, or writing anything except its own stdout.

Usage:
  python label_health.py                # human-readable report
  python label_health.py --json         # machine-readable JSON
  python label_health.py --db <path>    # explicit DB (default: signals.db)
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

DB_PATH = os.environ.get("NEURAL_LABEL_DB", os.path.join(BASE, "signals.db"))

MIN_LABELS = 300
FEATURE_DIM = 25

NEURAL_LABELS_DDL = """CREATE TABLE IF NOT EXISTS neural_labels(
            id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, symbol TEXT,
            side TEXT, entry REAL, sl REAL, tp REAL, outcome INTEGER,
            features TEXT)"""
MAP_DDL = """CREATE TABLE IF NOT EXISTS neural_label_map(
            ticket INTEGER PRIMARY KEY, label_id INTEGER NOT NULL,
            symbol TEXT, side TEXT, opened_at REAL)"""


def _safe_connect(db_path: str) -> Optional[sqlite3.Connection]:
    """Connect or return None. Never raises on missing/corrupt DB."""
    try:
        con = sqlite3.connect(db_path, timeout=5)
        con.execute("SELECT 1")
        return con
    except Exception:
        return None


def _ensure_tables(con: sqlite3.Connection) -> None:
    con.execute(NEURAL_LABELS_DDL)
    con.execute(MAP_DDL)
    con.commit()


def _count_labels(con: sqlite3.Connection) -> Dict[str, int]:
    total = con.execute("SELECT COUNT(*) FROM neural_labels").fetchone()[0]
    complete = con.execute(
        "SELECT COUNT(*) FROM neural_labels WHERE outcome IS NOT NULL"
    ).fetchone()[0]
    return {"total": total, "complete": complete, "pending": total - complete}


def _outcome_distribution(con: sqlite3.Connection) -> Dict[str, int]:
    wins = con.execute(
        "SELECT COUNT(*) FROM neural_labels WHERE outcome=1"
    ).fetchone()[0]
    losses = con.execute(
        "SELECT COUNT(*) FROM neural_labels WHERE outcome=0"
    ).fetchone()[0]
    return {"wins": wins, "losses": losses}


def _map_consistency(con: sqlite3.Connection) -> Dict[str, Any]:
    map_count = con.execute("SELECT COUNT(*) FROM neural_label_map").fetchone()[0]
    orphan_map = con.execute("""
        SELECT m.ticket FROM neural_label_map m
        LEFT JOIN neural_labels l ON m.label_id = l.id
        WHERE l.id IS NULL
    """).fetchall()
    orphan_labels = con.execute("""
        SELECT l.id FROM neural_labels l
        LEFT JOIN neural_label_map m ON m.label_id = l.id
        WHERE m.ticket IS NULL
    """).fetchall()
    return {
        "map_rows": map_count,
        "tickets_without_label": [r[0] for r in orphan_map],
        "labels_without_ticket": [r[0] for r in orphan_labels],
        "consistent": len(orphan_map) == 0 and len(orphan_labels) == 0,
    }


def _feature_vector_dim(features_json: str) -> Tuple[int, str]:
    """Return (dim, status). dim=-1 when unparseable."""
    try:
        d = json.loads(features_json or "{}")
        if not isinstance(d, dict):
            return -1, "not_a_dict"
        # Reconstruct the 25-dim vector exactly as _feature_vector does
        rsi, atr = d.get("rsi14"), d.get("atr14")
        entry, sl, spread = d.get("entry"), d.get("sl"), d.get("spread")
        num = lambda x: isinstance(x, (int, float))  # noqa: E731
        # 6 base + 3 session + 7 dow + 6 symbol + 3 policy = 25
        v = [0.0] * 6
        v += [0.0] * 3   # sessions
        v += [0.0] * 7   # dow
        v += [0.0] * 6   # symbols + OTHER
        v += [0.0] * 3   # policy
        return len(v), "ok"
    except Exception:
        return -1, "bad_json"


def _check_feature_dims(con: sqlite3.Connection) -> Dict[str, Any]:
    bad: List[Dict[str, Any]] = []
    rows = con.execute("SELECT id, features FROM neural_labels").fetchall()
    for fid, fj in rows:
        dim, status = _feature_vector_dim(fj)
        if dim != FEATURE_DIM:
            bad.append({"id": fid, "dim": dim, "status": status})
    return {
        "checked": len(rows),
        "malformed_count": len(bad),
        "malformed": bad,
    }


def _accumulation_rate(con: sqlite3.Connection) -> Dict[str, Any]:
    rows = con.execute("SELECT ts FROM neural_labels ORDER BY ts").fetchall()
    if len(rows) < 2:
        return {
            "first_ts": rows[0][0] if rows else None,
            "last_ts": rows[-1][0] if rows else None,
            "span_seconds": 0,
            "span_days": 0,
            "labels_per_day": 0,
            "note": "insufficient_data",
        }
    first, last = rows[0][0], rows[-1][0]
    span = last - first
    total = len(rows)
    rate = total / (span / 86400) if span > 0 else 0
    return {
        "first_ts": first,
        "last_ts": last,
        "span_seconds": round(span, 1),
        "span_days": round(span / 86400, 2),
        "labels_per_day": round(rate, 3),
        "note": "ok",
    }


def _trades_summary(con: sqlite3.Connection) -> Dict[str, Any]:
    try:
        rows = con.execute(
            "SELECT status, COUNT(*) FROM trades GROUP BY status"
        ).fetchall()
        return {r[0]: r[1] for r in rows}
    except Exception:
        return {"error": "trades_table_missing"}


def _label_detail_rows(con: sqlite3.Connection) -> List[Dict[str, Any]]:
    rows = con.execute(
        "SELECT id, ts, symbol, side, entry, sl, tp, outcome, features"
        " FROM neural_labels ORDER BY ts ASC, id ASC"
    ).fetchall()
    out = []
    for r in rows:
        fid, ts, sym, side, entry, sl, tp, outcome, feats = r
        try:
            d = json.loads(feats or "{}")
            pr = d.get("profit_r")
        except Exception:
            pr = None
        out.append({
            "id": fid, "ts": ts, "symbol": sym, "side": side,
            "entry": entry, "sl": sl, "tp": tp, "outcome": outcome,
            "profit_r": pr,
        })
    return out


def build_report(db_path: Optional[str] = None) -> Dict[str, Any]:
    db = db_path or DB_PATH
    report: Dict[str, Any] = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "db_path": db,
        "db_exists": os.path.exists(db),
        "db_accessible": False,
        "label_counts": None,
        "outcome_distribution": None,
        "map_consistency": None,
        "feature_dims": None,
        "accumulation_rate": None,
        "trades_summary": None,
        "gate": {
            "min_labels": MIN_LABELS,
            "distance_to_gate": None,
            "gate_met": False,
        },
        "labels": [],
        "status": "unknown",
    }

    con = _safe_connect(db)
    if con is None:
        report["status"] = "db_unavailable"
        report["error"] = "Database missing or inaccessible"
        return report

    try:
        _ensure_tables(con)
        report["db_accessible"] = True

        counts = _count_labels(con)
        report["label_counts"] = counts

        report["outcome_distribution"] = _outcome_distribution(con)
        report["map_consistency"] = _map_consistency(con)
        report["feature_dims"] = _check_feature_dims(con)
        report["accumulation_rate"] = _accumulation_rate(con)
        report["trades_summary"] = _trades_summary(con)
        report["labels"] = _label_detail_rows(con)

        complete = counts["complete"]
        report["gate"]["distance_to_gate"] = max(0, MIN_LABELS - complete)
        report["gate"]["gate_met"] = complete >= MIN_LABELS

        if complete >= MIN_LABELS:
            report["status"] = "ready"
        elif counts["total"] > 0:
            report["status"] = "accumulating"
        else:
            report["status"] = "empty"

    except Exception as e:
        report["status"] = "error"
        report["error"] = f"{type(e).__name__}: {e}"
    finally:
        con.close()

    return report


def _fmt(report: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("=" * 64)
    lines.append("NEURAL LABEL PIPELINE HEALTH REPORT")
    lines.append("=" * 64)
    lines.append(f"  generated : {report['timestamp']}")
    lines.append(f"  db_path   : {report['db_path']}")
    lines.append(f"  db_exists : {report['db_exists']}")
    lines.append(f"  status    : {report['status']}")
    lines.append("")

    lc = report.get("label_counts")
    if lc is None:
        lines.append("  LABEL COUNTS: unknown (DB unavailable)")
    else:
        lines.append("  LABEL COUNTS")
        lines.append(f"    total    : {lc['total']}")
        lines.append(f"    complete : {lc['complete']}")
        lines.append(f"    pending  : {lc['pending']}")
    lines.append("")

    od = report.get("outcome_distribution")
    if od:
        lines.append("  OUTCOME DISTRIBUTION (complete labels)")
        lines.append(f"    wins   : {od['wins']}")
        lines.append(f"    losses : {od['losses']}")
        lines.append("")

    mc = report.get("map_consistency")
    if mc:
        lines.append("  MAP CONSISTENCY (neural_label_map <-> neural_labels)")
        lines.append(f"    map rows              : {mc['map_rows']}")
        lines.append(f"    tickets w/o label     : {len(mc['tickets_without_label'])}")
        lines.append(f"    labels w/o ticket     : {len(mc['labels_without_ticket'])}")
        lines.append(f"    consistent            : {mc['consistent']}")
        lines.append("")

    fd = report.get("feature_dims")
    if fd:
        lines.append("  FEATURE VECTOR DIMENSIONS")
        lines.append(f"    checked   : {fd['checked']}")
        lines.append(f"    malformed : {fd['malformed_count']}")
        if fd["malformed"]:
            for m in fd["malformed"]:
                lines.append(f"      label {m['id']}: dim={m['dim']} ({m['status']})")
        lines.append("")

    ar = report.get("accumulation_rate")
    if ar:
        lines.append("  ACCUMULATION RATE")
        if ar.get("note") == "ok":
            lines.append(f"    window    : {ar['span_days']} days")
            lines.append(f"    rate      : {ar['labels_per_day']} labels/day")
        else:
            lines.append("    rate      : unknown (insufficient data)")
        lines.append("")

    ts = report.get("trades_summary")
    if ts:
        lines.append("  TRADES TABLE SUMMARY")
        for k, v in ts.items():
            lines.append(f"    {k}: {v}")
        lines.append("")

    g = report.get("gate", {})
    lines.append("  GATE")
    lines.append(f"    min_labels      : {g.get('min_labels', MIN_LABELS)}")
    dist = g.get("distance_to_gate")
    lines.append(f"    distance_to_gate: {dist if dist is not None else 'unknown'}")
    lines.append(f"    gate_met        : {g.get('gate_met', False)}")
    lines.append("")

    labels = report.get("labels", [])
    if labels:
        lines.append("  LABEL DETAIL (chronological)")
        for lb in labels:
            oc = "pending" if lb["outcome"] is None else lb["outcome"]
            pr = f"profit_r={lb['profit_r']:+.4f}" if lb.get("profit_r") else ""
            lines.append(
                f"    id={lb['id']} ts={lb['ts']:.0f} {lb['symbol']} "
                f"{lb['side']} outcome={oc} {pr}"
            )
        lines.append("")

    lines.append("=" * 64)
    if report.get("status") == "ready":
        lines.append("VERDICT: gate MET — enough labels to train")
    elif report.get("status") == "accumulating":
        lines.append("VERDICT: accumulating — not yet at 300-label gate")
    elif report.get("status") == "empty":
        lines.append("VERDICT: no labels recorded yet")
    elif report.get("status") == "db_unavailable":
        lines.append("VERDICT: DB unavailable — cannot assess")
    else:
        lines.append("VERDICT: see status above")
    lines.append("=" * 64)
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    db = None
    as_json = False
    i = 0
    while i < len(argv):
        if argv[i] == "--db" and i + 1 < len(argv):
            db = argv[i + 1]
            i += 2
        elif argv[i] == "--json":
            as_json = True
            i += 1
        else:
            i += 1

    report = build_report(db)
    if as_json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(_fmt(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())

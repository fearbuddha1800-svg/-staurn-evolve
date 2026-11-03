"""Offline, read-only signal-source evidence report; never approves or sends trades.

python source_intelligence.py --db signals.db --output agent-reports/source-intelligence.json
Receipt freshness is not market quote freshness. Parse yield is not profitability.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sqlite3

from signal_source_audit import audit


def utc_stamp(value):
    if not isinstance(value, str):
        raise ValueError('timestamp must be text')
    stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if stamp.utcoffset() is None:
        raise ValueError('timezone required')
    return stamp.astimezone(timezone.utc)


def read_snapshot(path):
    """Single SQLite read transaction; missing optional labels stay unknown."""
    uri = Path(path).resolve().as_uri() + '?mode=ro'
    with closing(sqlite3.connect(uri, uri=True, timeout=10)) as con:
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA query_only=ON')
        con.execute('BEGIN')
        rows = [dict(r) for r in con.execute(
            "SELECT ts,source,payload FROM events WHERE type='signal_received' ORDER BY ts")]
        tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        labels = None
        if 'neural_labels' in tables:
            columns = {r[1] for r in con.execute('PRAGMA table_info(neural_labels)')}
            if 'outcome' in columns:
                outcomes = [r[0] for r in con.execute('SELECT outcome FROM neural_labels')]
                labels = {'total': len(outcomes), 'finite_outcomes': sum(
                    isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)
                    for x in outcomes)}
        return rows, labels


def build_report(rows, *, now, labels=None):
    if now.utcoffset() is None:
        raise ValueError('now must be timezone-aware')
    now = now.astimezone(timezone.utc)
    clean = []
    invalid = future = missing_identity = 0
    for row in rows:
        try:
            stamp = utc_stamp(row['ts'])
            if stamp > now:
                future += 1
                continue
            source = row['source']
            if not isinstance(source, str) or not source.strip():
                raise ValueError('source required')
            payload = row['payload']
            if isinstance(payload, str):
                payload = json.loads(payload)
            if not isinstance(payload, dict):
                raise ValueError('payload must be object')
            payload = dict(payload)
            parsed = payload.get('parsed')
            if parsed is not None:
                if not isinstance(parsed, dict):
                    raise ValueError('parsed must be an object')
                for flag in ('is_signal', 'parse_ok'):
                    if flag in parsed and not isinstance(parsed[flag], bool):
                        raise ValueError('parsed flags must be booleans')
                if 'order_type' in parsed and not isinstance(parsed['order_type'], str):
                    raise ValueError('order_type must be text')
            mid = payload.get('msg_id')
            if isinstance(mid, int) and not isinstance(mid, bool):
                mid = str(mid)
            if not isinstance(mid, str) or not mid:
                missing_identity += 1
                continue
            payload['msg_id'] = mid
            clean.append({'ts': stamp.isoformat(), 'source': source, 'payload': payload})
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError):
            invalid += 1
    base = audit(clean)
    by_source = defaultdict(list)
    seen = set()
    for row in sorted(clean, key=lambda r: utc_stamp(r['ts'])):
        key = (row['source'], row['payload']['msg_id'])
        if key in seen:
            continue
        seen.add(key)
        by_source[row['source']].append(row)
    sources = []
    for source, counts in base['sources'].items():
        entries = by_source[source]
        last = max(utc_stamp(r['ts']) for r in entries)
        age_s = (now - last).total_seconds()
        ocr = Counter()
        ai = Counter()
        for row in entries:
            payload = row['payload']
            parsed = payload.get('parsed')
            usable = (isinstance(parsed, dict) and parsed.get('is_signal') is True
                      and parsed.get('parse_ok') is True)
            if payload.get('via_ocr') is True:
                ocr['messages'] += 1
                ocr['parsed_candidates'] += int(usable)
            if payload.get('used_ai') is True:
                ai['messages'] += 1
                ai['parsed_candidates'] += int(usable)
        comparable = counts.get('geometry_comparable', 0)
        stale = age_s > 86400  # Observation health only; not an execution TTL.
        sources.append({
            'source': source, 'last_received_at': last.isoformat(),
            'receipt_age_hours': round(age_s / 3600, 3),
            'observation_state': 'stale_receipts' if stale else 'recent_receipts',
            'counts': counts,
            'candidate_parse_yield': counts.get('parsed_candidates', 0) / counts['messages'],
            'cross_source_echo_fraction_of_comparable': (
                counts.get('cross_source_echo', 0) / comparable if comparable else None),
            'ocr': dict(ocr), 'ai_extraction': dict(ai),
            'profitability': 'unknown_no_attributed_cost_adjusted_outcomes',
            'live_entry_approved': False,
        })
    sources.sort(key=lambda s: (-s['counts']['messages'], s['source']))
    return {
        'generated_at': now.isoformat(), 'mode': 'read_only_research',
        'scope': base['scope'], 'stale_receipt_threshold_hours': 24,
        'raw_receipts': len(rows), 'invalid_rows': invalid, 'future_rows_quarantined': future,
        'missing_identity_quarantined': missing_identity,
        'unique_messages': base['unique_messages'], 'source_count': len(sources),
        'all_sources_stale': all(s['observation_state'] == 'stale_receipts' for s in sources)
            if sources else None,
        'global_labels': labels,
        'training_readiness': 'not_evaluated_requires_feature_and_chronological_validation',
        'sources': sources, 'duplicate_evidence': base['echoes'],
        'limitations': base['limitations'] + [
            'Not complete channel history; no receipt does not prove a channel stopped posting.',
            'Repeated message identities use the first receipt; edits need a separate version ledger.',
            'used_ai records extraction use, not provider availability or correctness.',
            'No source-to-realized-R linkage is established by this report.',
            'Global label counts do not establish training eligibility.',
            '24-hour receipt health is not an entry TTL or a fresh-market-data check.',
            'No channel promotion, subscriptions, config changes or broker operations.',
        ],
    }


def markdown(report):
    lines = ['# EVOLVE — Signal Source Evidence', '',
             f"Generated: {report['generated_at']}", '',
             f"Observed {report['raw_receipts']} receipts; {report['unique_messages']} unique messages; "
             f"{report['source_count']} sources. Scope: stored receipts only.", '',
             '**Parse yield is not win rate. No source is approved for live entries.**', '',
             '| Source | Unique | Parsed candidates | Review | Comparable geometry | Cross-source echoes | Receipt age (hours) |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for source in report['sources']:
        c = source['counts']
        name = source['source'].replace('|', '\\|').replace('\n', ' ').replace('\r', ' ')
        lines.append(f"| {name} | {c['messages']} | {c.get('parsed_candidates', 0)} | "
                     f"{c.get('needs_review', 0)} | {c.get('geometry_comparable', 0)} | "
                     f"{c.get('cross_source_echo', 0)} | {source['receipt_age_hours']} |")
    lines += ['', '## Evidence limits', ''] + ['- ' + x for x in report['limitations']]
    lines += ['', '## Learning evidence', '', json.dumps(report['global_labels']),
              '', report['training_readiness'], '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    target = Path(args.output).resolve()
    db = Path(args.db).resolve()
    if target.suffix.lower() != '.json' or db in (target, target.with_suffix('.md')):
        parser.error('output must be a .json report, not the input database')
    rows, labels = read_snapshot(db)
    report = build_report(rows, now=datetime.now(timezone.utc), labels=labels)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    target.with_suffix('.md').write_text(markdown(report), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('generated_at', 'raw_receipts', 'unique_messages',
        'source_count', 'all_sources_stale', 'global_labels')}))


if __name__ == '__main__':
    main()

"""Read-only source audit. No broker imports, network, or policy mutations.

Usage: python signal_source_audit.py --db signals.db --output agent-reports/signal-source-audit.json
Exact geometry matches are candidates, not proof of copying or shared ownership.
Receipt timestamps cannot establish the original author's publication time.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import closing
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sqlite3


def price(value):
    if isinstance(value, bool) or value is None:
        return None
    try:
        result = Decimal(str(value))
        return str(result.normalize()) if result.is_finite() and result > 0 else None
    except InvalidOperation:
        return None


def fingerprint(parsed):
    """Require explicit numeric geometry: no market-only or missing-side inference."""
    symbol = str(parsed.get('symbol') or '').upper()
    side = str(parsed.get('action') or '').lower()
    entry = price(parsed.get('entry'))
    stop = price(parsed.get('sl'))
    tps = parsed.get('tps') or []
    if not isinstance(tps, list):
        return None
    targets = [price(tp) for tp in tps]
    if not symbol or side not in ('buy', 'sell') or not entry or not stop:
        return None
    if not targets or any(tp is None for tp in targets):
        return None
    return (symbol, side, entry, stop, tuple(targets), parsed.get('order_type', 'market'))


def audit(rows, window_s=600):
    if window_s <= 0:
        raise ValueError('window_s must be positive')
    counts = defaultdict(Counter)
    recent = {}
    seen = set()
    echoes = []
    malformed = 0
    ordered = []
    for row in rows:
        try:
            stamp = datetime.fromisoformat(row['ts'].replace('Z', '+00:00'))
            if stamp.tzinfo is None:
                raise ValueError('timezone required')
            payload = row['payload']
            if isinstance(payload, str):
                payload = json.loads(payload)
            if not isinstance(payload, dict):
                raise ValueError('payload must be an object')
            ordered.append((stamp.timestamp(), row['source'], payload))
        except (ValueError, TypeError, KeyError, AttributeError):
            malformed += 1
    for ts, source, payload in sorted(ordered, key=lambda item: item[0]):
        msg_id = payload.get('msg_id')
        identity = (source, msg_id) if isinstance(msg_id, str) and msg_id else None
        if identity and identity in seen:
            counts[source]['replayed_events'] += 1
            continue
        if identity:
            seen.add(identity)
        c = counts[source]
        c['messages'] += 1
        parsed = payload.get('parsed') or {}
        if not isinstance(parsed, dict):
            c['malformed_parsed'] += 1
            continue
        if not parsed.get('is_signal'):
            c['not_signal'] += 1
            continue
        if not parsed.get('parse_ok'):
            c['needs_review'] += 1
            continue
        c['parsed_candidates'] += 1
        key = fingerprint(parsed)
        if key is None:
            c['geometry_unavailable'] += 1
            continue
        c['geometry_comparable'] += 1
        previous = recent.get(key)
        if previous and 0 <= ts - previous[0] < window_s:
            same_source = source == previous[1]
            c['same_source_repeat' if same_source else 'cross_source_echo'] += 1
            echoes.append({'first_observed_source': previous[1],
                           'first_observed_message': previous[2], 'source': source,
                           'message': msg_id, 'delay_s': round(ts - previous[0], 3),
                           'cross_source': not same_source})
        else:
            c['first_observed_geometry'] += 1
            recent[key] = (ts, source, msg_id)
    return {'scope': 'stored signal_received events only; not complete Telegram history',
            'method': 'exact entry/SL/ordered-TP geometry within receipt-time window',
            'window_s': window_s, 'malformed_events': malformed,
            'unique_messages': sum(c['messages'] for c in counts.values()),
            'sources': {source: dict(c) for source, c in sorted(counts.items())},
            'echoes': echoes,
            'limitations': ['No profitability inference or live policy changes.',
                            'First observed source is not proven original author.',
                            'Market-only, incomplete and near-match signals are not matched.',
                            'Parsed candidates may include recaps; this is not entry approval.']}


def read_events(path):
    uri = Path(path).resolve().as_uri() + '?mode=ro'
    with closing(sqlite3.connect(uri, uri=True)) as con:
        con.row_factory = sqlite3.Row
        return [dict(row) for row in con.execute(
            "SELECT ts, source, payload FROM events WHERE type='signal_received' ORDER BY ts")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', default='signals.db')
    parser.add_argument('--output', required=True)
    parser.add_argument('--window-s', type=int, default=600)
    args = parser.parse_args()
    result = audit(read_events(args.db), args.window_s)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=True) + '\n', encoding='utf-8')
    print(json.dumps({'output': str(target.resolve()), 'sources': len(result['sources']),
                      'unique_messages': result['unique_messages'],
                      'echoes': len(result['echoes']), 'malformed_events': result['malformed_events']}))


if __name__ == '__main__':
    main()

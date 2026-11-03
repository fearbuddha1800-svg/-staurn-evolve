---
slug: command_deck
type: note
graph: gitnexus
---

"""Read-only Command Deck projections. Never execute Pine, train or attach a broker."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sqlite3


def _read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return default


def _events(db, types):
    with sqlite3.connect(Path(db).resolve().as_uri() + '?mode=ro', uri=True, timeout=2) as con:
        rows = con.execute('SELECT ts,type,payload FROM events WHERE type IN (' +
                           ','.join('?' for _ in types) + ') ORDER BY ts DESC,rowid DESC LIMIT 2000', types)
        result = []
        for ts, kind, raw in rows:
            try:
                payload = json.loads(raw)
                if isinstance(payload, dict):
                    result.append((ts, kind, payload))
            except (ValueError, TypeError):
                continue
        return result


def _number(value):
    return value if isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value) else None


def _golden(payload):
    return any('golden_eye' in str(payload.get(key, '')).lower().replace(' ', '_') or
               'golden_edge' in str(payload.get(key, '')).lower().replace(' ', '_')
               for key in ('strategy_id', 'strategy_name', 'strategy', 'indicator'))


def golden_eye_data(base, db):
    result = {'observed_at': datetime.now(timezone.utc).isoformat(), 'available': False,
              'source': 'signals.db/events + watch_assignments.json', 'rows': [],
              'broker_orders_enabled': False,
              'notice': 'Strength and consensus are descriptive indices, not win probabilities. Missing observations are not neutral signals.'}
    assignments = _read_json(Path(base) / 'watch_assignments.json', [])
    pairs = {(a.get('symbol'), a.get('timeframe')) for a in assignments
             if isinstance(a, dict) and a.get('symbol') and a.get('timeframe')}
    latest, signals = {}, {}
    try:
        events = _events(db, ('pine_signal', 'golden_eye_state', 'golden_edge_state'))
    except (sqlite3.Error, OSError) as exc:
        result['reason'] = 'Recorded strategy state unavailable: ' + type(exc).__name__
        events = []
    for ts, kind, p in events:
        if not _golden(p) and kind == 'pine_signal':
            continue
        key = (p.get('symbol'), p.get('timeframe', p.get('tf')))
        if not all(key):
            continue
        pairs.add(key)
        latest.setdefault(key, (ts, p))
        if p.get('action') or p.get('signal'):
            signals.setdefault(key, {'action': p.get('action', p.get('signal')), 'ts': ts,
                                     'strategy_id': p.get('strategy_id'), 'price': p.get('price')})
    for key in sorted(pairs):
        ts, p = latest.get(key, (None, {}))
        state = p.get('state') if isinstance(p.get('state'), dict) else p
        def feature(name):
            value = state.get(name)
            if value is None:
                plot = p.get('plots', {}).get(name, {})
                value = plot.get('latest') if isinstance(plot, dict) else None
            return value
        age = None
        if ts:
            try:
                age = max(0, (datetime.now(timezone.utc) - datetime.fromisoformat(ts.replace('Z', '+00:00'))).total_seconds())
            except ValueError:
                pass
        result['rows'].append({'symbol': key[0], 'timeframe': key[1], 'available': bool(p),
                               'observed_at': ts, 'age_seconds': age,
                               'stale': age is None or age > 300,
                               'regime': feature('regime'), 'strength': _number(feature('strength')),
                               'consensus': _number(feature('consensus')),
                               'latest_signal': signals.get(key)})
    result['available'] = bool(latest)
    if not latest:
        result.setdefault('reason', 'No recorded GOLDEN EYE/EDGE observations; strategy files exist but no Golden watcher signals have been published.')
    return result


def ai_brain_data(base, db):
    from neural_pipeline import health
    pipeline = health(db)
    diagnostic = _read_json(str(db) + '.neural_eval.json', None)
    versions = pipeline.get('versions', [])
    model = versions[0] if versions else None
    metrics = model.get('metrics', {}) if model else {}
    auc = _number(metrics.get('holdout_auc', metrics.get('auc')))
    confidence = None
    try:
        for ts, kind, p in _events(db, ('pine_signal',)):
            ai = p.get('ai')
            if not isinstance(ai, dict):
                continue
            value = _number(ai.get('confidence'))
            # The watcher currently emits stub_model_neutral: it is not a model prediction.
            if value is not None and 0 <= value <= 1 and 'stub' not in str(ai).lower():
                confidence = {'value': value, 'symbol': p.get('symbol'),
                              'timeframe': p.get('timeframe'), 'observed_at': ts,
                              'direction': ai.get('direction'), 'rationale': ai.get('rationale')}
                break
    except (sqlite3.Error, OSError):
        pass
    labels = pipeline.get('verified_labels')
    minimum = pipeline.get('min_labels', 300)
    return {'observed_at': datetime.now(timezone.utc).isoformat(),
            'available': pipeline.get('status') != 'unavailable',
            'ready': labels is not None and labels >= minimum and not pipeline.get('audit_stale', True),
            'readiness_basis': 'Provenance-verified labels and fresh outcome audit; readiness does not enable trading.',
            'label_count': labels, 'min_labels': minimum, 'total_labels': pipeline.get('total_labels'),
            'holdout_auc': auc, 'model': model, 'setup_confidence': confidence,
            'diagnostic_evaluation': diagnostic,
            'notice': 'Diagnostic AUC is not a validated holdout result. Stub setup confidence is excluded.',
            'pipeline': pipeline, 'live_execution_enabled': False,
            'source': 'signals.db/neural_outcome_audit + neural_model_versions + events; signals.db.neural_eval.json (diagnostic only)'}

## Links from
- [[cockpit]]

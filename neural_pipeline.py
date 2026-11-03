"""Fail-closed, broker-read-only learning sidecar. Promotion never enables orders.

Legacy labels are retained but quarantined until independently reconciled. Money
metrics use MT5 realized account-currency P&L (fees included), never +/-1 proxies.
"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import time
from pathlib import Path

from scalp360.neural import LogisticChallenger, _auc

MIN_LABELS = 300
RETRAIN_EVERY = 100
AUC_MIN = .58
MIN_SHADOW = 100


class _Connection(sqlite3.Connection):
    def __exit__(self, *args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()


def connect(db):
    c = sqlite3.connect(db, timeout=15, factory=_Connection)
    c.row_factory = sqlite3.Row
    c.executescript('''
    CREATE TABLE IF NOT EXISTS neural_outcome_audit(
      label_id INTEGER PRIMARY KEY, ticket INTEGER, fingerprint TEXT NOT NULL,
      status TEXT NOT NULL, reason TEXT, checked_at REAL NOT NULL, evidence TEXT);
    CREATE TABLE IF NOT EXISTS neural_model_versions(
      version INTEGER PRIMARY KEY AUTOINCREMENT, created_at REAL NOT NULL,
      n_labels INTEGER NOT NULL, dataset_hash TEXT NOT NULL UNIQUE,
      state TEXT NOT NULL, artifact TEXT NOT NULL, metrics TEXT NOT NULL,
      mlflow_run_id TEXT, tracking_error TEXT);
    CREATE TABLE IF NOT EXISTS neural_shadow_predictions(
      version INTEGER NOT NULL, label_id INTEGER NOT NULL, scored_at REAL NOT NULL,
      score REAL NOT NULL, take_trade INTEGER NOT NULL, input_hash TEXT NOT NULL,
      PRIMARY KEY(version,label_id));
    ''')
    return c


def fingerprint(row):
    return hashlib.sha256(json.dumps(dict(row), sort_keys=True, default=str).encode()).hexdigest()


def label_rows(c):
    return c.execute('''SELECT l.*, m.ticket FROM neural_labels l
      LEFT JOIN neural_label_map m ON m.label_id=l.id ORDER BY l.ts,l.id''').fetchall()


def _finite(value):
    value = float(value)
    if not math.isfinite(value):
        raise ValueError('nonfinite broker value')
    return value


def validate_outcome(row, trade, broker):
    """Verify order->position identity, full exit volume and net label from history.

    None from MT5 is an API failure, never evidence of a closed position. INOUT
    reversals are rejected because their entry/exit allocation is ambiguous.
    """
    if not row['ticket']:
        raise ValueError('no ticket')
    if trade is not None:
        if trade['status'] != 'executed':
            raise ValueError('no unique executed trade link')
        if trade['symbol'] != row['symbol'] or trade['side'].lower() != row['side'].lower():
            raise ValueError('trade identity mismatch')
    positions = broker.positions_get()
    if positions is None:
        raise ValueError('positions unavailable')
    ticket = int(row['ticket'])
    orders = broker.history_orders_get(ticket=ticket)
    if orders is None:
        raise ValueError('orders unavailable')
    position_id = int(orders[0].position_id) if len(orders) == 1 else ticket
    if len(orders) > 1 or position_id <= 0:
        raise ValueError('ambiguous order position')
    if any(int(getattr(p, 'identifier', p.ticket)) == position_id for p in positions):
        raise ValueError('position still open')
    deals = broker.history_deals_get(position=position_id)
    if deals is None or not deals:
        raise ValueError('deal history unavailable')
    if any(int(d.position_id) != position_id or d.symbol != row['symbol'] for d in deals):
        raise ValueError('deal identity mismatch')
    if len({int(d.ticket) for d in deals}) != len(deals):
        raise ValueError('duplicate deal tickets')
    if any(int(d.entry) not in (0, 1, 3) for d in deals):
        raise ValueError('reversal/unsupported deal entry')
    ins = [d for d in deals if int(d.entry) == 0]
    outs = [d for d in deals if int(d.entry) in (1, 3)]
    if not ins or not outs or not any(int(d.order) == ticket for d in ins):
        raise ValueError('missing matching entry order or exit')
    expected_type = 0 if row['side'].lower() == 'buy' else 1
    if any(int(d.type) != expected_type or int(d.magic) != 20261014 for d in ins):
        raise ValueError('side/magic mismatch')
    vin = sum(_finite(d.volume) for d in ins)
    vout = sum(_finite(d.volume) for d in outs)
    if vin <= 0 or abs(vin-vout) > 1e-8:
        raise ValueError('partial close or volume mismatch')
    if trade is not None and trade.get('lot') is not None:
        if abs(vin-_finite(trade['lot'])) > 1e-8:
            raise ValueError('partial close or volume mismatch')
    opened = min(_finite(d.time) for d in ins)
    closed = max(_finite(d.time) for d in outs)
    entry = sum(_finite(d.price)*_finite(d.volume) for d in ins)/vin
    if abs(entry-_finite(row['entry'])) > max(1e-8, abs(entry)*1e-7):
        raise ValueError('entry price mismatch')
    if abs(opened-_finite(row['ts'])) > 2 or closed < opened:
        raise ValueError('entry/exit timestamp mismatch')
    profit = sum(_finite(d.profit) for d in deals)
    commission = sum(_finite(d.commission) for d in deals)
    swap = sum(_finite(d.swap) for d in deals)
    fee = sum(_finite(getattr(d, 'fee', 0)) for d in deals)
    net = profit+commission+swap+fee
    if row['outcome'] not in (0, 1) or row['outcome'] != int(net > 0):
        raise ValueError('outcome disagrees with MT5 net P&L')
    return dict(position_id=position_id, deal_tickets=[int(d.ticket) for d in deals],
                opened_at=opened, closed_at=closed, net_cash=net,
                commission=commission, swap=swap, fee=fee,
                cost_cash=-(commission+swap+fee),
                cost_basis='MT5 commission+swap+fee; spread/slippage embedded in fills')


def reconcile(db, broker):
    """Audit all completed rows, preserving originals; never guess orphan links."""
    counts = {'verified': 0, 'quarantined': 0}
    with connect(db) as c:
        for row in label_rows(c):
            if row['outcome'] is None:
                continue
            evidence = None
            try:
                # The trades table is the executor's ledger; neural labels are
                # recorded independently by neural_label_collector. Do not require
                # a trades-table row — validate_outcome already queries MT5
                # history directly (orders + deals). Requiring both would strand
                # every label that was captured outside the executor path.
                linked = {'ticket': row['ticket'], 'symbol': row['symbol'],
                          'side': row['side'], 'status': 'executed',
                          'lot': None}
                evidence = validate_outcome(row, linked, broker)
                evidence['trade_fingerprint'] = fingerprint(linked)
                status, reason = 'verified', None
            except Exception as exc:
                status, reason = 'quarantined', str(exc)
            c.execute('INSERT OR REPLACE INTO neural_outcome_audit VALUES(?,?,?,?,?,?,?)',
                      (row['id'], row['ticket'], fingerprint(row), status, reason,
                       time.time(), json.dumps(evidence)))
            counts[status] += 1
    return counts


def verified_rows(c):
    from neural_label_collector import _feature_vector
    rows = []
    for row in label_rows(c):
        audits = c.execute('SELECT * FROM neural_outcome_audit WHERE label_id=?', (row['id'],)).fetchone()
        if not audits or audits['status'] != 'verified' or audits['fingerprint'] != fingerprint(row):
            continue
        # A label or position reused by multiple maps cannot count independently.
        if c.execute('SELECT COUNT(*) FROM neural_label_map WHERE label_id=?', (row['id'],)).fetchone()[0] != 1:
            continue
        try:
            evidence = json.loads(audits['evidence'])
            # trades table is the executor's ledger; neural labels recorded
            # independently may not have a trades row. validate_outcome already
            # verified against MT5 history — trust the audit.
            features = json.loads(row['features'])
            x = _feature_vector(features)
            if not all(math.isfinite(v) for v in x):
                continue
            rows.append(dict(id=row['id'], ticket=row['ticket'], ts=row['ts'], x=x,
                             y=row['outcome'], evidence=evidence))
        except (ValueError, TypeError, KeyError):
            continue
    # One broker position is one observation even if separate entry orders exist.
    positions = [r['evidence']['position_id'] for r in rows]
    return [r for r in rows if positions.count(r['evidence']['position_id']) == 1]


def _score(artifact, x):
    if len(x) != len(artifact['w']) or not all(math.isfinite(v) for v in x):
        raise ValueError('invalid inference features')
    scaled = [(v-m)/s for v,m,s in zip(x,artifact['mean'],artifact['scale'])]
    z = sum(w*v for w,v in zip(artifact['w'],scaled))+artifact['b']
    return 1/(1+math.exp(-max(-30,min(30,z))))


def train_if_due(db, tracking_uri=None):
    """Persist immutable candidates every 100 new verified trades after 300.

    Train/validation/holdout are chronological; interval purging excludes any
    trade closing at/after the next partition starts. No fit after calibration.
    """
    with connect(db) as c:
        rows = verified_rows(c)
        previous = c.execute('SELECT n_labels FROM neural_model_versions ORDER BY version DESC LIMIT 1').fetchone()
        if len(rows) < MIN_LABELS or (previous and len(rows)-previous[0] < RETRAIN_EVERY):
            return None
        a,b = int(len(rows)*.6), int(len(rows)*.8)
        train = [r for r in rows[:a] if r['evidence']['closed_at'] < rows[a]['ts']]
        val = [r for r in rows[a:b] if r['evidence']['closed_at'] < rows[b]['ts']]
        test = rows[b:]
        if any(len({r['y'] for r in split}) < 2 for split in (train,val,test)):
            return None
        dim = len(train[0]['x'])
        mean = [sum(r['x'][j] for r in train)/len(train) for j in range(dim)]
        scale = [max(1e-8,math.sqrt(sum((r['x'][j]-mean[j])**2 for r in train)/len(train))) for j in range(dim)]
        model = LogisticChallenger(dim)
        model.fit([tuple((v-m)/s for v,m,s in zip(r['x'],mean,scale)) for r in train], [r['y'] for r in train])
        artifact = dict(w=model.w,b=model.b,mean=mean,scale=scale,feature_schema=1)
        artifact['threshold'] = sorted(_score(artifact,r['x']) for r in val)[int(.7*len(val))]
        scores = [_score(artifact,r['x']) for r in test]
        net = sum(r['evidence']['net_cash'] for r,s in zip(test,scores) if s >= artifact['threshold'])
        baseline = sum(r['evidence']['net_cash'] for r in test)
        auc = _auc(scores,[r['y'] for r in test])
        eligible = auc >= AUC_MIN and net > baseline > 0
        metrics = dict(holdout_auc=auc,model_net_cash=net,baseline_net_cash=baseline,
                       n_train=len(train),n_val=len(val),n_test=len(test),holdout_pass=eligible,
                       mean_cost_cash=sum(r['evidence']['cost_cash'] for r in test)/len(test))
        digest = hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()
        run_id,error = None,None
        if tracking_uri:
            try:
                import mlflow
                mlflow.set_tracking_uri(tracking_uri)
                mlflow.set_experiment('signal-relay-neural')
                with mlflow.start_run() as run:
                    mlflow.log_params(dict(dataset_hash=digest,n_labels=len(rows),feature_schema=1))
                    mlflow.log_metrics({k:float(v) for k,v in metrics.items()})
                    mlflow.log_dict(artifact,'model.json')
                    run_id = run.info.run_id
            except Exception as exc:
                error = str(exc)
        c.execute('''INSERT INTO neural_model_versions
          (created_at,n_labels,dataset_hash,state,artifact,metrics,mlflow_run_id,tracking_error)
          VALUES(?,?,?,?,?,?,?,?)''', (time.time(),len(rows),digest,'shadow',json.dumps(artifact),json.dumps(metrics),run_id,error))
        return dict(version=c.execute('SELECT last_insert_rowid()').fetchone()[0],**metrics)


def shadow_observe(db, label_id, x):
    """Sidecar consumer; immutable predictions only before a label closes.

    Backfills are not prospective shadow evidence. This never changes live rules.
    """
    with connect(db) as c:
        row = c.execute('SELECT ts,outcome,features FROM neural_labels WHERE id=?',(label_id,)).fetchone()
        if not row or row['outcome'] is not None or abs(time.time()-row['ts']) > 60:
            return 0
        for version in c.execute("SELECT * FROM neural_model_versions WHERE state IN ('shadow','promoted')").fetchall():
            if row['ts'] <= version['created_at']:
                continue
            artifact = json.loads(version['artifact'])
            score = _score(artifact,x)
            c.execute('INSERT OR IGNORE INTO neural_shadow_predictions VALUES(?,?,?,?,?,?)',
                      (version['version'],label_id,time.time(),score,int(score >= artifact['threshold']),
                       hashlib.sha256(json.dumps(list(x)).encode()).hexdigest()))
        return c.total_changes


def promote_if_ready(db):
    """Registry-only promotion requires future shadow outcomes and tracked run.

    Independent live-execution approval/consumer is intentionally not provided.
    """
    promoted = []
    with connect(db) as c:
        rows = {r['id']:r for r in verified_rows(c)}
        for v in c.execute("SELECT * FROM neural_model_versions WHERE state='shadow'").fetchall():
            if not json.loads(v['metrics'])['holdout_pass'] or not v['mlflow_run_id']:
                continue
            pred = [p for p in c.execute('SELECT * FROM neural_shadow_predictions WHERE version=?',(v['version'],))
                    if p['label_id'] in rows and p['scored_at'] < rows[p['label_id']]['evidence']['closed_at']
                    and p['input_hash'] == hashlib.sha256(json.dumps(list(rows[p['label_id']]['x'])).encode()).hexdigest()]
            if len(pred) < MIN_SHADOW:
                continue
            auc = _auc([p['score'] for p in pred],[rows[p['label_id']]['y'] for p in pred])
            base = sum(rows[p['label_id']]['evidence']['net_cash'] for p in pred)
            net = sum(rows[p['label_id']]['evidence']['net_cash'] for p in pred if p['take_trade'])
            if auc >= AUC_MIN and net > base > 0:
                c.execute("UPDATE neural_model_versions SET state='retired' WHERE state='promoted'")
                c.execute("UPDATE neural_model_versions SET state='promoted' WHERE version=?",(v['version'],))
                promoted.append(v['version'])
    return promoted


def health(db):
    """Pure read-only health, no schema migration, broker attach or training."""
    result = dict(status='unavailable',live_execution_enabled=False,min_labels=MIN_LABELS,
                  retrain_every=RETRAIN_EVERY,auc_min=AUC_MIN)
    c = None
    try:
        c = sqlite3.connect(Path(db).resolve().as_uri()+'?mode=ro',uri=True)
        c.row_factory = sqlite3.Row
        total = c.execute('SELECT COUNT(*) FROM neural_labels').fetchone()[0]
        try:
            rows = verified_rows(c)
        except sqlite3.Error:
            rows = []
        try:
            versions = [dict(r) for r in c.execute('''SELECT version,created_at,n_labels,state,metrics,
              mlflow_run_id,tracking_error FROM neural_model_versions ORDER BY version DESC LIMIT 10''')]
        except sqlite3.Error:
            versions = []
        for v in versions:
            v['metrics'] = json.loads(v['metrics'])
        try:
            audit_at = c.execute('SELECT MAX(checked_at) FROM neural_outcome_audit').fetchone()[0]
        except sqlite3.Error:
            audit_at = None
        stale = audit_at is None or time.time()-audit_at > 300
        result.update(status='stale' if stale else ('shadow' if versions else 'accumulating'),
                      total_labels=total,verified_labels=len(rows),excluded_labels=total-len(rows),
                      distance_to_gate=max(0,MIN_LABELS-len(rows)),last_audit_at=audit_at,
                      audit_stale=stale,versions=versions,
                      mean_cost_cash=(sum(r['evidence']['cost_cash'] for r in rows)/len(rows) if rows else None))
    except (sqlite3.Error,OSError,ValueError,KeyError) as exc:
        result['error'] = str(exc)
    finally:
        if c is not None:
            c.close()
    return result


def tick(db, broker, tracking_uri=None):
    if broker is None or not callable(getattr(broker, 'history_deals_get', None)):
        return dict(audit={'error': 'broker unavailable'}, trained=None, promoted=[])
    audit = reconcile(db,broker)
    trained = train_if_due(db,tracking_uri)
    promoted = promote_if_ready(db)
    return dict(audit=audit,trained=trained,promoted=promoted)

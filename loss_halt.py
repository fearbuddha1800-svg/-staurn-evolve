"""Durable account-currency daily NET realised-loss latch (read-only broker).

Caller initializes/injects an MT5-compatible broker and consults observe(now)
BEFORE every entry. This module is additive; it does not wire existing engines,
change flag files, or submit orders. UTC calendar days by default; supply a
fixed trading_timezone explicitly to use another calendar. now must be aware.

Trading deals (BUY/SELL, including entry commissions) contribute profit + swap
+ commission + fee; balance/deposit deals are excluded. Positive P/L offsets
losses. Broker history must be complete for the requested day. None/errors are
UNKNOWN, never zero. A durable SQLite transaction commits latch and audit
atomically; database corruption/identity/config changes raise, never reset.
Use a dedicated persistent path, never delete it to resume. Deletion/tampering
is outside this module's threat model. Reconciliation is read-only and records
broker history, open positions and pending orders; recovery requires a fresh,
unchanged receipt, operator/reason, and a day below the loss limit.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import sqlite3
import uuid


class SafetyError(RuntimeError):
    """Fail closed: caller must block entries when this is raised."""


def _money(value):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise SafetyError('invalid monetary value') from exc
    if not result.is_finite():
        raise SafetyError('non-finite monetary value')
    return result


class LossHalt:
    def __init__(self, path, broker, daily_loss_limit, *, trading_timezone=timezone.utc):
        self.path = str(Path(path))
        self.broker = broker
        self.limit = _money(daily_loss_limit)
        if self.limit <= 0:
            raise ValueError('daily_loss_limit must be positive account currency')
        self.timezone = trading_timezone
        self.policy = {'limit': str(self.limit), 'timezone': str(trading_timezone)}
        with self._transaction() as con:
            con.execute('CREATE TABLE IF NOT EXISTS loss_state (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS loss_audit (seq INTEGER PRIMARY KEY, data TEXT NOT NULL)')
            row = con.execute('SELECT data FROM loss_state WHERE id=1').fetchone()
            if row is None:
                self._save(con, dict(policy=self.policy, day=None, pnl='0', loss='0',
                                     halted=False, revision=0, identity=None, receipt=None))
            elif json.loads(row[0])['policy'] != self.policy:
                raise SafetyError('persisted loss policy differs; explicit migration required')

    @contextmanager
    def _transaction(self):
        con = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:
            con.execute('PRAGMA busy_timeout=10000')
            con.execute('PRAGMA synchronous=FULL')
            con.execute('BEGIN IMMEDIATE')
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()

    @staticmethod
    def _load(con):
        return json.loads(con.execute('SELECT data FROM loss_state WHERE id=1').fetchone()[0])

    @staticmethod
    def _save(con, state):
        con.execute('INSERT OR REPLACE INTO loss_state VALUES (1,?)', (json.dumps(state),))

    @staticmethod
    def _log(con, kind, now, **payload):
        event = {'kind': kind, 'at': now.isoformat(), **payload}
        con.execute('INSERT INTO loss_audit(data) VALUES (?)', (json.dumps(event),))
        return event

    def _local(self, now):
        if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
            raise ValueError('now must be a timezone-aware datetime')
        return now.astimezone(self.timezone)

    def _roll(self, con, state, now):
        day = self._local(now).date().isoformat()
        if state['day'] and day < state['day']:
            raise SafetyError('clock moved behind persisted trading day')
        if day != state['day']:
            self._log(con, 'day_rollover', now, previous_day=state['day'],
                      previous_pnl=state['pnl'], halted=state['halted'])
            state.update(day=day, pnl='0', loss='0', receipt=None,
                         revision=state['revision'] + 1)

    def _snapshot(self, now, *, exposures=False):
        local = self._local(now)
        try:
            account = self.broker.account_info()
            if account is None:
                raise SafetyError('account snapshot unavailable')
            identity = [str(account.login), str(account.server), str(account.currency)]
            deals = self.broker.history_deals_get(local.replace(hour=0, minute=0, second=0, microsecond=0), now)
            if deals is None:
                raise SafetyError('deal history unavailable')
            rows = {}
            for deal in deals:
                # Explicitly exclude funding/balance transactions.
                if deal.type not in (self.broker.DEAL_TYPE_BUY, self.broker.DEAL_TYPE_SELL):
                    continue
                stamp = datetime.fromtimestamp(deal.time, timezone.utc)
                if stamp.astimezone(self.timezone).date() != local.date() or stamp > now:
                    raise SafetyError('broker returned out-of-window trading deal')
                key = str(deal.ticket)
                values = [str(_money(getattr(deal, name) if name != 'fee'
                                     else getattr(deal, name, 0)))
                          for name in ('profit', 'swap', 'commission', 'fee')]
                record = dict(ticket=key, time=deal.time, type=deal.type, amounts=values)
                if key in rows and rows[key] != record:
                    raise SafetyError('conflicting duplicate deal')
                rows[key] = record
            ordered = sorted(rows.values(), key=lambda r: r['ticket'])
            pnl = sum((_money(v) for r in ordered for v in r['amounts']), Decimal(0))
            snapshot = dict(identity=identity, day=local.date().isoformat(),
                            pnl=str(pnl), deals=ordered)
            if exposures:
                for label, getter in [('positions', self.broker.positions_get), ('orders', self.broker.orders_get)]:
                    items = getter()
                    if items is None:
                        raise SafetyError(f'{label} unavailable; reconciliation incomplete')
                    snapshot[label] = sorted([
                        {k: getattr(p, k, None) for k in (
                            'ticket', 'symbol', 'type', 'volume', 'volume_current',
                            'volume_initial', 'sl', 'tp', 'price_open', 'price_stoplimit')}
                        for p in items], key=lambda r: r['ticket'])
            # Also refuse non-JSON/non-finite exposure data.
            json.dumps(snapshot, allow_nan=False)
            return snapshot
        except SafetyError:
            raise
        except Exception as exc:
            raise SafetyError(f'broker reconciliation unavailable: {exc}') from exc

    def _observe(self, con, state, snapshot, now):
        self._roll(con, state, now)
        if state['identity'] is not None and state['identity'] != snapshot['identity']:
            raise SafetyError('account identity changed')
        loss = max(Decimal(0), -_money(snapshot['pnl']))
        if state['pnl'] != snapshot['pnl'] or state['identity'] is None:
            state.update(revision=state['revision'] + 1, receipt=None)
        state.update(identity=snapshot['identity'], pnl=snapshot['pnl'], loss=str(loss))
        if loss >= self.limit and not state['halted']:
            state.update(halted=True, receipt=None, revision=state['revision'] + 1)
            self._log(con, 'loss_breach', now, day=state['day'], loss=str(loss), limit=str(self.limit))

    def status(self, now):
        """Local persisted state only; does NOT assert broker history freshness."""
        with self._transaction() as con:
            state = self._load(con)
            self._roll(con, state, now)
            self._save(con, state)
            return state

    def observe(self, now):
        """Refresh full-day realised P/L idempotently and durably latch at >= limit."""
        with self._transaction() as con:
            state = self._load(con)
            self._observe(con, state, self._snapshot(now), now)
            self._save(con, state)
            return state

    def reconcile(self, now, *, operator, reason):
        if not operator.strip() or not reason.strip():
            raise ValueError('operator and reconciliation reason required')
        with self._transaction() as con:
            state = self._load(con)
            snapshot = self._snapshot(now, exposures=True)
            self._observe(con, state, snapshot, now)
            receipt = dict(id=uuid.uuid4().hex, at=now.isoformat(), revision=state['revision'],
                           operator=operator, reason=reason, reconciled=snapshot)
            state['receipt'] = receipt
            self._log(con, 'reconciliation', now, **receipt)
            self._save(con, state)
            return receipt

    def recover(self, now, *, reconciliation_id, operator, reason, max_age_s=60):
        """Clear only a latched state with a fresh, unchanged reconciliation receipt.

        Never erases daily loss or audit. A same-day breach cannot be overridden.
        Recovery authorization belongs to caller; operator is an audit identity,
        not authentication. An external HALT/PAUSE is never altered.
        """
        if not operator.strip() or not reason.strip():
            raise ValueError('operator and recovery reason required')
        if not 0 < max_age_s <= 60:
            raise ValueError('receipt validity must be >0 and <=60 seconds')
        with self._transaction() as con:
            state = self._load(con)
            self._roll(con, state, now)
            receipt = state['receipt']
            if not state['halted'] or not receipt or receipt['id'] != reconciliation_id:
                raise SafetyError('active halt and explicit reconciliation required')
            age = (now - datetime.fromisoformat(receipt['at'])).total_seconds()
            if not 0 <= age <= max_age_s or receipt['revision'] != state['revision']:
                raise SafetyError('stale reconciliation; reconcile again')
            snapshot = self._snapshot(now, exposures=True)
            if snapshot != receipt['reconciled']:
                raise SafetyError('broker state changed; reconcile again')
            if max(Decimal(0), -_money(snapshot['pnl'])) >= self.limit:
                raise SafetyError('daily loss still breaches limit')
            event = self._log(con, 'operator_recovery', now, operator=operator,
                              reason=reason, reconciliation_id=reconciliation_id,
                              reconciled=snapshot)
            state.update(halted=False, receipt=None, revision=state['revision'] + 1)
            self._save(con, state)
            return event

    def audit(self):
        with self._transaction() as con:
            return [json.loads(r[0]) for r in con.execute('SELECT data FROM loss_audit ORDER BY seq')]

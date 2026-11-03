"""Offline fake-broker tests; no MT5 import, flag changes, or sends."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS
import sqlite3

import pytest
from loss_halt import LossHalt, SafetyError

NOW = datetime(2026, 10, 15, 23, 59, 30, tzinfo=timezone.utc)
NEXT = NOW + timedelta(minutes=1)


class Broker:
    DEAL_TYPE_BUY, DEAL_TYPE_SELL = 0, 1

    def __init__(self):
        self.deals = []
        self.positions = []
        self.orders = []
        self.account = NS(login=123, server='Fake-Demo', currency='USD')

    def account_info(self):
        return self.account

    def history_deals_get(self, start, end):
        if self.deals is None:
            return None
        return [d for d in self.deals if start.timestamp() <= d.time <= end.timestamp()]

    def positions_get(self):
        return self.positions

    def orders_get(self):
        return self.orders

    def deal(self, profit, *, when=NOW, ticket=1, **kwargs):
        d = NS(ticket=ticket, time=when.timestamp(), type=0, profit=profit,
               swap=0, commission=0, fee=0)
        d.__dict__.update(kwargs)
        self.deals.append(d)
        return d


@pytest.fixture
def setup(tmp_path):
    b = Broker()
    path = tmp_path / 'loss-state.sqlite3'
    return b, path, LossHalt(path, b, 100)


def test_breach_latches_at_limit_and_is_idempotent(setup):
    b, _, h = setup
    b.deal(-99, commission=-1)
    assert h.observe(NOW)['halted']
    assert h.observe(NOW)['loss'] == '100'
    assert [e['kind'] for e in h.audit()].count('loss_breach') == 1


def test_restart_preserves_latch(setup):
    b, path, h = setup
    b.deal(-101)
    h.observe(NOW)
    restarted = LossHalt(path, b, 100)
    assert restarted.status(NOW)['halted']
    assert restarted.observe(NOW)['halted']


def test_midnight_rollover_resets_counter_not_latch(setup):
    b, path, h = setup
    b.deal(-150)
    h.observe(NOW)
    restarted = LossHalt(path, b, 100)
    state = restarted.status(NEXT)
    assert state['loss'] == '0' and state['pnl'] == '0'
    assert state['day'] == '2026-10-16' and state['halted']
    assert restarted.observe(NEXT)['halted']


def test_recovery_requires_reconciliation_and_is_recorded(setup):
    b, path, h = setup
    b.deal(-150)
    h.observe(NOW)
    with pytest.raises(SafetyError, match='reconciliation required'):
        h.recover(NEXT, reconciliation_id='flag-flip', operator='alice', reason='resume')
    b.positions = [NS(ticket=2, symbol='XAUUSD', type=0, volume=.1, sl=90, tp=0, price_open=100)]
    receipt = h.reconcile(NEXT, operator='alice', reason='review account and history')
    assert receipt['reconciled']['positions'][0]['ticket'] == 2
    restarted = LossHalt(path, b, 100)
    event = restarted.recover(NEXT, reconciliation_id=receipt['id'], operator='alice', reason='new day reviewed')
    assert event['kind'] == 'operator_recovery'
    assert event['reconciled'] == receipt['reconciled']
    assert not LossHalt(path, b, 100).status(NEXT)['halted']
    assert [e['kind'] for e in h.audit()][-2:] == ['reconciliation', 'operator_recovery']
    with pytest.raises(SafetyError):
        h.recover(NEXT, reconciliation_id=receipt['id'], operator='alice', reason='replay')


def test_same_day_recovery_cannot_override_breach(setup):
    b, _, h = setup
    b.deal(-100)
    receipt = h.reconcile(NOW, operator='alice', reason='check')
    with pytest.raises(SafetyError, match='still breaches'):
        h.recover(NOW, reconciliation_id=receipt['id'], operator='alice', reason='override')
    assert h.status(NOW)['halted']


def test_no_breach_day_never_latches_and_profits_offset(setup):
    b, _, h = setup
    b.deal(-80)
    b.deal(20, ticket=2, swap=-1, fee=-2)
    b.deal(-9999, ticket=3, type=2)  # funding excluded
    state = h.observe(NOW)
    assert state['loss'] == '63' and not state['halted']
    assert not h.observe(NEXT)['halted']


@pytest.mark.parametrize('field', ['deals', 'positions', 'orders', 'account'])
def test_unknown_broker_data_never_authorizes_recovery(setup, field):
    b, _, h = setup
    b.deal(-100)
    h.observe(NOW)
    setattr(b, field, None)
    with pytest.raises(SafetyError):
        h.reconcile(NEXT, operator='alice', reason='check')
    assert h.status(NEXT)['halted']


def test_changed_positions_invalidate_reconciliation(setup):
    b, _, h = setup
    b.deal(-100)
    h.observe(NOW)
    receipt = h.reconcile(NEXT, operator='alice', reason='check')
    b.orders = [NS(ticket=77)]
    with pytest.raises(SafetyError, match='state changed'):
        h.recover(NEXT, reconciliation_id=receipt['id'], operator='alice', reason='resume')
    assert h.status(NEXT)['halted']


def test_stale_receipt_cannot_recover(setup):
    b, _, h = setup
    b.deal(-100)
    h.observe(NOW)
    r = h.reconcile(NEXT, operator='alice', reason='check')
    with pytest.raises(SafetyError, match='stale reconciliation'):
        h.recover(NEXT + timedelta(seconds=61), reconciliation_id=r['id'], operator='alice', reason='resume')


def test_multiple_instances_do_not_lose_latch(setup):
    b, path, h = setup
    other = LossHalt(path, b, 100)
    b.deal(-100)
    h.observe(NOW)
    b.deals = []  # corrected broker history must NOT implicitly unlatch
    assert other.observe(NOW)['halted']


def test_corrupt_database_not_silently_reset(tmp_path):
    path = tmp_path / 'bad.sqlite3'
    path.write_bytes(b'not a database')
    with pytest.raises(sqlite3.DatabaseError):
        LossHalt(path, Broker(), 100)


def test_account_policy_and_clock_changes_rejected(setup):
    b, path, h = setup
    h.observe(NOW)
    with pytest.raises(SafetyError, match='policy differs'):
        LossHalt(path, b, 200)
    b.account.login = 999
    with pytest.raises(SafetyError, match='identity changed'):
        h.observe(NOW)
    with pytest.raises(SafetyError, match='clock moved'):
        h.status(NOW - timedelta(days=1))
    with pytest.raises(ValueError, match='aware'):
        h.status(NOW.replace(tzinfo=None))


def test_nonfinite_history_and_duplicate_conflict_rejected(setup):
    b, _, h = setup
    d = b.deal(float('nan'))
    with pytest.raises(SafetyError):
        h.observe(NOW)
    d.profit = -10
    b.deal(-11)
    with pytest.raises(SafetyError, match='conflicting duplicate'):
        h.observe(NOW)


def test_recovery_and_latch_audit_commit_atomically(setup, monkeypatch):
    b, _, h = setup
    b.deal(-100)
    h.observe(NOW)
    r = h.reconcile(NEXT, operator='alice', reason='check')
    def fail(*args, **kwargs):
        raise OSError('audit disk failure')
    monkeypatch.setattr(h, '_log', fail)
    with pytest.raises(OSError):
        h.recover(NEXT, reconciliation_id=r['id'], operator='alice', reason='resume')
    assert h.status(NEXT)['halted']


def test_restart_in_separate_python_process(setup):
    import os
    import subprocess
    import sys
    b, path, h = setup
    b.deal(-100)
    h.observe(NOW)
    code = (
        'import sys; from datetime import datetime; from loss_halt import LossHalt; '
        'h=LossHalt(sys.argv[1],None,100); '
        'assert h.status(datetime.fromisoformat(sys.argv[2]))["halted"]; '
        'print("persisted HALTED in new process")'
    )
    env = dict(os.environ, PYTHONPATH='')
    run = subprocess.run([sys.executable, '-c', code, str(path), NOW.isoformat()],
                         env=env, capture_output=True, text=True, check=True)
    assert run.stdout.strip() == 'persisted HALTED in new process'


def test_malformed_history_never_assumed_zero(setup):
    b, _, h = setup
    d = b.deal(-100)
    del d.profit
    with pytest.raises(SafetyError):
        h.observe(NOW)


def test_pending_volume_change_requires_new_reconciliation(setup):
    b, _, h = setup
    b.deal(-100)
    h.observe(NOW)
    b.orders = [NS(ticket=9, volume_current=.1)]
    r = h.reconcile(NEXT, operator='alice', reason='check')
    b.orders[0].volume_current = .2
    with pytest.raises(SafetyError, match='state changed'):
        h.recover(NEXT, reconciliation_id=r['id'], operator='alice', reason='resume')


def test_timezone_calendar_day_explicit(tmp_path):
    tz = timezone(timedelta(hours=-4))
    b = Broker()
    h = LossHalt(tmp_path / 'tz.sqlite3', b, 100, trading_timezone=tz)
    b.deal(-100)
    h.observe(NOW)
    assert h.observe(NEXT)['loss'] == '100'  # UTC midnight is NOT local midnight
    local_next = NOW + timedelta(hours=5)
    assert h.observe(local_next)['loss'] == '0'
    assert h.status(local_next)['halted']

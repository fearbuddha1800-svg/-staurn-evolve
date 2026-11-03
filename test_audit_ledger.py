"""Offline tests: scratch DBs only; no broker, credentials or live state."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import importlib.util
from unittest.mock import patch
import copy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from audit_ledger import AuditLedger, EVENTS_URL, GENESIS, IntegrityError, LedgerError, entry_hash

STATE = dict(position_size=-0.2, netprofit=12.5, equity=1012.5, max_drawdown=20)


class AuditLedgerTests(unittest.TestCase):
    def setUp(self):
        scratch = Path.home() / '.hermes/cache/scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'audit.db'
        self.ledger = AuditLedger(self.path, scope='paper:XAUUSD')

    def snapshot(self, **changes):
        return self.ledger.record_snapshot(dict(STATE, **changes), actor='collector', reason='observation')

    def proposal(self):
        self.snapshot()
        self.snapshot(equity=990, netprofit=-10)
        return self.ledger.propose_revert(1, actor='requester', reason='correct paper state')

    def approve(self, proposal):
        return self.ledger.decide_revert(proposal['seq'], approve=True,
                                         actor='reviewer', reason='reviewed')

    def test_empty_and_persistence(self):
        self.assertEqual(self.ledger.verify()['head_hash'], GENESIS)
        first = self.snapshot()
        reopened = AuditLedger(self.path, scope='paper:XAUUSD')
        self.assertEqual(reopened.entries(), [first])
        self.assertTrue(reopened.verify(expected_head=(1, first['hash']))['ok'])
        with self.assertRaises(IntegrityError):
            AuditLedger(self.path, scope='another-scope')

    def test_chain_canonical_hash_and_metadata_copy(self):
        meta = {'units': {'equity': 'USD'}, 'source_event_id': 'offline-observation'}
        state = copy.deepcopy(STATE)
        first = self.ledger.record_snapshot(state, actor='collector', reason='observation', metadata=meta)
        second = self.snapshot()
        meta['units']['equity'] = 'changed'
        state['equity'] = 0
        self.assertEqual(self.ledger.entries()[0]['payload']['metadata']['units']['equity'], 'USD')
        self.assertEqual(first['state']['equity'], STATE['equity'])
        self.assertEqual(second['prev_hash'], first['hash'])
        self.assertEqual(entry_hash(dict(reversed(list(second.items())))), second['hash'])

    def test_unknown_metrics_and_bad_numbers(self):
        self.snapshot(position_size=None, netprofit=None, equity=None, max_drawdown=None)
        before = self.ledger.verify()
        for key, value in [('equity', True), ('equity', float('nan')),
                           ('equity', float('inf')), ('max_drawdown', -1), ('position_size', '1')]:
            with self.subTest(key=key, value=value), self.assertRaises(LedgerError):
                self.snapshot(**{key: value})
        for state in ({}, dict(STATE, extra=1)):
            with self.assertRaises(LedgerError):
                self.ledger.record_snapshot(state, actor='a', reason='b')
        with self.assertRaises(LedgerError):
            self.ledger.record_snapshot(STATE, actor=' ', reason='b')
        with self.assertRaises(ValueError):
            self.ledger.record_snapshot(STATE, actor='a', reason='b', metadata={'bad': float('nan')})
        self.assertEqual(self.ledger.verify(), before)

    def test_revert_proposal_approval_commit_preserves_history(self):
        p = self.proposal()
        before = self.ledger.entries()
        approval = self.approve(p)
        committed = self.ledger.commit_revert(p['seq'], actor='operator', reason='ledger compensation only')
        self.assertEqual(committed['state'], STATE)
        self.assertEqual(committed['payload']['approval_seq'], approval['seq'])
        self.assertEqual(self.ledger.entries()[:3], before)
        self.assertEqual(self.ledger.verify()['count'], 5)
        with self.assertRaises(LedgerError):
            self.ledger.commit_revert(p['seq'], actor='operator', reason='replay')
        self.assertEqual(self.ledger.verify()['count'], 5)

    def test_self_approval_unknown_proposal_and_missing_approval_fail(self):
        p = self.proposal()
        for proposal_seq, actor in [(p['seq'], 'requester'), (999, 'reviewer'), (1, 'reviewer')]:
            with self.assertRaises(LedgerError):
                self.ledger.decide_revert(proposal_seq, approve=True, actor=actor, reason='bad')
        with self.assertRaises(LedgerError):
            self.ledger.commit_revert(p['seq'], actor='operator', reason='unapproved')
        self.assertEqual(self.ledger.verify()['count'], 3)

    def test_rejected_and_duplicate_decision(self):
        p = self.proposal()
        self.ledger.decide_revert(p['seq'], approve=False, actor='reviewer', reason='not justified')
        with self.assertRaises(LedgerError):
            self.approve(p)
        with self.assertRaises(LedgerError):
            self.ledger.commit_revert(p['seq'], actor='operator', reason='rejected')
        self.assertEqual(self.ledger.verify()['count'], 4)

    def test_stale_approval_and_stale_commit(self):
        p = self.proposal()
        self.snapshot(equity=2000)
        with self.assertRaises(LedgerError):
            self.approve(p)
        # Rejection remains possible for a stale proposal.
        self.ledger.decide_revert(p['seq'], approve=False, actor='reviewer', reason='stale')
        p2 = self.ledger.propose_revert(1, actor='requester', reason='new base')
        self.approve(p2)
        self.snapshot(equity=3000)
        with self.assertRaises(LedgerError):
            self.ledger.commit_revert(p2['seq'], actor='operator', reason='stale')
        self.assertEqual(self.ledger.entries()[-1]['state']['equity'], 3000)

    def test_nonstate_current_and_invalid_targets(self):
        p = self.proposal()
        self.approve(p)
        for target in (p['seq'], 2, 999, 0, True, '1'):
            with self.subTest(target=target), self.assertRaises(LedgerError):
                self.ledger.propose_revert(target, actor='requester', reason='bad target')

    def test_triggers_and_tampering_fail_closed(self):
        self.snapshot()
        with closing(sqlite3.connect(self.path)) as con, con:
            for sql in ('UPDATE audit_entries SET document=\'{}\'', 'DELETE FROM audit_entries'):
                with self.assertRaises(sqlite3.IntegrityError):
                    con.execute(sql)
            con.execute('DROP TRIGGER audit_no_update')
            row = self.ledger.entries()[0]
            row['state']['equity'] = 0
            con.execute('UPDATE audit_entries SET document=? WHERE seq=1', (json.dumps(row),))
        with self.assertRaises(IntegrityError):
            self.ledger.verify()
        with self.assertRaises(IntegrityError):
            self.snapshot()

    def test_trusted_checkpoint_detects_tail_truncation(self):
        self.snapshot()
        last = self.snapshot()
        checkpoint = (last['seq'], last['hash'])
        with closing(sqlite3.connect(self.path)) as con, con:
            con.execute('DROP TRIGGER audit_no_delete')
            con.execute('DELETE FROM audit_entries WHERE seq=2')
        self.assertTrue(self.ledger.verify()['ok'])  # A chain alone cannot detect this.
        with self.assertRaises(IntegrityError):
            self.ledger.verify(expected_head=checkpoint)

    def test_parallel_instances_serialize(self):
        def write(i):
            ledger = AuditLedger(self.path, scope='paper:XAUUSD')
            return ledger.record_snapshot(dict(STATE, equity=i), actor='worker', reason='offline concurrent test')
        with ThreadPoolExecutor(max_workers=6) as pool:
            entries = list(pool.map(write, range(18)))
        self.assertEqual(sorted(e['seq'] for e in entries), list(range(1, 19)))
        self.assertEqual(self.ledger.verify()['count'], 18)

    def test_schema_matches_all_workflow_entries(self):
        import jsonschema
        schema = json.loads(Path(__file__).with_name('audit_ledger.schema.json').read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema, format_checker=jsonschema.FormatChecker())
        p = self.proposal()
        self.approve(p)
        self.ledger.commit_revert(p['seq'], actor='operator', reason='paper only')
        p2 = self.ledger.propose_revert(2, actor='requester', reason='second proposal')
        self.ledger.decide_revert(p2['seq'], approve=False, actor='reviewer', reason='reject')
        for row in self.ledger.entries():
            validator.validate(row)
        bad = self.ledger.entries()[0]
        bad['state']['position_size'] = True
        with self.assertRaises(jsonschema.ValidationError):
            validator.validate(bad)

    def test_event_tuning_does_not_drop_storage_or_subscribers(self):
        # Import bus only after redirecting its module-level default away from live DB.
        spec = importlib.util.spec_from_file_location('offline_audit_event_bus', Path(__file__).with_name('event_bus.py'))
        module = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, {'SIGNAL_RELAY_EVENT_DB': str(Path(self.tmp.name) / 'default-events.db')}):
            spec.loader.exec_module(module)
        bus = module.EventBus(str(Path(self.tmp.name) / 'events.db'))
        received = []
        bus.subscribe('pnl_update', received.append)
        bus.publish({'type': 'pnl_update', 'source': 'offline', 'payload': STATE})
        bus.publish({'type': 'signal_received', 'source': 'offline', 'payload': {'symbol': 'XAUUSD'}})
        self.assertEqual(len(bus.history()), 2)
        self.assertEqual(len(bus.history(exclude='pnl_update')), 1)
        self.assertEqual(len(received), 1)
        self.assertEqual(EVENTS_URL, '/api/events?limit=100&exclude=pnl_update')
        # Memory fallback must apply the same filter.
        bus.db = str(Path(self.tmp.name) / 'missing' / 'events.db')
        self.assertEqual([e['type'] for e in bus.history(exclude='pnl_update')], ['signal_received'])


    def test_http_exclude_is_validated_forwarded_and_authenticated(self):
        from test_cockpit_api import CockpitHTTP
        # Entirely offline handler backend, real ephemeral loopback HTTP.
        with patch.dict(os.environ, {'TMPDIR': self.tmp.name}):
            CockpitHTTP.setUpClass()
        self.addCleanup(CockpitHTTP.tearDownClass)
        fixture = CockpitHTTP()
        for suffix in ('', '&stream=1'):
            code, _, _ = fixture.request(EVENTS_URL + suffix)
            self.assertEqual(code, 200)
            fixture.b.bus.history.assert_called_with(100, trace_id=None, exclude='pnl_update')
        self.assertEqual(fixture.request(EVENTS_URL, auth=False)[0], 401)
        self.assertEqual(fixture.request('/api/events?exclude=invalid%2Ctype')[0], 400)


if __name__ == '__main__':
    unittest.main()

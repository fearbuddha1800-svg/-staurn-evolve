---
slug: test_signal_evidence
type: note
graph: gitnexus
---

"""Offline tests: synthetic TEST fixtures only; no accounts or services."""
import ast
from dataclasses import replace, asdict
from datetime import timedelta
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from signal_evidence import (EvidenceError, SignalEvidence, OutcomeEvidence, Policy,
                             ShadowEngine, decode, fixture_records, stamp, replay,
                             json_default, strict_json)


BASE = stamp('2026-01-01T12:00:02+00:00')


def signal(index=0, **changes):
    data = fixture_records()[0]['data'].copy()
    t = BASE + timedelta(minutes=index * 20)
    data.update(message_id=f'TEST-{index}', correlation_id=f'TEST-cluster-{index}',
                original_at=(t - timedelta(seconds=2)).isoformat(),
                version_at=(t - timedelta(seconds=2)).isoformat(),
                received_at=t.isoformat(), feature_at=(t - timedelta(seconds=1)).isoformat(),
                quote_at=(t - timedelta(seconds=1)).isoformat())
    data.update(changes)
    return decode(SignalEvidence, data)


def outcome(decision, **changes):
    t = decision.decided_at
    data = dict(outcome_id='TEST-outcome-' + decision.decision_id,
                decision_id=decision.decision_id, mode='paper', status='completed',
                opened_at=t, closed_at=t + timedelta(seconds=30),
                observed_at=t + timedelta(seconds=31), gross_pnl=Decimal('25'),
                costs=Decimal('5'), initial_risk=Decimal('10'), currency='USD',
                evidence_ref='TEST-ledger-' + decision.decision_id, costs_complete=True)
    data.update(changes)
    return OutcomeEvidence(**data)


class SchemaTests(unittest.TestCase):
    def test_json_duplicate_keys_and_decimal_lexemes(self):
        for raw in ('{"version":1,"version":2}', '{"value":NaN}', '{"value":Infinity}'):
            with self.assertRaises(EvidenceError):
                strict_json(raw)
        for value in (' 1.1', '1_000', '+1.1', '01.1', '1e1000', '0.' + '1' * 40):
            with self.subTest(value=value), self.assertRaises(EvidenceError):
                signal(entry=value)

    def test_exact_keys_and_types(self):
        raw = fixture_records()[0]['data']
        for data in ({**raw, 'extra': 1}, {k: v for k, v in raw.items() if k != 'source'},
                     {**raw, 'version': True}, {**raw, 'version': '1'},
                     {**raw, 'entry': 1.1}, {**raw, 'source': ' '},
                     {**raw, 'content_hash': 'a'}, {**raw, 'correlation_id': None}):
            with self.subTest(data=data), self.assertRaises(EvidenceError):
                decode(SignalEvidence, data)

    def test_timezone_and_chronology(self):
        for changes in ({'original_at': '2026-01-01T12:00:00'},
                        {'original_at': '2026-01-02T12:00:00Z'},
                        {'version_at': '2026-01-01T12:00:01Z'}):
            with self.subTest(changes=changes), self.assertRaises(EvidenceError):
                signal(**changes)
        s = signal(original_at='2026-01-01T07:00:00-05:00',
                   version_at='2026-01-01T07:00:00-05:00')
        self.assertEqual(s.original_at, BASE - timedelta(seconds=2))

    def test_prices_precision_and_geometry(self):
        self.assertEqual(signal().entry, Decimal('1.10001'))
        for changes in ({'stop': '1.2'}, {'side': 'guess'}, {'ask': '1'},
                        {'entry': 'NaN'}, {'stop': '-1'}, {'target': 'Infinity'}):
            with self.subTest(changes=changes), self.assertRaises(EvidenceError):
                signal(**changes)
        self.assertEqual(signal(side='sell', stop='1.10201', target='1.09901').side, 'sell')

    def test_direct_constructor_strict(self):
        with self.assertRaises(EvidenceError):
            replace(signal(), entry=1.1)
        with self.assertRaises(EvidenceError):
            replace(signal(), received_at=BASE.replace(tzinfo=None))
        for changes in ({'max_age_s': True}, {'min_clusters': 1}, {'max_latency_s': 0}):
            with self.assertRaises(EvidenceError):
                Policy(**changes)


class DecisionTests(unittest.TestCase):
    def test_candidate_never_live(self):
        d = ShadowEngine().decide(signal(), now=BASE)
        self.assertEqual(d.disposition, 'shadow_candidate')
        self.assertIs(d.approved_for_live, False)

    def test_replay_conflict_and_source_version(self):
        e = ShadowEngine()
        s = signal()
        d = e.decide(s, now=BASE)
        self.assertEqual(e.decide(s, now=BASE).reason, 'replay')
        self.assertEqual(e.decide(replace(s, parser_version='changed'), now=BASE).reason, 'identity_conflict')
        self.assertEqual(e.decisions[d.decision_id], d)
        self.assertEqual(e.decide(replace(s, source_version='new-version'), now=BASE).reason,
                         'correlated_duplicate')

    def test_edits_never_new_entries(self):
        e = ShadowEngine()
        s = signal()
        e.decide(s, now=BASE)
        edited = replace(s, version=2, version_at=BASE, received_at=BASE + timedelta(seconds=1))
        self.assertEqual(e.decide(edited, now=edited.received_at).reason, 'edit_not_new_entry')
        self.assertEqual(ShadowEngine().decide(edited, now=edited.received_at).reason,
                         'edit_not_new_entry')

    def test_latency_age_quote_features(self):
        cases = [(replace(signal(), received_at=BASE + timedelta(seconds=70)),
                  BASE + timedelta(seconds=70), 'publication_latency'),
                 (signal(), BASE + timedelta(seconds=121), 'stale_signal'),
                 (replace(signal(), quote_at=BASE + timedelta(seconds=1)), BASE, 'future_features_or_quote'),
                 (replace(signal(), feature_at=BASE + timedelta(seconds=1)), BASE, 'future_features_or_quote'),
                 (replace(signal(), quote_at=BASE - timedelta(seconds=11)), BASE, 'stale_features_or_quote'),
                 (replace(signal(), feature_at=BASE - timedelta(seconds=11)), BASE, 'stale_features_or_quote'),
                 (signal(), BASE - timedelta(seconds=1), 'future_receipt')]
        for s, now, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(ShadowEngine().decide(s, now=now).reason, reason)

    def test_categories_and_order(self):
        for category in ('recap', 'management', 'ambiguous'):
            self.assertEqual(ShadowEngine().decide(signal(category=category), now=BASE).reason,
                             'not_entry')
        e = ShadowEngine()
        later = signal(1)
        e.decide(later, now=later.received_at)
        self.assertEqual(e.decide(signal(), now=BASE).reason, 'out_of_order_receipt')

    def test_correlation_no_independent_votes(self):
        e = ShadowEngine()
        d = e.decide(signal(), now=BASE)
        echo = replace(signal(), source='TEST-OTHER', message_id='echo', correlation_id='other',
                       received_at=BASE + timedelta(seconds=3))
        ed = e.decide(echo, now=echo.received_at)
        self.assertEqual(ed.reason, 'correlated_duplicate')
        self.assertEqual(ed.cluster_id, d.cluster_id)
        declared = signal(2, correlation_id='TEST-cluster-0', entry='1.2', stop='1.1', target='1.3')
        self.assertEqual(e.decide(declared, now=declared.received_at).reason, 'correlated_duplicate')
        separate = signal(3)
        self.assertEqual(e.decide(separate, now=separate.received_at).reason, 'eligible')


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.e = ShadowEngine()
        self.d = self.e.decide(signal(), now=BASE)
        self.o = outcome(self.d)
        self.now = BASE + timedelta(days=1)

    def test_cost_adjusted_r_and_modes(self):
        self.assertEqual(self.o.realized_r, Decimal('2'))
        self.assertEqual(self.e.record_outcome(self.o, now=self.now), 'recorded')
        broker = replace(self.o, outcome_id='TEST-broker', mode='broker', gross_pnl=Decimal('-5'))
        self.assertEqual(self.e.record_outcome(broker, now=self.now), 'recorded')
        reports = self.e.source_report(as_of=self.now, split_at=BASE + timedelta(hours=1))['sources']
        self.assertEqual({r['mode']: r['mean_realized_r'] for r in reports}, {'paper': 2, 'broker': -1})

    def test_invalid_completed_evidence(self):
        for changes in ({'costs': None}, {'costs_complete': False}, {'closed_at': None},
                        {'initial_risk': Decimal(0)}, {'costs': Decimal(-1)},
                        {'gross_pnl': Decimal('NaN')}, {'costs_complete': 1},
                        {'closed_at': BASE - timedelta(seconds=1)}):
            with self.subTest(changes=changes), self.assertRaises(EvidenceError):
                replace(self.o, **changes)

    def test_open_censored_not_labels(self):
        for status in ('open', 'censored'):
            o = replace(self.o, status=status, closed_at=None, gross_pnl=None, costs=None,
                        initial_risk=None, costs_complete=False)
            self.assertIsNone(o.realized_r)
            e = ShadowEngine()
            e.decide(signal(), now=BASE)
            self.assertEqual(e.record_outcome(o, now=self.now), 'recorded')
            r = e.source_report(as_of=self.now, split_at=BASE + timedelta(hours=1))['sources'][0]
            self.assertEqual(r['completed'], 0)
            self.assertEqual(r['open_or_censored'], 1)
            self.assertIsNone(r['mean_realized_r'])

    def test_attribution_replay_revision_and_future(self):
        self.assertEqual(self.e.record_outcome(replace(self.o, decision_id='missing'), now=self.now),
                         'unattributed_or_abstained_decision')
        self.assertEqual(self.e.record_outcome(self.o, now=BASE), 'future_or_predecision_outcome')
        early = replace(self.o, opened_at=BASE - timedelta(seconds=1))
        self.assertEqual(self.e.record_outcome(early, now=self.now), 'future_or_predecision_outcome')
        self.e.record_outcome(self.o, now=self.now)
        self.assertEqual(self.e.record_outcome(self.o, now=self.now), 'outcome_replay_or_conflict')
        self.assertEqual(self.e.record_outcome(replace(self.o, outcome_id='revision'), now=self.now),
                         'outcome_revision_conflict')

    def test_open_to_complete_and_fixed_risk(self):
        o = replace(self.o, outcome_id='open', status='open', closed_at=None,
                    gross_pnl=None, costs=None, costs_complete=False, observed_at=BASE)
        self.e.record_outcome(o, now=self.now)
        self.assertEqual(self.e.record_outcome(replace(self.o, initial_risk=Decimal('20')), now=self.now),
                         'outcome_revision_conflict')
        self.assertEqual(self.e.record_outcome(self.o, now=self.now), 'recorded')

    def test_duplicate_cash_evidence_cannot_be_reused(self):
        self.e.record_outcome(self.o, now=self.now)
        s = signal(1)
        d = self.e.decide(s, now=s.received_at)
        o = outcome(d, evidence_ref=self.o.evidence_ref)
        self.assertEqual(self.e.record_outcome(o, now=self.now), 'outcome_evidence_already_attributed')


class ReportTests(unittest.TestCase):
    def test_no_outcomes_no_profit_ranking(self):
        e = ShadowEngine()
        e.decide(signal(), now=BASE)
        report = e.source_report(as_of=BASE + timedelta(days=1), split_at=BASE + timedelta(hours=1))
        for r in report['sources']:
            self.assertEqual(r['evidence_state'], 'insufficient_evidence')
            self.assertEqual(r['missing_outcomes'], 1)
            self.assertIsNone(r['mean_r_interval_approx95'])
            self.assertIs(r['approved_for_live'], False)

    def test_boundary_purge_and_sample_threshold(self):
        e = ShadowEngine(Policy(min_clusters=4, min_split_clusters=2))
        for i in range(4):
            s = signal(i)
            d = e.decide(s, now=s.received_at)
            e.record_outcome(outcome(d, gross_pnl=Decimal(str(20 + i))), now=BASE + timedelta(days=1))
        report = e.source_report(as_of=BASE + timedelta(days=1), split_at=BASE + timedelta(minutes=30))
        r = next(r for r in report['sources'] if r['mode'] == 'paper')
        self.assertEqual((r['train_completed'], r['holdout_completed']), (2, 2))
        self.assertEqual(r['evidence_state'], 'descriptive_only')
        self.assertEqual(r['independent_clusters'], 4)
        self.assertLess(r['mean_r_interval_approx95'][0], r['mean_realized_r'])
        self.assertIs(r['approved_for_live'], False)
        report = e.source_report(as_of=BASE + timedelta(days=1), split_at=BASE + timedelta(seconds=15))
        r = next(r for r in report['sources'] if r['mode'] == 'paper')
        self.assertEqual(r['boundary_leakage_excluded'], 1)
        self.assertEqual(r['train_completed'], 0)
        self.assertEqual(r['evidence_state'], 'insufficient_evidence')

    def test_transitive_bridge_quarantines_and_preserves_asof(self):
        e = ShadowEngine()
        a = signal(0)
        b = signal(1, entry='1.2', stop='1.1', target='1.3')
        da = e.decide(a, now=a.received_at)
        db = e.decide(b, now=b.received_at)
        end = BASE + timedelta(days=1)
        e.record_outcome(outcome(da), now=end)
        e.record_outcome(outcome(db), now=end)
        cutoff = b.received_at + timedelta(seconds=32)
        bridge = replace(b, message_id='TEST-bridge', correlation_id=a.correlation_id,
                         received_at=cutoff + timedelta(seconds=1),
                         quote_at=cutoff, feature_at=cutoff)
        self.assertEqual(e.decide(bridge, now=bridge.received_at).reason, 'correlated_duplicate')
        before = e.source_report(as_of=cutoff, split_at=BASE - timedelta(seconds=1))['sources'][0]
        after = e.source_report(as_of=end, split_at=BASE - timedelta(seconds=1))['sources'][0]
        self.assertEqual(before['scored_completed'], 2)
        self.assertEqual(after['completed'], 2)
        self.assertEqual(after['scored_completed'], 0)
        self.assertEqual(after['correlation_excluded'], 2)
        self.assertIsNone(after['mean_realized_r'])

    def test_asof_preserves_open_history(self):
        e = ShadowEngine()
        d = e.decide(signal(), now=BASE)
        o = outcome(d)
        opened = replace(o, outcome_id='TEST-open', status='open', closed_at=None,
                         gross_pnl=None, costs=None, costs_complete=False,
                         observed_at=BASE + timedelta(seconds=1))
        end = BASE + timedelta(days=1)
        e.record_outcome(opened, now=end)
        e.record_outcome(o, now=end)
        r = e.source_report(as_of=BASE + timedelta(seconds=10),
                            split_at=BASE - timedelta(seconds=1))['sources'][0]
        self.assertEqual(r['open_or_censored'], 1)
        self.assertEqual(r['missing_outcomes'], 0)
        self.assertEqual(r['completed'], 0)

    def test_asof_excludes_later_labels(self):
        e = ShadowEngine()
        d = e.decide(signal(), now=BASE)
        e.record_outcome(outcome(d), now=BASE + timedelta(hours=1))
        report = e.source_report(as_of=BASE + timedelta(seconds=10), split_at=BASE - timedelta(seconds=1))
        self.assertEqual(report['sources'][0]['completed'], 0)
        with self.assertRaises(EvidenceError):
            e.source_report(as_of=BASE, split_at=BASE)


class CLITests(unittest.TestCase):
    def test_bad_records_abstain_not_repaired(self):
        records = fixture_records() + [{'kind': 'signal', 'data': {}}, {'unknown': 1}]
        output = replay(records, as_of=BASE + timedelta(hours=1), split_at=BASE - timedelta(days=1))
        self.assertEqual(len(output['rejected']), 2)
        self.assertEqual(output['decisions'][0]['disposition'], 'shadow_candidate')
        self.assertFalse(output['report']['approved_for_live'])

    def test_json_and_jsonl_cli_and_demo(self):
        script = str(Path(__file__).with_name('signal_evidence.py'))
        command = [sys.executable, script, '--as-of', '2026-01-01T13:00:00Z',
                   '--split-at', '2026-01-01T11:00:00Z']
        result = subprocess.run(command + ['--demo'], check=True, capture_output=True, text=True)
        self.assertTrue(json.loads(result.stdout)['test_fixture_only'])
        # Native Windows scratch only, no system temp directory.
        scratch = Path.home() / '.hermes/cache/scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            for suffix in ('.json', '.jsonl'):
                path = Path(directory) / ('TEST-fixtures' + suffix)
                records = fixture_records()
                s = decode(SignalEvidence, records[0]['data'])
                e = ShadowEngine()
                d = e.decide(s, now=s.received_at)
                records.append({'kind': 'outcome', 'data': asdict(outcome(d))})
                raw = json.dumps(records, default=json_default) if suffix == '.json' else '\n'.join(
                    json.dumps(r, default=json_default) for r in records)
                path.write_text(raw, encoding='utf-8')
                result = subprocess.run(command + ['--input', str(path)], check=True,
                                        capture_output=True, text=True)
                data = json.loads(result.stdout)
                self.assertEqual(data['outcomes'][0]['result'], 'recorded')
                self.assertEqual(data['report']['sources'][0]['completed'], 1)
                self.assertFalse(data['report']['approved_for_live'])

    def test_no_broker_or_network_imports(self):
        tree = ast.parse(Path(__file__).with_name('signal_evidence.py').read_text(encoding='utf-8'))
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports += [alias.name.split('.')[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module.split('.')[0])
        self.assertFalse(set(imports) & {'MetaTrader5', 'requests', 'socket', 'sqlite3', 'subprocess',
                                         'broker', 'execution', 'signal_source_audit'})


if __name__ == '__main__':
    unittest.main()


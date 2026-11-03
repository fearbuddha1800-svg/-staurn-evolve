import copy
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from source_intelligence import build_report, markdown, read_snapshot

NOW = datetime(2026, 10, 27, 12, tzinfo=timezone.utc)


def receipt(source='tg:a', mid='a:1', ts='2026-10-27T11:00:00Z', **fields):
    payload = dict(msg_id=mid, parsed=dict(is_signal=True, parse_ok=True,
        symbol='EURUSD', action='buy', entry=1.10001, sl=1.099, tps=[1.102]))
    payload.update(fields)
    return dict(ts=ts, source=source, payload=payload)


class IntelligenceTests(unittest.TestCase):
    def test_recent_is_not_approval(self):
        report = build_report([receipt()], now=NOW)
        source = report['sources'][0]
        self.assertEqual(source['observation_state'], 'recent_receipts')
        self.assertFalse(source['live_entry_approved'])
        self.assertIn('unknown', source['profitability'])

    def test_stale_receipts(self):
        report = build_report([receipt(ts='2026-10-20T12:00:00Z')], now=NOW)
        self.assertTrue(report['all_sources_stale'])
        self.assertEqual(report['sources'][0]['receipt_age_hours'], 168)

    def test_empty_not_vacuously_stale(self):
        self.assertIsNone(build_report([], now=NOW)['all_sources_stale'])

    def test_future_quarantined(self):
        report = build_report([receipt(ts='2026-10-28T12:00:00Z')], now=NOW)
        self.assertEqual(report['future_rows_quarantined'], 1)
        self.assertEqual(report['unique_messages'], 0)

    def test_invalid_rows(self):
        rows = [receipt(ts='bad'), receipt(ts='2026-10-27T11:00:00'),
                receipt(source=[]), receipt(payload='not json')]
        rows[-1]['payload'] = 'not json'
        self.assertEqual(build_report(rows, now=NOW)['invalid_rows'], 4)

    def test_integer_message_identity_deduped(self):
        report = build_report([receipt(mid=4), receipt(mid='4')], now=NOW)
        self.assertEqual(report['unique_messages'], 1)
        self.assertEqual(report['sources'][0]['counts']['replayed_events'], 1)

    def test_missing_identity_quarantined(self):
        report = build_report([receipt(mid=None), receipt(mid=True)], now=NOW)
        self.assertEqual(report['missing_identity_quarantined'], 2)

    def test_ocr_ai_count_unique_only(self):
        row = receipt(via_ocr=True, used_ai=True)
        source = build_report([row, row], now=NOW)['sources'][0]
        self.assertEqual(source['ocr'], {'messages': 1, 'parsed_candidates': 1})
        self.assertEqual(source['ai_extraction']['messages'], 1)

    def test_no_geometry_no_echo_rate(self):
        row = receipt()
        row['payload']['parsed']['entry'] = None
        source = build_report([row], now=NOW)['sources'][0]
        self.assertIsNone(source['cross_source_echo_fraction_of_comparable'])

    def test_cross_source_echo_and_denominator(self):
        report = build_report([receipt(), receipt(source='tg:b')], now=NOW)
        self.assertEqual(report['sources'][1]['cross_source_echo_fraction_of_comparable'], 1)
        self.assertEqual(len(report['duplicate_evidence']), 1)

    def test_bad_parsed_types_quarantined(self):
        rows = [receipt(parsed=[]), receipt(parsed={'is_signal': 'false'}),
                receipt(parsed={'is_signal': True, 'parse_ok': True, 'order_type': []})]
        report = build_report(rows, now=NOW)
        self.assertEqual(report['invalid_rows'], 3)
        self.assertEqual(report['unique_messages'], 0)

    def test_valid_json_object_and_timezone_offset(self):
        row = receipt(ts='2026-10-27T13:00:00+02:00')
        row['payload'] = json.dumps(row['payload'])
        self.assertEqual(build_report([row], now=NOW)['sources'][0]['receipt_age_hours'], 1)

    def test_no_mutation(self):
        rows = [receipt(mid=3)]
        before = copy.deepcopy(rows)
        build_report(rows, now=NOW)
        self.assertEqual(rows, before)

    def test_timezone_required_for_now(self):
        with self.assertRaises(ValueError):
            build_report([], now=datetime(2026, 10, 27))

    def test_markdown_not_performance(self):
        text = markdown(build_report([receipt()], now=NOW))
        self.assertIn('Parse yield is not win rate', text)
        self.assertIn('No source-to-realized-R linkage', text)

    def test_readonly_snapshot_and_unknown_labels(self):
        root = Path.home() / '.hermes/cache/scratch'
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            db = Path(tmp) / 'evidence.db'
            with closing(sqlite3.connect(db)) as c:
                c.execute('CREATE TABLE events(ts TEXT,source TEXT,payload TEXT,type TEXT)')
                row = receipt()
                c.execute('INSERT INTO events VALUES(?,?,?,?)',
                    (row['ts'], row['source'], json.dumps(row['payload']), 'signal_received'))
                c.commit()
            before = db.read_bytes()
            rows, labels = read_snapshot(db)
            self.assertEqual(len(rows), 1)
            self.assertIsNone(labels)
            self.assertEqual(db.read_bytes(), before)

    def test_label_counts_never_enable_training(self):
        report = build_report([], now=NOW, labels={'total': 500, 'finite_outcomes': 500})
        self.assertTrue(report['training_readiness'].startswith('not_evaluated'))


if __name__ == '__main__':
    unittest.main()

import copy
import json
import sqlite3
import tempfile
from pathlib import Path
import unittest
from signal_source_audit import audit, fingerprint, read_events


def row(source='tg:a', mid='a:1', second=0, **changes):
    parsed = dict(is_signal=True, parse_ok=True, symbol='XAUUSD', action='buy',
                  entry=4170, sl=4160, tps=[4180, 4190], order_type='market')
    parsed.update(changes)
    return dict(ts=f'2026-10-18T12:{second // 60:02d}:{second % 60:02d}Z', source=source,
                payload=dict(msg_id=mid, parsed=parsed))


class SourceAuditTests(unittest.TestCase):
    def test_cross_channel_echo(self):
        result = audit([row(), row('tg:b', 'b:1', 30)])
        self.assertEqual(result['sources']['tg:b']['cross_source_echo'], 1)
        self.assertEqual(result['echoes'][0]['first_observed_message'], 'a:1')

    def test_replay_not_new_signal(self):
        self.assertEqual(audit([row(), row()])['unique_messages'], 1)

    def test_same_channel_repeat(self):
        self.assertEqual(audit([row(), row(mid='a:2', second=2)])['sources']['tg:a']['same_source_repeat'], 1)

    def test_window_expires(self):
        self.assertFalse(audit([row(), row('tg:b', 'b:1', 600)])['echoes'])

    def test_distinct_stop_not_echo(self):
        self.assertFalse(audit([row(), row('tg:b', 'b:1', 1, sl=4150)])['echoes'])

    def test_market_missing_geometry_not_guessed(self):
        self.assertIsNone(fingerprint(row(entry='market')['payload']['parsed']))
        self.assertIsNone(fingerprint(row(action=None)['payload']['parsed']))

    def test_decimal_precision_preserved(self):
        a = row(symbol='EURUSD', entry=1.10001)['payload']['parsed']
        b = dict(a, entry=1.10002)
        self.assertNotEqual(fingerprint(a), fingerprint(b))

    def test_bad_numbers_rejected(self):
        for value in (True, float('nan'), float('inf'), -1, 0):
            self.assertIsNone(fingerprint(row(entry=value)['payload']['parsed']))

    def test_malformed_and_incomplete(self):
        result = audit([dict(ts='bad'), row(parse_ok=False), row(mid='a:2', is_signal=False)])
        self.assertEqual(result['malformed_events'], 1)
        self.assertEqual(result['sources']['tg:a']['needs_review'], 1)
        self.assertEqual(result['sources']['tg:a']['not_signal'], 1)

    def test_order_json_and_no_mutation(self):
        rows = [row('tg:b', 'b:1', 20), row()]
        before = copy.deepcopy(rows)
        rows[0]['payload'] = json.dumps(rows[0]['payload'])
        result = audit(rows)
        self.assertEqual(result['echoes'][0]['first_observed_source'], 'tg:a')
        self.assertEqual(rows[1], before[1])

    def test_readonly_database(self):
        with tempfile.TemporaryDirectory(dir=Path.home() / '.hermes/cache/scratch') as tmp:
            db = Path(tmp) / 'audit.db'
            with sqlite3.connect(db) as con:
                con.execute('CREATE TABLE events(ts TEXT, source TEXT, payload TEXT, type TEXT)')
                r = row()
                con.execute('INSERT INTO events VALUES(?,?,?,?)',
                            (r['ts'], r['source'], json.dumps(r['payload']), 'signal_received'))
            con.close()
            before = db.read_bytes()
            self.assertEqual(len(read_events(db)), 1)
            self.assertEqual(before, db.read_bytes())

    def test_invalid_window(self):
        with self.assertRaises(ValueError):
            audit([], 0)


if __name__ == '__main__':
    unittest.main()

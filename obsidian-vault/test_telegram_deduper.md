---
slug: test_telegram_deduper
type: note
graph: gitnexus
---

"""Isolated tests; no Telegram, MT5, config, or production database access."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
import tempfile
import unittest

from telegram_deduper import CHANNELS, TelegramDeduper, non_pnl_events

ENTRY = 'BUY XAUUSD @ 2650.5\nSL: 2640\nTP1: 2660 TP2: 2675'


class DedupeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = Path(self.tmp.name) / 'dedupe.sqlite'
        self.d = TelegramDeduper(self.db)
        self.channel = next(iter(CHANNELS))

    def test_five_channels(self):
        self.assertEqual(len(CHANNELS), 5)
        for channel in CHANNELS:
            self.assertEqual(self.d.process(channel, 1, ENTRY).status, 'candidate')

    def test_restart_replay(self):
        self.assertEqual(self.d.process(self.channel, 1, ENTRY).status, 'candidate')
        self.assertEqual(TelegramDeduper(self.db).process(self.channel, 1, ENTRY).status,
                         'duplicate')

    def test_edits_and_replay(self):
        self.d.process(self.channel, 1, ENTRY)
        edited = ENTRY.replace('2640', '2641')
        self.assertEqual(self.d.process(self.channel, 1, edited).status, 'edit_review')
        self.assertEqual(self.d.process(self.channel, 1, edited).status, 'duplicate')

    def test_distinct_messages_and_channels_survive(self):
        self.d.process(self.channel, 1, ENTRY)
        self.assertEqual(self.d.process(self.channel, 2, ENTRY).status, 'candidate')
        other = list(CHANNELS)[1]
        self.assertEqual(self.d.process(other, 1, ENTRY).status, 'candidate')

    def test_management_empty_and_missing_sl(self):
        self.assertEqual(self.d.process(self.channel, 1, 'Close XAUUSD now').status, 'not_entry')
        self.assertEqual(self.d.process(self.channel, 2, '').status, 'needs_ocr_or_empty')
        self.assertEqual(self.d.process(self.channel, 3, 'BUY XAUUSD @ 2650 TP 2660').status,
                         'missing_sl')

    def test_invalid_identities(self):
        for channel, message in [(1, 1), (str(self.channel), 1), (self.channel, 0),
                                 (self.channel, True)]:
            with self.assertRaises(ValueError):
                self.d.process(channel, message, ENTRY)

    def test_concurrent_atomic_claim(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.d.process(self.channel, 1, ENTRY).status,
                                    range(16)))
        self.assertEqual(results.count('candidate'), 1)
        self.assertEqual(results.count('duplicate'), 15)

    def test_event_exclusion_preserves_lifecycle_and_order(self):
        events = [{'type': 'pnl_update', 'ticket': 1} for _ in range(95)]
        lifecycle = [{'type': t} for t in ['trade_executed', 'sl_moved', 'tp_hit',
                                          'trade_closed', 'trade_closed']]
        self.assertEqual(list(non_pnl_events(events + lifecycle)), lifecycle)

    def test_metadata_persisted(self):
        metadata = {'reply_to_msg_id': 9, 'reply_to_peer_id': -100111,
                    'forward_from': 'source', 'edit_date': None}
        self.d.process(self.channel, 1, ENTRY, metadata=metadata)
        import json
        from contextlib import closing
        with closing(sqlite3.connect(self.db)) as conn:
            row = conn.execute('SELECT metadata_json FROM telegram_dedupe_receipts').fetchone()
        self.assertEqual(json.loads(row[0]), metadata)


if __name__ == '__main__':
    unittest.main()


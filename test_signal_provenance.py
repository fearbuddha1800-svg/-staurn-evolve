from datetime import datetime, timezone
from types import SimpleNamespace as NS
import unittest
from signal_provenance import telegram_provenance


class ProvenanceTests(unittest.TestCase):
    def test_missing_metadata_safe(self):
        result = telegram_provenance(-1001, NS(id=3))
        self.assertIsNone(result['reply_parent_trace'])
        self.assertFalse(result['is_forwarded'])

    def test_same_chat_reply(self):
        result = telegram_provenance(-1001, NS(id=3, reply_to_msg_id=2))
        self.assertEqual(result['reply_parent_trace'], '-1001:2')

    def test_header_fallback(self):
        result = telegram_provenance(-1001, NS(id=3, reply_to=NS(reply_to_msg_id=2)))
        self.assertEqual(result['reply_message_id'], 2)

    def test_cross_peer_no_guessed_parent(self):
        result = telegram_provenance(-1001, NS(id=3, reply_to=NS(reply_to_msg_id=2, reply_to_peer_id=NS(channel_id=99))))
        self.assertTrue(result['cross_peer_reply'])
        self.assertIsNone(result['reply_parent_trace'])

    def test_forward_and_timestamp(self):
        stamp = datetime(2026, 10, 18, tzinfo=timezone.utc)
        result = telegram_provenance(-1001, NS(id=3, date=stamp, fwd_from=NS(channel_post=7)))
        self.assertTrue(result['is_forwarded'])
        self.assertEqual(result['forwarded_channel_post'], 7)
        self.assertEqual(result['posted_at'], stamp.isoformat())


if __name__ == '__main__':
    unittest.main()

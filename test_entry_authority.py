"""Tests for executor.execute_algo - the SINGLE ALGO ENTRY AUTHORITY.

Verifies that algorithmic entries are routed through the same guards as the
Telegram path (masterbook section 4). No MT5 order is ever sent: mt5 and the
guard helpers are patched. Run: PYTHONPATH= python test_entry_authority.py
"""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import executor  # noqa: E402

PASS = 0
FAIL = 0


class AlgoAuthorityTests(unittest.TestCase):
    def setUp(self):
        # base patches: MT5 attached, symbol resolves, volume passes through
        self.patches = [
            mock.patch.object(executor, "load_config", return_value={"risk": {}, "sizing": {}}),
            mock.patch.object(executor, "resolve_symbol", return_value="XAUUSD"),
            mock.patch.object(executor, "_norm_volume", side_effect=lambda s, l: float(l)),
            mock.patch.object(executor, "_validate_stops", return_value=None),
            mock.patch.object(executor, "_record"),
            mock.patch.object(executor, "_emit_order_events"),
            mock.patch.object(executor, "tick_price", return_value=4150.0),
            mock.patch.object(executor, "_fill_type", return_value=1),
        ]
        for p in self.patches:
            p.start()
        self.mt5 = mock.MagicMock()
        self.mt5.terminal_info.return_value = object()  # attached
        self.mt5.symbol_select.return_value = True
        self.mt5.TRADE_ACTION_DEAL = 1
        self.mt5.ORDER_TYPE_BUY = 0
        self.mt5.ORDER_TYPE_SELL = 1
        self.mt5.ORDER_TIME_GTC = 0
        self.mt5.TRADE_RETCODE_DONE = 10009
        self.mt5_patch = mock.patch.object(executor, "mt5", self.mt5)
        self.mt5_patch.start()
        # news gate: no block by default
        self.news = mock.MagicMock()
        self.news.block_reason.return_value = None
        self.news_patch = mock.patch.dict(sys.modules, {"news_fetcher": self.news})
        self.news_patch.start()

    def tearDown(self):
        self.news_patch.stop()
        self.mt5_patch.stop()
        for p in self.patches:
            p.stop()

    def test_daily_cap_is_enforced(self):
        """The shared daily-cap guard must block an algo entry."""
        with mock.patch.object(executor, "_guards",
                               return_value=(False, "daily trade cap reached (20)")):
            r = executor.execute_algo("XAUUSD", "buy", 0.01, 4140.0, 0.0,
                                      msg_id="t1", strategy_name="rsi-pullback")
        self.assertNotEqual(r["status"], "executed")
        self.assertIn("daily trade cap", r["detail"])
        self.mt5.order_send.assert_not_called()

    def test_news_window_blocks_entry(self):
        """A High-USD news window must block an algo entry (same gate as signals)."""
        self.news.block_reason.return_value = "High-impact USD event in 2 min (NFP)"
        with mock.patch.object(executor, "_guards", return_value=(True, "")):
            r = executor.execute_algo("XAUUSD", "buy", 0.01, 4140.0, 0.0, msg_id="t2")
        self.assertEqual(r["status"], "skipped_news_window")
        self.mt5.order_send.assert_not_called()

    def test_unknown_symbol_rejected(self):
        with mock.patch.object(executor, "resolve_symbol", return_value=None):
            r = executor.execute_algo("NOPE", "buy", 0.01, 4140.0, 0.0, msg_id="t3")
        self.assertIn("not found", r["detail"])
        self.mt5.order_send.assert_not_called()

    def test_duplicate_msg_id_refused(self):
        """A replayed algo signal must be refused by the shared dedupe guard."""
        with mock.patch.object(executor, "_guards",
                               return_value=(False, "duplicate signal (already processed)")):
            r = executor.execute_algo("XAUUSD", "buy", 0.01, 4140.0, 0.0, msg_id="dup-1")
        self.assertIn("duplicate", r["detail"])
        self.mt5.order_send.assert_not_called()

    def test_dry_run_never_sends(self):
        with mock.patch.object(executor, "_guards", return_value=(True, "")):
            r = executor.execute_algo("XAUUSD", "buy", 0.01, 4140.0, 0.0,
                                      msg_id="t5", dry_run=True)
        self.assertEqual(r["status"], "dry_run_ok")
        self.mt5.order_send.assert_not_called()

    def test_executed_path_writes_ledger_and_emits(self):
        """A filled algo entry writes a ledger row and emits order events."""
        res = mock.MagicMock()
        res.retcode = 10009
        res.order = 555001
        res.price = 4150.5
        self.mt5.order_send.return_value = res
        with mock.patch.object(executor, "_guards", return_value=(True, "")):
            r = executor.execute_algo("XAUUSD", "buy", 0.01, 4140.0, 0.0,
                                      msg_id="t6", magic=20261015,
                                      strategy_name="london-breakout")
        self.assertEqual(r["status"], "executed")
        self.assertEqual(r["ticket"], 555001)
        self.assertEqual(r["lot"], 0.01)
        executor._record.assert_called_once()
        executor._emit_order_events.assert_called_once()
        # magic must be stamped on the broker request
        sent = self.mt5.order_send.call_args[0][0]
        self.assertEqual(sent["magic"], 20261015)
        self.assertEqual(sent["sl"], 4140.0)
        self.assertIn("london-breakout", sent["comment"])

    def test_broker_reject_is_recorded_not_hidden(self):
        res = mock.MagicMock()
        res.retcode = 10016
        res.comment = "Invalid stops"
        res.order = 0
        self.mt5.order_send.return_value = res
        with mock.patch.object(executor, "_guards", return_value=(True, "")):
            r = executor.execute_algo("XAUUSD", "buy", 0.01, 4140.0, 0.0, msg_id="t7")
        self.assertEqual(r["status"], "broker_rejected")
        self.assertIn("10016", r["detail"])
        executor._record.assert_called_once()

    def test_telegram_execute_unchanged(self):
        """The Telegram authority must still exist and be separate."""
        self.assertTrue(callable(getattr(executor, "execute", None)))
        self.assertTrue(callable(getattr(executor, "execute_algo", None)))
        self.assertIsNot(executor.execute, executor.execute_algo)


if __name__ == "__main__":
    unittest.main(verbosity=2)

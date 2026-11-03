"""Offline tests for reconciliation.py - broker send reconciliation.

Every test runs against a FAKE mt5 handle: no MT5 terminal, no orders, no
network. The reconciler is read-only by contract - several tests assert
``order_send`` is NEVER called, proving reconciliation cannot place an order.

Run:  PYTHONPATH= C:/Users/voidk/miniconda3/python.exe -m pytest test_reconciliation.py -v
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import reconciliation as rec  # noqa: E402

MAGIC = 20261014
ALGO_MAGIC = 20261015
SYMBOL = "EURUSD"


# ---- fake broker -------------------------------------------------------------
class FakePosition:
    def __init__(self, ticket, symbol=SYMBOL, type=0, volume=0.10,
                 price_open=1.10000, sl=1.09000, tp=0.0, magic=MAGIC,
                 comment="sigrelay m-1", time=1760000000, profit=0.0,
                 swap=0.0, price_current=1.10050):
        self.ticket, self.symbol, self.type = ticket, symbol, type
        self.volume, self.price_open, self.sl, self.tp = volume, price_open, sl, tp
        self.magic, self.comment, self.time = magic, comment, time
        self.profit, self.swap, self.price_current = profit, swap, price_current


class FakeDeal:
    def __init__(self, ticket, order=0, time=1760000000, type=0, entry=0,
                 magic=MAGIC, position_id=0, symbol=SYMBOL, volume=0.10,
                 price=1.10000, profit=0.0, commission=0.0, swap=0.0,
                 fee=0.0, comment="sigrelay m-1", external_id=""):
        self.ticket, self.order, self.time = ticket, order, time
        self.type, self.entry, self.magic = type, entry, magic
        self.position_id, self.symbol, self.volume = position_id, symbol, volume
        self.price, self.profit, self.commission = price, profit, commission
        self.swap, self.fee, self.comment, self.external_id = swap, fee, comment, external_id


class FakeOrder:
    def __init__(self, ticket, time_setup=1760000000, type=0, magic=MAGIC,
                 symbol=SYMBOL, volume_initial=0.10, price_open=1.10000,
                 sl=1.09000, tp=0.0, comment="sigrelay m-1", state=1):
        self.ticket, self.time_setup, self.type = ticket, time_setup, type
        self.magic, self.symbol, self.volume_initial = magic, symbol, volume_initial
        self.price_open, self.sl, self.tp, self.comment, self.state = price_open, sl, tp, comment, state


class FakeMT5:
    """In-memory fake of the read-only MT5 surface the reconciler uses."""

    # documented MQL5 constants
    DEAL_ENTRY_IN, DEAL_ENTRY_OUT, DEAL_ENTRY_INOUT = 0, 1, 2
    POSITION_TYPE_BUY, POSITION_TYPE_SELL = 0, 1
    TRADE_RETCODE_DONE, TRADE_RETCODE_PLACED = 10009, 10008

    def __init__(self, positions=(), deals=(), orders=()):
        self.positions = list(positions)
        self.deals = list(deals)
        self.orders = list(orders)
        self.order_send = mock.Mock()  # must never be called
        self.calls = []

    def positions_get(self, symbol=None):
        self.calls.append(("positions_get", symbol))
        return tuple(p for p in self.positions
                     if symbol is None or p.symbol == symbol)

    def history_deals_get(self, date_from, date_to, symbol=None):
        self.calls.append(("history_deals_get", date_from, date_to, symbol))
        return tuple(d for d in self.deals
                     if symbol is None or d.symbol == symbol)

    def history_orders_get(self, date_from, date_to, symbol=None):
        self.calls.append(("history_orders_get", date_from, date_to, symbol))
        return tuple(o for o in self.orders
                     if symbol is None or o.symbol == symbol)

    def symbol_info(self, symbol):
        return SimpleNamespace(point=0.00001, digits=5, trade_tick_size=0.00001)


class BrokenMT5(FakeMT5):
    """Simulates a dead terminal: every read returns None (API error)."""
    def positions_get(self, symbol=None):
        self.calls.append(("positions_get", symbol))
        return None

    def history_deals_get(self, date_from, date_to, symbol=None):
        self.calls.append(("history_deals_get", date_from, date_to, symbol))
        return None

    def history_orders_get(self, date_from, date_to, symbol=None):
        self.calls.append(("history_orders_get", date_from, date_to, symbol))
        return None


class RaisingMT5(FakeMT5):
    """Simulates a connection drop: reads raise."""
    def positions_get(self, symbol=None):
        raise ConnectionError("IPC pipe closed")


# ---- 1. lost ack that actually filled ----------------------------------------
class LostAckFilled(unittest.TestCase):
    def test_position_match_confirms_fill(self):
        """order_send returned None, but the position is live at the broker."""
        pos = FakePosition(ticket=777001, volume=0.10, price_open=1.10025,
                           sl=1.09000, comment="sigrelay m-42")
        mt5 = FakeMT5(positions=[pos])
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-42", requested_volume=0.10,
                               expected_sl=1.09000, comment="sigrelay m-42")
        self.assertEqual(r.status, rec.STATUS_FILLED)
        self.assertFalse(r.safe_to_retry)
        self.assertEqual(r.ticket, 777001)
        self.assertEqual(r.fill_price, 1.10025)
        self.assertEqual(r.filled_volume, 0.10)
        self.assertFalse(r.partial)
        self.assertEqual(r.native_stop["state"], "attached")
        self.assertEqual(r.evidence["source"], "positions_get")
        mt5.order_send.assert_not_called()

    def test_deal_match_when_position_closed(self):
        """Position already closed: the fill deal still proves the order landed."""
        deal = FakeDeal(ticket=9001, order=777002, position_id=777002,
                        volume=0.10, price=1.10010, entry=0,
                        comment="sigrelay m-43")
        mt5 = FakeMT5(deals=[deal])
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-43", requested_volume=0.10,
                               comment="sigrelay m-43")
        self.assertEqual(r.status, rec.STATUS_FILLED)
        self.assertEqual(r.ticket, 777002)          # position_id
        self.assertEqual(r.deal_ticket, 9001)
        self.assertEqual(r.fill_price, 1.10010)
        self.assertFalse(r.safe_to_retry)
        mt5.order_send.assert_not_called()

    def test_ticket_hint_matches_deal_via_order_field(self):
        """Caller saw a PLACED ack (order 777003) before the timeout; the deal
        references that order id."""
        deal = FakeDeal(ticket=9002, order=777003, position_id=777003,
                        volume=0.10, price=1.10010, entry=0, magic=ALGO_MAGIC,
                        comment="algo rsi-pullback")  # no msg_id in comment
        mt5 = FakeMT5(deals=[deal])
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=ALGO_MAGIC,
                               msg_id="", requested_volume=0.10,
                               comment="algo rsi-pullback",
                               ticket_hint=777003)
        self.assertEqual(r.status, rec.STATUS_FILLED)
        self.assertEqual(r.evidence["match_strength"], "ticket")
        self.assertEqual(r.ticket, 777003)

    def test_exit_deal_is_reported_as_evidence(self):
        """Exit read-back: an OUT deal for the same identity is noted."""
        fill = FakeDeal(ticket=9003, order=777004, position_id=777004,
                        volume=0.10, price=1.10010, entry=0,
                        comment="sigrelay m-44")
        exit_ = FakeDeal(ticket=9004, order=777004, position_id=777004,
                         volume=0.10, price=1.10500, entry=1,
                         comment="sigrelay m-44")
        mt5 = FakeMT5(deals=[fill, exit_])
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-44", requested_volume=0.10,
                               comment="sigrelay m-44")
        self.assertEqual(r.status, rec.STATUS_FILLED)
        self.assertEqual(r.evidence["exit_deal_ticket"], 9004)


# ---- 2. lost ack that never landed -------------------------------------------
class LostAckAbsent(unittest.TestCase):
    def test_empty_reads_mean_safe_to_retry(self):
        mt5 = FakeMT5()  # nothing anywhere
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-50", requested_volume=0.10,
                               comment="sigrelay m-50")
        self.assertEqual(r.status, rec.STATUS_ABSENT)
        self.assertTrue(r.safe_to_retry)
        self.assertIsNone(r.ticket)
        self.assertEqual(r.evidence["source"], "read_back_empty")
        mt5.order_send.assert_not_called()

    def test_other_magic_position_does_not_match(self):
        """A live position from the ALGO engine must not confirm a signal-relay
        order, and vice versa."""
        pos = FakePosition(ticket=777010, magic=ALGO_MAGIC,
                           comment="algo rsi-pullback")
        mt5 = FakeMT5(positions=[pos])
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-51", requested_volume=0.10,
                               comment="sigrelay m-51")
        self.assertEqual(r.status, rec.STATUS_ABSENT)
        self.assertTrue(r.safe_to_retry)

    def test_same_magic_different_comment_does_not_match(self):
        """Same magic, different msg_id: not our order -> absent."""
        pos = FakePosition(ticket=777011, magic=MAGIC, comment="sigrelay m-99")
        mt5 = FakeMT5(positions=[pos])
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-52", requested_volume=0.10,
                               comment="sigrelay m-52")
        self.assertEqual(r.status, rec.STATUS_ABSENT)
        self.assertTrue(r.safe_to_retry)


# ---- 3. unknown / timeout ------------------------------------------------------
class UnknownStates(unittest.TestCase):
    def test_none_read_is_unknown_not_absent(self):
        """positions_get returning None is an API error, NOT an empty account.
        Must be UNKNOWN: retrying blind could duplicate."""
        mt5 = BrokenMT5()
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-60", requested_volume=0.10,
                               comment="sigrelay m-60")
        self.assertEqual(r.status, rec.STATUS_UNKNOWN)
        self.assertFalse(r.safe_to_retry)
        self.assertIn("positions_get", r.detail)
        mt5.order_send.assert_not_called()

    def test_raising_read_is_unknown(self):
        mt5 = RaisingMT5()
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-61", requested_volume=0.10,
                               comment="sigrelay m-61")
        self.assertEqual(r.status, rec.STATUS_UNKNOWN)
        self.assertFalse(r.safe_to_retry)

    def test_unmatched_same_magic_order_in_window_is_unknown(self):
        """A same-magic order we cannot identify inside the window: ambiguous,
        surface for operator review rather than guessing."""
        other = FakeOrder(ticket=777020, magic=MAGIC, comment="sigrelay m-99")
        mt5 = FakeMT5(orders=[other])
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-62", requested_volume=0.10,
                               comment="sigrelay m-62")
        self.assertEqual(r.status, rec.STATUS_UNKNOWN)
        self.assertFalse(r.safe_to_retry)
        self.assertIn("unmatched_same_magic", r.evidence["read_errors"])

    def test_placed_not_filled_is_confirmed_placed(self):
        """10008 PLACED: order accepted at broker, not a fill. Never resubmit."""
        pend = FakeOrder(ticket=777030, magic=MAGIC, comment="sigrelay m-63")
        mt5 = FakeMT5(orders=[pend])
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-63", requested_volume=0.10,
                               comment="sigrelay m-63")
        self.assertEqual(r.status, rec.STATUS_PLACED)
        self.assertFalse(r.safe_to_retry)
        self.assertEqual(r.ticket, 777030)
        self.assertEqual(r.evidence["source"], "history_orders_get")


# ---- 4. partial fills -----------------------------------------------------------
class PartialFills(unittest.TestCase):
    def test_position_partial_fill_reports_both_volumes(self):
        pos = FakePosition(ticket=777040, volume=0.07, price_open=1.10025,
                           sl=1.09000, comment="sigrelay m-70")
        mt5 = FakeMT5(positions=[pos])
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-70", requested_volume=0.10,
                               expected_sl=1.09000, comment="sigrelay m-70")
        self.assertEqual(r.status, rec.STATUS_FILLED)
        self.assertTrue(r.partial)
        self.assertEqual(r.partial_info["filled"], 0.07)
        self.assertEqual(r.partial_info["requested"], 0.10)
        self.assertEqual(r.partial_info["remaining"], 0.03)
        self.assertAlmostEqual(r.partial_info["fill_ratio"], 0.7)

    def test_deal_partial_fill(self):
        deal = FakeDeal(ticket=9010, order=777041, position_id=777041,
                        volume=0.04, price=1.10010, entry=0,
                        comment="sigrelay m-71")
        mt5 = FakeMT5(deals=[deal])
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-71", requested_volume=0.10,
                               comment="sigrelay m-71")
        self.assertEqual(r.status, rec.STATUS_FILLED)
        self.assertTrue(r.partial)
        self.assertEqual(r.filled_volume, 0.04)
        self.assertEqual(r.partial_info["remaining"], 0.06)

    def test_full_fill_is_not_partial(self):
        pos = FakePosition(ticket=777042, volume=0.10, comment="sigrelay m-72")
        mt5 = FakeMT5(positions=[pos])
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-72", requested_volume=0.10,
                               comment="sigrelay m-72")
        self.assertFalse(r.partial)
        self.assertIsNone(r.partial_info)


# ---- 5. native stop verification -------------------------------------------------
class NativeStop(unittest.TestCase):
    def test_stop_attached_at_expected_distance(self):
        pos = FakePosition(ticket=777050, price_open=1.10000, sl=1.09000,
                           comment="sigrelay m-80")
        mt5 = FakeMT5(positions=[pos])
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-80", requested_volume=0.10,
                               expected_sl=1.09000, comment="sigrelay m-80")
        self.assertEqual(r.native_stop["state"], "attached")
        self.assertEqual(r.native_stop["actual_sl"], 1.09000)
        self.assertAlmostEqual(r.native_stop["expected_distance"], 0.01)
        self.assertAlmostEqual(r.native_stop["actual_distance"], 0.01)

    def test_missing_native_stop_is_reported(self):
        """Position live with NO protective stop: report, never assume."""
        pos = FakePosition(ticket=777051, price_open=1.10000, sl=0.0,
                           comment="sigrelay m-81")
        mt5 = FakeMT5(positions=[pos])
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-81", requested_volume=0.10,
                               expected_sl=1.09000, comment="sigrelay m-81")
        self.assertEqual(r.status, rec.STATUS_FILLED)
        self.assertEqual(r.native_stop["state"], "missing")
        self.assertIn("NATIVE STOP MISSING", r.native_stop["detail"])

    def test_mismatched_native_stop_is_reported(self):
        """Stop exists but at the WRONG level: report both levels."""
        pos = FakePosition(ticket=777052, price_open=1.10000, sl=1.09500,
                           comment="sigrelay m-82")
        mt5 = FakeMT5(positions=[pos])
        r = rec.reconcile_send(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-82", requested_volume=0.10,
                               expected_sl=1.09000, comment="sigrelay m-82",
                               sl_tolerance=0.00010)
        self.assertEqual(r.native_stop["state"], "mismatch")
        self.assertEqual(r.native_stop["actual_sl"], 1.09500)
        self.assertEqual(r.native_stop["expected_sl"], 1.09000)
        self.assertIn("MISMATCH", r.native_stop["detail"])

    def test_verify_native_stop_standalone_unknown_when_position_gone(self):
        mt5 = FakeMT5()
        out = rec.verify_native_stop(mt5, symbol=SYMBOL, ticket=999999,
                                     expected_sl=1.09000)
        self.assertEqual(out["state"], "unknown")
        self.assertIn("not visible", out["detail"])

    def test_verify_native_stop_not_requested_reports_actuals(self):
        pos = FakePosition(ticket=777053, sl=1.08990, tp=1.12000)
        out = rec.verify_native_stop(FakeMT5(), position=pos)
        self.assertEqual(out["state"], "not_requested")
        self.assertEqual(out["actual_sl"], 1.08990)
        self.assertEqual(out["actual_tp"], 1.12000)


# ---- 6. idempotence / duplicate suppression ---------------------------------------
class Idempotence(unittest.TestCase):
    def test_second_reconcile_same_identity_is_suppressed(self):
        """Once CONFIRMED_FILLED, the same msg_id must never recommend a second
        submission - even if the broker state has since changed."""
        pos = FakePosition(ticket=777060, comment="sigrelay m-90")
        mt5 = FakeMT5(positions=[pos])
        recr = rec.Reconciler()
        first = recr.reconcile(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-90", requested_volume=0.10,
                               expected_sl=1.09000, comment="sigrelay m-90")
        self.assertEqual(first.status, rec.STATUS_FILLED)
        self.assertFalse(first.duplicate)
        # broker now empty (position closed) - retry must still be suppressed
        mt5.positions = []
        second = recr.reconcile(mt5, symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-90", requested_volume=0.10,
                               expected_sl=1.09000, comment="sigrelay m-90")
        self.assertTrue(second.duplicate)
        self.assertEqual(second.status, rec.STATUS_FILLED)
        self.assertFalse(second.safe_to_retry)
        self.assertIn("duplicate suppressed", second.detail)
        self.assertEqual(second.ticket, 777060)

    def test_placed_identity_is_also_suppressed(self):
        pend = FakeOrder(ticket=777061, comment="sigrelay m-91")
        recr = rec.Reconciler()
        first = recr.reconcile(FakeMT5(orders=[pend]), symbol=SYMBOL,
                               side="buy", magic=MAGIC, msg_id="m-91",
                               requested_volume=0.10, comment="sigrelay m-91")
        self.assertEqual(first.status, rec.STATUS_PLACED)
        second = recr.reconcile(FakeMT5(), symbol=SYMBOL, side="buy",
                                magic=MAGIC, msg_id="m-91",
                                requested_volume=0.10, comment="sigrelay m-91")
        self.assertTrue(second.duplicate)
        self.assertFalse(second.safe_to_retry)

    def test_absent_does_not_poison_identity(self):
        """CONFIRMED_ABSENT is not a confirmation: a later reconcile may retry."""
        recr = rec.Reconciler()
        first = recr.reconcile(FakeMT5(), symbol=SYMBOL, side="buy",
                               magic=MAGIC, msg_id="m-92", requested_volume=0.10,
                               comment="sigrelay m-92")
        self.assertEqual(first.status, rec.STATUS_ABSENT)
        self.assertIsNone(recr.is_confirmed(MAGIC, "m-92"))
        pos = FakePosition(ticket=777062, comment="sigrelay m-92")
        second = recr.reconcile(FakeMT5(positions=[pos]), symbol=SYMBOL,
                                side="buy", magic=MAGIC, msg_id="m-92",
                                requested_volume=0.10, comment="sigrelay m-92")
        self.assertEqual(second.status, rec.STATUS_FILLED)
        self.assertFalse(second.duplicate)

    def test_different_msg_id_is_a_distinct_identity(self):
        recr = rec.Reconciler()
        recr.reconcile(FakeMT5(), symbol=SYMBOL, side="buy", magic=MAGIC,
                       msg_id="m-93", requested_volume=0.10,
                       comment="sigrelay m-93")
        other = recr.reconcile(FakeMT5(), symbol=SYMBOL, side="buy", magic=MAGIC,
                               msg_id="m-94", requested_volume=0.10,
                               comment="sigrelay m-94")
        self.assertFalse(other.duplicate)

    def test_registry_persists_across_instances(self):
        """A crash after confirmation must not reopen the duplicate window."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "reconcile-state.json")
            pos = FakePosition(ticket=777063, comment="sigrelay m-95")
            recr = rec.Reconciler(state_path=path)
            recr.reconcile(FakeMT5(positions=[pos]), symbol=SYMBOL, side="buy",
                           magic=MAGIC, msg_id="m-95", requested_volume=0.10,
                           comment="sigrelay m-95")
            self.assertTrue(os.path.exists(path))
            # new process, empty broker: still suppressed
            recr2 = rec.Reconciler(state_path=path)
            again = recr2.reconcile(FakeMT5(), symbol=SYMBOL, side="buy",
                                    magic=MAGIC, msg_id="m-95",
                                    requested_volume=0.10,
                                    comment="sigrelay m-95")
            self.assertTrue(again.duplicate)
            self.assertFalse(again.safe_to_retry)
            self.assertEqual(again.ticket, 777063)


# ---- 7. executor integration (guarded call site) ------------------------------------
class ExecutorIntegration(unittest.TestCase):
    """The executor's lost-ack path annotates the result with a reconciliation
    outcome. Reconciliation failure must never break the execution path."""

    def setUp(self):
        import executor
        self.executor = executor
        self.patches = [
            mock.patch.object(executor, "load_config",
                              return_value={"risk": {}, "sizing": {}}),
            mock.patch.object(executor, "resolve_symbol", return_value=SYMBOL),
            mock.patch.object(executor, "_norm_volume",
                              side_effect=lambda s, l: float(l)),
            mock.patch.object(executor, "_validate_stops", return_value=None),
            mock.patch.object(executor, "_record"),
            mock.patch.object(executor, "_emit_order_events"),
            mock.patch.object(executor, "tick_price", return_value=1.10000),
            mock.patch.object(executor, "_fill_type", return_value=1),
            mock.patch.object(executor, "_guards", return_value=(True, "")),
        ]
        for p in self.patches:
            p.start()
        self.mt5 = mock.MagicMock()
        self.mt5.terminal_info.return_value = object()      # attached
        self.mt5.symbol_select.return_value = True
        self.mt5.account_info.return_value = None
        self.mt5.positions_total.return_value = 0
        self.mt5.order_send.return_value = None            # LOST ACK
        self.mt5.last_error.return_value = (10012, "timeout")
        self.mt5.positions_get.return_value = ()           # reconciler reads
        self.mt5.history_deals_get.return_value = ()
        self.mt5.history_orders_get.return_value = ()
        self.mt5.symbol_info.return_value = SimpleNamespace(
            point=0.00001, digits=5, trade_tick_size=0.00001)
        self.mt5_patch = mock.patch.object(executor, "mt5", self.mt5)
        self.mt5_patch.start()
        self.news = mock.MagicMock()
        self.news.block_reason.return_value = None
        self.news_patch = mock.patch.dict(sys.modules,
                                          {"news_fetcher": self.news})
        self.news_patch.start()

    def tearDown(self):
        self.news_patch.stop()
        self.mt5_patch.stop()
        for p in self.patches:
            p.stop()

    def test_lost_ack_annotates_result_with_reconciliation(self):
        r = self.executor.execute({"symbol": "EURUSD", "action": "buy",
                                   "sl": 1.09000, "tps": []},
                                  msg_id="m-100")
        self.assertIn("reconciliation", r)
        self.assertEqual(r["reconciliation"]["status"], rec.STATUS_ABSENT)
        self.assertTrue(r["reconciliation"]["safe_to_retry"])
        self.assertIn("reconciled: CONFIRMED_ABSENT", r["detail"])
        # exactly one send: the original lost-ack attempt. The reconciler
        # must never add a second submission.
        self.assertEqual(self.mt5.order_send.call_count, 1)

    def test_lost_ack_that_filled_is_flagged_do_not_retry(self):
        self.mt5.positions_get.return_value = [
            FakePosition(ticket=777100, volume=0.10, price_open=1.10025,
                         sl=1.09000, comment="sigrelay m-101")]
        r = self.executor.execute({"symbol": "EURUSD", "action": "buy",
                                   "sl": 1.09000, "tps": []},
                                  msg_id="m-101")
        self.assertEqual(r["reconciliation"]["status"], rec.STATUS_FILLED)
        self.assertFalse(r["reconciliation"]["safe_to_retry"])
        self.assertEqual(r["reconciliation"]["ticket"], 777100)
        self.assertIn("reconciled: CONFIRMED_FILLED", r["detail"])

    def test_reconciliation_failure_never_breaks_execution(self):
        """If the reconciler itself blows up, the executor still returns a
        normal result (guarded call site)."""
        with mock.patch.object(rec, "reconcile_send",
                               side_effect=RuntimeError("boom")):
            r = self.executor.execute({"symbol": "EURUSD", "action": "buy",
                                       "sl": 1.09000, "tps": []},
                                      msg_id="m-102")
        self.assertIn("order_send returned None", r["detail"])
        self.assertIn("reconciliation unavailable", r["detail"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

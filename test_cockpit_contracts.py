"""Offline backend contracts. No live MT5 attach, orders, shared DB or services."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent


def load_backend():
    name = '_cockpit_contract_backend'
    spec = importlib.util.spec_from_file_location(name, ROOT / 'cockpit.py')
    backend = importlib.util.module_from_spec(spec)
    bus = ModuleType('event_bus')
    bus.bus = SimpleNamespace(history=Mock(return_value=[]))
    fake_mt5 = ModuleType('MetaTrader5')
    disabled = {k: None for k in ('signal_inbox', 'event_journal', 'mobile_view', 'edge_stats_bridge', 'scalp360_bridge')}
    with patch.dict(sys.modules, {'event_bus': bus, 'MetaTrader5': fake_mt5, name: backend, **disabled}):
        spec.loader.exec_module(backend)
    # quant_data/compile_pine use sys.modules for their dependency injection.
    sys.modules[name] = backend
    return backend


class BackendContracts(unittest.TestCase):
    def setUp(self):
        self.b = load_backend()
        scratch = os.environ.get('TMPDIR') or str(ROOT / '.cache')
        Path(scratch).mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        b = self.b
        b.BASE = self.tmp.name
        b.CONFIG = str(Path(b.BASE, 'config.json'))
        b.REPORT = str(Path(b.BASE, 'absent-report.json'))
        b._stage = lambda name: contextlib.nullcontext()
        for name, value in {'engines': {}, 'ledger': [], 'inbox_data': [], 'journal_data': [],
                            'mobile_html': '', 'neural_label_count': 0, 'pine_strategies': []}.items():
            setattr(b, name, Mock(return_value=value))
        b.socket = SimpleNamespace(create_connection=Mock(side_effect=OSError))
        b.mt5 = Mock(POSITION_TYPE_BUY=0, POSITION_TYPE_SELL=1)
        b.mt5.terminal_info.return_value = SimpleNamespace()
        b.mt5.account_info.return_value = None
        b.mt5.positions_get.return_value = None
        b.mt5.history_deals_get.return_value = None

    def test_unavailable_is_not_zero_or_confirmed_empty(self):
        s = self.b.state()
        self.assertIsNone(s['account']['balance'])
        self.assertFalse(s['mt5']['account_available'])
        self.assertFalse(s['mt5']['positions_available'])
        self.assertFalse(s['day_pl']['available'])
        self.assertIsNone(s['day_pl']['total'])
        self.b.mt5.positions_get.return_value = ()
        self.b.mt5.history_deals_get.return_value = ()
        s = self.b.state()
        self.assertTrue(s['mt5']['positions_available'])
        self.assertTrue(s['day_pl']['available'])
        self.assertEqual(s['day_pl']['total'], 0)

    def test_price_r_direction_units_and_no_current_stop_fallback(self):
        positions = [SimpleNamespace(ticket=i, symbol='EURUSD', type=side, volume=0.1,
                     price_open=1.1, price_current=price, profit=900, swap=-1, sl=1.1,
                     tp=0, magic=0, time=1700000000) for i, side, price in
                     ((1, 0, 1.102), (2, 1, 1.098), (3, 0, 1.102))]
        Path(self.b.BASE, 'manage-state.json').write_text(json.dumps({'1': {'r': .001}, '2': {'r': .001}}))
        self.b.mt5.positions_get.return_value = positions
        rows = self.b.state()['positions']
        self.assertEqual([r['r_multiple'] for r in rows], [2, 2, None])
        self.assertEqual(rows[0]['r'], .001)
        self.assertEqual(rows[0]['r_units'], 'symbol_price')
        self.b.mt5.order_send.assert_not_called()
        self.b.mt5.symbol_select.assert_not_called()

    def test_account_error_does_not_erase_positions(self):
        self.b.mt5.account_info.side_effect = RuntimeError
        self.b.mt5.positions_get.return_value = ()
        self.assertTrue(self.b.state()['mt5']['positions_available'])

    def test_history_costs_and_split(self):
        self.b.mt5.history_deals_get.return_value = [SimpleNamespace(profit=10, commission=-2,
              swap=-1, fee=-.5, magic=20261014), SimpleNamespace(profit=-3, commission=0,
              swap=0, magic=20261015)]
        self.assertEqual(self.b.day_pl(), (3.5, 6.5, -3))

    def test_candles_unknown_and_broker_timestamp(self):
        m = self.b.mt5
        m.symbol_info.return_value = SimpleNamespace()
        m.copy_rates_from_pos.return_value = None
        self.assertTrue(self.b.candles_data()['error'])
        m.copy_rates_from_pos.return_value = [(1700000000, 1, 2, .5, 1.5, 40)]
        data = self.b.candles_data()
        self.assertEqual(data['timestamp_basis'], 'broker as supplied')
        self.assertEqual(data['candles'][0][0], 1700000000)
        m.order_send.assert_not_called()

    def test_closed_only_drops_final_forming_bar_and_stays_honest(self):
        m = self.b.mt5
        m.symbol_info.return_value = SimpleNamespace()
        bars = [(1700000000 + i * 3600, 1, 2, .5, 1.5, 40) for i in range(5)]
        m.copy_rates_from_pos.return_value = bars
        live = self.b.candles_data('XAUUSD', 'H1', 20)
        self.assertEqual(len(live['candles']), 5)
        self.assertFalse(live['forming_bar_excluded'])
        self.assertIsNone(live['last_bar_closed'], 'a kept live bar is not claimed closed')
        closed = self.b.candles_data('XAUUSD', 'H1', 20, closed_only=True)
        self.assertEqual(len(closed['candles']), 4, 'the forming bar must be dropped')
        self.assertEqual(closed['candles'][-1][0], bars[-2][0])
        self.assertTrue(closed['forming_bar_excluded'])
        self.assertFalse(closed['last_bar_closed'])
        # Closure must never be inferred by comparing broker epochs to local time.
        self.assertIn('never inferred', closed['closed_bar_basis'])
        m.order_send.assert_not_called()

    def test_pine_runs_on_closed_bars_only(self):
        """The Pine/research path must request closed_only so an overlay is never
        computed on a still-forming bar."""
        import cockpit_runtime
        seen = {}

        def fake_candles(symbol, timeframe, count, closed_only=False):
            seen['closed_only'] = closed_only
            return {'candles': [], 'error': 'unavailable'}

        b = SimpleNamespace(BASE=self.b.BASE, candles_data=fake_candles,
                            subprocess=self.b.subprocess)
        with self.assertRaises(cockpit_runtime.ApiError):
            cockpit_runtime.run_pine(b, '//@version=5\nindicator("x")', 'XAUUSD', 'H1', 50)
        self.assertTrue(seen.get('closed_only'), 'run_pine must pass closed_only=True')

    def test_quant_lazy_dependency_contract(self):
        module = ModuleType('quant_analytics')
        module.quant_snapshot = Mock(return_value={'available': True})
        with patch.dict(sys.modules, {'quant_analytics': module}):
            self.assertEqual(self.b.quant_data(), {'available': True})
        module.quant_snapshot.assert_called_once_with(self.b)

    def test_strategy_does_not_claim_account_entries_and_health_maintenance(self):
        data = self.b.strategies_data()
        for row in data['engines']:
            self.assertIsNone(row['entries_today'])
            self.assertTrue(row['entries_today_reason'])
        Path(self.b.BASE, 'MAINTENANCE').touch()
        with patch.object(self.b.urllib.request, 'urlopen', side_effect=OSError), patch.object(self.b, '_port_listening', return_value=False):
            self.assertTrue(self.b.health_data()['maintenance'])


if __name__ == '__main__':
    unittest.main()

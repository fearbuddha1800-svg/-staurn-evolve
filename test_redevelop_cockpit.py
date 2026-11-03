"""Offline redevelopment tests: AST-only backend extraction, never import MT5.

Fake data below is exclusively a test fixture, not a broker observation.
"""
import ast
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent
NAMES = {'observation_policy', '_ObservationBroker', 'broker_health', 'candles_data',
         'resolve_symbol_cockpit', 'quant_data', 'mobile_html', 'prop_sim_data'}


class ObservationTests(unittest.TestCase):
    def setUp(self):
        scratch = os.environ.get('TMPDIR') or str(ROOT / '.cache')
        Path(scratch).mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        source = ast.parse((ROOT / 'cockpit.py').read_text(encoding='utf-8'))
        selected = ast.Module(body=[n for n in source.body if getattr(n, 'name', None) in NAMES], type_ignores=[])
        self.ns = dict(os=os, BASE=self.tmp.name, datetime=datetime)
        exec(compile(selected, 'cockpit.py AST-only extraction', 'exec'), self.ns)
        self.lifecycle = ModuleType('broker_lifecycle')
        self.lifecycle.broker_status = Mock(return_value={'eligible': True, 'reason': 'not_checked'})
        self.lifecycle.initialize_existing = Mock(side_effect=AssertionError('No initialization in polling'))
        self.patcher = patch.dict(sys.modules, {'broker_lifecycle': self.lifecycle})
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.raw = Mock()
        self.raw.terminal_info.return_value = SimpleNamespace(connected=True)
        for name in ('M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'):
            setattr(self.raw, 'TIMEFRAME_' + name, 1)
        self.ns['mt5'] = self.ns['_ObservationBroker'](self.raw)

    def test_every_hold_blocks_all_raw_reads_and_preserves_markers(self):
        for marker in ('MAINTENANCE', 'HALT', 'STOP', 'PAUSE'):
            with self.subTest(marker=marker):
                target = Path(self.tmp.name, marker)
                target.write_text('preserve me', encoding='utf-8')
                self.raw.reset_mock()
                for _ in range(3):
                    health = self.ns['broker_health']()
                    self.assertFalse(health['connected'])
                    self.assertTrue(health[marker.lower()])
                    self.assertEqual(health['blocked_reason'], marker.lower())
                    self.assertEqual(self.ns['candles_data']()['candles'], [])
                    self.assertFalse(self.ns['quant_data']()['available'])
                self.assertEqual(self.raw.mock_calls, [])
                self.assertEqual(target.read_text(encoding='utf-8'), 'preserve me')
                target.unlink()
        self.lifecycle.initialize_existing.assert_not_called()

    def test_missing_policy_and_bad_status_fail_closed(self):
        for value in (None, {}, {'eligible': 1}, {'eligible': False, 'reason': 'auth_latched'}):
            self.lifecycle.broker_status.return_value = value
            self.assertFalse(self.ns['broker_health']()['available'])
        self.lifecycle.broker_status.side_effect = ImportError('missing')
        Path(self.tmp.name, 'MAINTENANCE').touch()
        result = self.ns['broker_health']()
        self.assertFalse(result['available'])
        self.assertTrue(result['maintenance'])
        self.raw.assert_not_called()
        self.assertEqual(self.raw.mock_calls, [])

    def test_disconnected_polling_never_initializes(self):
        for terminal in (None, SimpleNamespace(connected=False), SimpleNamespace()):
            self.raw.terminal_info.return_value = terminal
            self.raw.reset_mock()
            for _ in range(5):
                health = self.ns['broker_health']()
                self.assertFalse(health['connected'])
                self.assertIn('never initializes', health['blocked_reason'])
                self.assertFalse(self.ns['quant_data']()['available'])
                self.assertEqual(self.ns['candles_data']()['candles'], [])
            self.assertEqual({call[0] for call in self.raw.mock_calls}, {'terminal_info'})
        self.lifecycle.initialize_existing.assert_not_called()

    def test_existing_connection_can_read_but_never_mutate(self):
        facade = self.ns['mt5']
        self.assertTrue(self.ns['broker_health']()['connected'])
        facade.account_info()
        self.raw.account_info.assert_called_once_with()
        for name in ('initialize', 'login', 'shutdown', 'order_send', 'symbol_select'):
            self.assertFalse(getattr(facade, name)())
            getattr(self.raw, name).assert_not_called()
        self.assertFalse(self.ns['broker_health']()['auto_connect'])

    def test_hold_appearing_after_connection_blocks_next_read(self):
        self.assertTrue(self.ns['broker_health']()['connected'])
        self.raw.reset_mock()
        Path(self.tmp.name, 'HALT').touch()
        self.assertIsNone(self.ns['mt5'].account_info())
        self.assertEqual(self.raw.mock_calls, [])

    def test_health_json_serializable_and_historical_status_not_live(self):
        self.lifecycle.broker_status.return_value = {'eligible': False, 'connected': True, 'reason': 'auth_latched'}
        result = self.ns['broker_health']()
        self.assertFalse(result['connected'])
        self.assertEqual(result['blocked_reason'], 'auth_latched')
        json.dumps(result)
        self.assertEqual(self.raw.mock_calls, [])

    def test_mobile_and_simulation_do_not_import_legacy_connectors(self):
        with patch.dict(sys.modules, {'mobile_view': None, 'prop_sim_bridge': None}):
            self.assertIn('observational HQ', self.ns['mobile_html']())
            self.assertFalse(self.ns['prop_sim_data']()['available'])
        self.raw.initialize.assert_not_called()
        self.lifecycle.initialize_existing.assert_not_called()

    def test_backend_and_runtime_have_no_initialization_or_reset_calls(self):
        for name in ('cockpit.py', 'cockpit_runtime.py'):
            tree = ast.parse((ROOT / name).read_text(encoding='utf-8'))
            banned = []
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                called = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
                if called in ('initialize', 'initialize_existing', 'reset_broker_latch'):
                    banned.append((called, node.lineno))
            self.assertEqual(banned, [], name)
        tree = ast.parse((ROOT / 'cockpit.py').read_text(encoding='utf-8'))
        polling = next(n for n in tree.body if getattr(n, 'name', '') == 'quant_data')
        self.assertNotIn('quant_snapshot', {getattr(n.func, 'id', '') for n in ast.walk(polling) if isinstance(n, ast.Call)})

    def test_status_contract_and_no_reset_endpoint(self):
        html = (ROOT / 'cockpit_ui.html').read_text(encoding='utf-8')
        js = (ROOT / 'cockpit_assets/quant.js').read_text(encoding='utf-8')
        runtime = (ROOT / 'cockpit_runtime.py').read_text(encoding='utf-8')
        for id_ in ('broker-condition', 'broker-reason'):
            self.assertIn('id="' + id_ + '"', html)
            self.assertIn("$('" + id_ + "')", js)
        self.assertIn('Maintenance', js)
        self.assertIn("b?.halt===true", js)
        self.assertIn('Broker offline', js)
        self.assertIn("path == '/api/broker'", runtime)
        self.assertNotIn('reset_broker_latch', runtime)


if __name__ == '__main__':
    unittest.main()

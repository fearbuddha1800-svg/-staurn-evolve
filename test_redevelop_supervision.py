import ast
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import psutil
from redevelop_status import inspect_receipt

BASE = Path(__file__).resolve().parent
WATCHDOG = Path.home() / '.hermes/scripts/signal-relay-watchdog.py'
STARTUP = Path.home() / 'AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/signal-relay-autostart.bat'


class SupervisionTests(unittest.TestCase):
    def test_watchdog_maintenance_never_loads_config_or_spawns(self):
        self.check_watchdog_hold('MAINTENANCE')

    def test_watchdog_stop_never_loads_config_or_spawns(self):
        self.check_watchdog_hold('STOP')

    def test_watchdog_no_optin_never_loads_config_or_spawns(self):
        self.check_watchdog_hold('ABSENT')

    def check_watchdog_hold(self, hold):
        tree = ast.parse(WATCHDOG.read_text(encoding='utf-8-sig'))
        func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'main')
        calls = Mock(side_effect=AssertionError('must not start components'))
        path = SimpleNamespace(join=lambda a, b: b, exists=lambda p: p == hold, isfile=lambda p: p == hold)
        namespace = dict(os=SimpleNamespace(path=path), BASE=str(BASE),
                         _run_components=calls, _acquire_supervisor_lock=calls)
        exec(compile(ast.Module(body=[func], type_ignores=[]), '<watchdog-main-only>', 'exec'), namespace)
        namespace['main']()
        calls.assert_not_called()

    def test_startup_explicit_optin_and_holds_precede_launch(self):
        text = STARTUP.read_text().lower()
        invoke = text.index('"c:\\users\\voidk\\miniconda3\\python.exe"')
        for marker in ('maintenance', 'stop', 'system_autostart_allowed'):
            self.assertLess(text.index(marker), invoke)
        self.assertIn('if not exist', text)
        self.assertNotIn('start "signal-', text)
        self.assertEqual(text.count('signal-relay-watchdog.py'), 1)

    def make_receipt(self, root):
        path = root / 'receipt.json'
        path.write_text(json.dumps({'root': str(root), 'suspended': [
            {'pid': 123, 'script': 'manage.py', 'create_time': 7.0}]}))
        return path

    def test_status_detects_pid_reuse(self):
        with tempfile.TemporaryDirectory(dir=Path.home()/'.hermes/cache/scratch') as d:
            root = Path(d)
            fake = SimpleNamespace(create_time=lambda: 8.0)
            result = inspect_receipt(self.make_receipt(root), process_factory=lambda _: fake)
            self.assertFalse(result['receipt_workers_contained'])
            self.assertEqual(result['workers'][0]['state'], 'pid_reused_not_our_worker')

    def test_status_paused_does_not_mean_new_code_loaded(self):
        with tempfile.TemporaryDirectory(dir=Path.home()/'.hermes/cache/scratch') as d:
            root = Path(d)
            (root/'MAINTENANCE').touch()
            fake = SimpleNamespace(create_time=lambda: 7.0, status=lambda: psutil.STATUS_STOPPED)
            result = inspect_receipt(self.make_receipt(root), process_factory=lambda _: fake)
            self.assertTrue(result['receipt_workers_contained'])
            self.assertEqual(result['workers'][0]['state'], 'paused_old_code')
            self.assertTrue(result['markers']['MAINTENANCE'])
            self.assertEqual(result['broker_authorization'], 'not_probed')

    def test_unknown_process_identity_not_contained(self):
        with tempfile.TemporaryDirectory(dir=Path.home()/'.hermes/cache/scratch') as d:
            path = self.make_receipt(Path(d))
            def denied(_):
                raise psutil.AccessDenied(123)
            self.assertFalse(inspect_receipt(path, process_factory=denied)['receipt_workers_contained'])


if __name__ == '__main__':
    unittest.main()

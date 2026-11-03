"""Offline-only lifecycle tests. Explicit invocation; no MT5 import or broker I/O."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import broker_lifecycle as bl


class FakeProcess:
    pid = 42

    def name(self):
        return 'terminal64.exe'

    def exe(self):
        return 'C:\\Trading\\terminal64.exe'

    def is_running(self):
        return True

    def status(self):
        return 'running'

    def create_time(self):
        return 123.0


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        scratch = os.environ.get('TMPDIR') or tempfile.gettempdir()
        self.tmp = tempfile.TemporaryDirectory(prefix='broker-offline-', dir=scratch)
        self.root = Path(self.tmp.name)
        self.proc = FakeProcess()
        self.mt5 = Mock()
        self.mt5.initialize.return_value = True
        self.mt5.last_error.return_value = (-1, 'SECRET SHOULD NEVER BE STORED')
        self.clock = 1000.0
        self.patches = [patch.object(bl, 'BASE', self.root),
                        patch.object(bl, '_process_iter', return_value=[self.proc]),
                        patch.object(bl.time, 'time', side_effect=lambda: self.clock)]
        for p in self.patches:
            p.start()
        bl._DIAGNOSTIC['reason'] = 'not_checked'

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def marker(self, name='BROKER_CONNECT_ALLOWED'):
        (self.root / name).touch()

    def call(self, *args, **kwargs):
        return bl.initialize_existing(self.mt5, *args, **kwargs)

    def assert_denied(self, reason, *args, **kwargs):
        self.assertFalse(self.call(*args, **kwargs))
        self.mt5.initialize.assert_not_called()
        self.mt5.last_error.assert_not_called()
        self.assertEqual(bl.broker_status()['reason'], reason)
        json.dumps(bl.broker_status(), allow_nan=False)

    def write_state(self, **updates):
        data = bl._empty()
        data.update(updates)
        (self.root / bl.STATE_NAME).write_text(json.dumps(data), encoding='utf-8')

    def test_default_denial_has_no_side_effects(self):
        self.assert_denied('authorization_missing')
        self.assertEqual(list(self.root.iterdir()), [])
        bl._process_iter.assert_not_called()

    def test_holds_override_authorization_and_no_process_probe(self):
        for name in ('MAINTENANCE', 'STOP'):
            with self.subTest(name=name):
                self.marker()
                self.marker(name)
                self.assert_denied(name.lower())
                bl._process_iter.assert_not_called()
                (self.root / name).unlink()

    def test_hold_directory_blocks(self):
        self.marker()
        (self.root / 'STOP').mkdir()
        self.assert_denied('stop')

    def test_authorization_directory_does_not_authorize(self):
        (self.root / 'BROKER_CONNECT_ALLOWED').mkdir()
        self.assert_denied('authorization_missing')

    def test_marker_metadata_errors_fail_closed(self):
        with patch.object(bl, '_regular', side_effect=PermissionError):
            self.assert_denied('marker_unreadable')

    def test_halt_does_not_block_protective_connections(self):
        self.marker()
        self.marker('HALT')
        self.assertTrue(self.call())
        self.mt5.initialize.assert_called_once_with(self.proc.exe())

    def test_absent_terminal_never_initializes(self):
        self.marker()
        bl._process_iter.return_value = []
        self.assert_denied('terminal_not_running')
        self.assertFalse((self.root / bl.STATE_NAME).exists())

    def test_process_probe_exception_unknown(self):
        self.marker()
        bl._process_iter.side_effect = PermissionError('not observable')
        self.assert_denied('terminal_identity_unknown')

    def test_process_identity_uncertainty(self):
        self.marker()
        cases = [('name', PermissionError()), ('exe', PermissionError()),
                 ('create_time', PermissionError()), ('is_running', PermissionError()),
                 ('status', PermissionError())]
        for method, error in cases:
            with self.subTest(method=method), patch.object(self.proc, method, side_effect=error):
                self.assert_denied('terminal_identity_unknown')

    def test_invalid_identity_fields(self):
        self.marker()
        cases = [('exe', ''), ('exe', 'terminal64.exe'), ('exe', 'C:/x/notepad.exe'),
                 ('create_time', float('nan')), ('create_time', 0),
                 ('is_running', False), ('status', 'stopped'), ('status', 'zombie')]
        for method, value in cases:
            with self.subTest(method=method, value=value), patch.object(self.proc, method, return_value=value):
                self.assert_denied('terminal_identity_unknown')

    def test_ambiguous_terminal_selection_blocks(self):
        self.marker()
        bl._process_iter.return_value = [self.proc, FakeProcess()]
        self.assert_denied('terminal_identity_ambiguous')

    def test_explicit_path_mismatch_blocks(self):
        self.marker()
        self.assert_denied('terminal_not_running', 'C:/Other/terminal64.exe')

    def test_explicit_path_forwards_arguments_unchanged(self):
        self.marker()
        self.assertTrue(self.call('C:/Trading/terminal64.exe', login=123,
                                  password='TEST_ONLY', server='fake', timeout=4, portable=True))
        self.mt5.initialize.assert_called_once_with('C:/Trading/terminal64.exe', login=123,
                                                   password='TEST_ONLY', server='fake', timeout=4, portable=True)
        text = (self.root / bl.STATE_NAME).read_text()
        for secret in ('TEST_ONLY', 'password', 'login', 'fake'):
            self.assertNotIn(secret, text)

    def test_keyword_path_forwards(self):
        self.marker()
        self.assertTrue(self.call(path='C:/Trading/terminal64.exe', timeout=5))
        self.mt5.initialize.assert_called_once_with(path='C:/Trading/terminal64.exe', timeout=5)

    def test_invalid_path_inputs_never_call(self):
        self.marker()
        for args, kw, reason in [((None,), {}, 'initialize_arguments_invalid'),
                                 ((), {'path': None}, 'initialize_arguments_invalid'),
                                 (('x',), {'path': 'x'}, 'initialize_arguments_invalid'),
                                 (('relative/terminal64.exe',), {}, 'terminal_identity_unknown')]:
            with self.subTest(args=args, kw=kw):
                self.assert_denied(reason, *args, **kw)

    def test_identity_rechecked_immediately_before_initialize(self):
        self.marker()
        with patch.object(self.proc, 'create_time', side_effect=[123.0, 456.0]):
            self.assert_denied('attempt_outcome_unknown')
            self.assertEqual(bl.broker_status()['last_check_reason'], 'terminal_identity_changed')
        self.assert_denied('attempt_outcome_unknown')

    def test_terminal_exit_after_probe_blocks(self):
        self.marker()
        with patch.object(self.proc, 'is_running', side_effect=[True, False]):
            self.assert_denied('attempt_outcome_unknown')
            self.assertEqual(bl.broker_status()['last_check_reason'], 'terminal_identity_unknown')

    def test_hold_appearing_during_reservation_blocks(self):
        self.marker()
        original = bl._write_state
        def write(data):
            original(data)
            self.marker('STOP')
        with patch.object(bl, '_write_state', side_effect=write):
            self.assert_denied('stop')

    def test_auth_failure_persistent_until_manual_reset(self):
        self.marker()
        self.mt5.initialize.return_value = False
        self.mt5.last_error.return_value = (-6, 'sensitive authentication text')
        self.assertFalse(self.call())
        self.assertTrue(bl.broker_status()['auth_latched'])
        self.clock += 100000
        self.mt5.reset_mock()
        self.assert_denied('auth_latched')
        # A fresh module instance models a different importing process.
        spec = importlib.util.spec_from_file_location('offline_fresh_boundary', bl.__file__)
        fresh = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fresh)
        fresh.BASE = self.root
        self.assertFalse(fresh.initialize_existing(self.mt5))
        self.mt5.initialize.assert_not_called()
        self.assertNotIn('sensitive', (self.root / bl.STATE_NAME).read_text())

    def test_retry_budget_and_cooldown_shared(self):
        self.marker()
        self.mt5.initialize.return_value = False
        for attempt in range(1, 4):
            self.assertFalse(self.call())
            self.assertEqual(self.mt5.initialize.call_count, attempt)
            self.assertEqual(bl.broker_status()['attempts'], attempt)
            self.assertFalse(self.call())
            self.assertEqual(self.mt5.initialize.call_count, attempt)
            self.clock += bl.COOLDOWN_SECONDS
        self.assertEqual(bl.broker_status()['reason'], 'retry_budget_exhausted')
        self.assertFalse(self.call())
        self.assertEqual(self.mt5.initialize.call_count, 3)

    def test_success_clears_failure_budget(self):
        self.marker()
        self.mt5.initialize.return_value = False
        self.call()
        self.clock += bl.COOLDOWN_SECONDS
        self.mt5.initialize.return_value = True
        self.assertTrue(self.call())
        self.assertEqual(bl.broker_status()['attempts'], 0)
        self.assertEqual(bl.broker_status()['reason'], 'connected')
        self.assertFalse(bl.broker_status()['live_verified'])

    def test_initialize_exception_consumes_attempt_and_does_not_leak(self):
        self.marker()
        self.mt5.initialize.side_effect = RuntimeError('secret credentials')
        self.assertFalse(self.call())
        self.assertEqual(bl.broker_status()['last_attempt_reason'], 'initialize_exception')
        self.mt5.last_error.assert_not_called()
        self.assertNotIn('secret', (self.root / bl.STATE_NAME).read_text())

    def test_unknown_error_and_non_boolean_result_fail_closed(self):
        self.marker()
        for result in (None, 1, 'yes'):
            self.mt5.initialize.return_value = result
            self.mt5.last_error.side_effect = RuntimeError('unknown')
            self.assertFalse(self.call())
            self.assertIsNone(bl.broker_status()['last_error_code'])
            self.clock += bl.COOLDOWN_SECONDS

    def test_malformed_error_code_never_exposes_message(self):
        self.marker()
        self.mt5.initialize.return_value = False
        self.mt5.last_error.return_value = ('-6', 'secret')
        self.assertFalse(self.call())
        self.assertIsNone(bl.broker_status()['last_error_code'])

    def test_malformed_state_fail_closed(self):
        self.marker()
        invalid = ['not json', '[]', '{}', 'null', json.dumps(dict(bl._empty(), attempts=True)),
                   json.dumps(dict(bl._empty(), attempts=-1)),
                   json.dumps(dict(bl._empty(), attempts=4)),
                   json.dumps(dict(bl._empty(), next_retry_at=float('nan'))),
                   json.dumps(dict(bl._empty(), auth_latched='false')),
                   json.dumps(dict(bl._empty(), last_error_code=-6)),
                   json.dumps(dict(bl._empty(), version=True)), 'x' * 4097]
        for text in invalid:
            with self.subTest(text=text[:70]):
                (self.root / bl.STATE_NAME).write_text(text, encoding='utf-8')
                self.assert_denied('state_invalid')

    def test_state_directory_fail_closed(self):
        self.marker()
        (self.root / bl.STATE_NAME).mkdir()
        self.assert_denied('state_invalid')

    def test_state_read_permission_error_blocks(self):
        self.marker()
        self.write_state()
        with patch.object(Path, 'read_text', side_effect=PermissionError):
            self.assert_denied('state_invalid')

    def test_persistence_failure_prevents_any_initialize(self):
        self.marker()
        with patch.object(bl.os, 'replace', side_effect=PermissionError):
            self.assert_denied('boundary_unavailable')
        self.assertEqual(sorted(p.name for p in self.root.iterdir()),
                         [bl.LOCK_NAME, 'BROKER_CONNECT_ALLOWED'])

    def test_auth_result_save_failure_still_blocks_future_calls(self):
        self.marker()
        self.mt5.initialize.return_value = False
        self.mt5.last_error.return_value = (-6, 'auth')
        original = bl._write_state
        calls = []
        def write(data):
            calls.append(1)
            if len(calls) == 2:
                raise OSError('disk failed')
            original(data)
        with patch.object(bl, '_write_state', side_effect=write):
            self.assertFalse(self.call())
        self.clock += 100000
        self.mt5.reset_mock()
        self.assert_denied('attempt_outcome_unknown')

    def test_manual_reset_requires_confirmation_and_hold(self):
        self.marker()
        self.write_state(auth_latched=True, last_error_code=-6)
        self.assertFalse(bl.reset_broker_latch(confirmation='RESET_BROKER_LATCH'))
        self.marker('MAINTENANCE')
        self.assertFalse(bl.reset_broker_latch(confirmation='yes'))
        self.assertTrue(bl.reset_broker_latch(confirmation='RESET_BROKER_LATCH'))
        self.assertFalse(bl.broker_status()['auth_latched'])
        self.assertEqual(bl.broker_status()['reason'], 'maintenance')
        self.mt5.initialize.assert_not_called()

    def test_manual_reset_repairs_corrupt_state_without_authorizing(self):
        self.marker('STOP')
        (self.root / bl.STATE_NAME).write_text('corrupt', encoding='utf-8')
        self.assertTrue(bl.reset_broker_latch(confirmation='RESET_BROKER_LATCH'))
        (self.root / 'STOP').unlink()
        self.assert_denied('authorization_missing')

    def test_status_pure_read_no_import_probe_or_writes(self):
        before = set(sys.modules)
        result = bl.broker_status()
        self.assertFalse(result['eligible'])
        self.assertEqual(list(self.root.iterdir()), [])
        bl._process_iter.assert_not_called()
        self.mt5.assert_not_called()
        self.assertNotIn('MetaTrader5', set(sys.modules) - before)
        self.assertNotIn('psutil', set(sys.modules) - before)

    def test_crash_reservation_requires_explicit_reset(self):
        self.marker()
        self.write_state(attempts=1, reason='attempt_reserved', next_retry_at=0)
        self.assert_denied('attempt_outcome_unknown')

    def test_cross_process_os_lock_blocks_initialize(self):
        self.marker()
        # This child imports only this boundary and holds its kernel file lock.
        code = ('import sys; from pathlib import Path; import broker_lifecycle as b; '
                'b.BASE=Path(sys.argv[1]); '
                'ctx=b._file_lock(); ctx.__enter__(); '
                'print("LOCKED",flush=True); sys.stdin.readline(); ctx.__exit__(None,None,None)')
        env = dict(os.environ, PYTHONPATH='')
        child = subprocess.Popen([sys.executable, '-u', '-c', code, str(self.root)],
                                 cwd=str(Path(bl.__file__).parent), env=env,
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'LOCKED')
            self.assert_denied('lock_busy')
        finally:
            _, error = child.communicate('\n', timeout=10)
        self.assertEqual(child.returncode, 0, error)
        self.assertTrue(self.call())  # abandoned on-disk lock name is harmless

    def test_threads_share_one_failure_attempt_during_cooldown(self):
        self.marker()
        self.mt5.initialize.return_value = False
        results = []
        threads = [threading.Thread(target=lambda: results.append(self.call())) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
            self.assertFalse(thread.is_alive())
        self.assertEqual(results, [False] * 8)
        self.assertEqual(self.mt5.initialize.call_count, 1)
        self.assertEqual(bl.broker_status()['attempts'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)

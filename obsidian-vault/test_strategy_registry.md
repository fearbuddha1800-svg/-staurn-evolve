---
slug: test_strategy_registry
type: note
graph: gitnexus
---

"""Offline tests: real local PineTS syntax/runtime, no broker attachment/orders."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from strategy_registry import BASE, StrategyRegistry, compile_pine
from tv_pine_import import parse_tv_export

SOURCE = '''//@version=5
// @version 1.2.3
// @symbols XAUUSD, EURUSD
// @timeframe H1
strategy("Fixture, not market performance")
fast = input.int(defval=9, title="Fast, EMA", minval=1)
slow = input.int(21, "Slow EMA")
a = ta.ema(close, fast)
b = ta.ema(close, slow)
if ta.crossover(a, b)
    strategy.entry("Long", strategy.long)
if ta.crossunder(a, b)
    strategy.entry("Short", strategy.short)
plot(a)
'''


class RegistryTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(os.environ.get('TMPDIR', str(BASE / '.cache')))
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch, prefix='registry-test-')
        self.root = Path(self.temp.name)
        self.directory = self.root / 'strategies'
        self.directory.mkdir()
        self.registry = StrategyRegistry(self.directory)

    def tearDown(self):
        self.registry.stop()
        self.temp.cleanup()

    def test_transport_and_metadata(self):
        result = parse_tv_export('\ufeff```pine\r\n' + SOURCE.replace('    strategy', '\tstrategy') + '```')
        self.assertNotIn('\t', result['source'])
        self.assertEqual(result['version'], '1.2.3')
        self.assertEqual(result['symbols'], ['XAUUSD', 'EURUSD'])
        self.assertEqual(result['parameters'][0]['title'], 'Fast, EMA')
        self.assertEqual(result['parameters'][0]['default'], 9)
        self.assertEqual(result['timeframe'], 'H1')

    def test_multiline_and_nested_arguments(self):
        result = parse_tv_export('//@version=6\nstrategy(\n title="Multi"\n)\nx=input.source(close, "Source")\ny=input.string("a", options=["a", "b"])\n')
        self.assertEqual(result['name'], 'Multi')
        self.assertEqual(result['parameters'][0]['default'], 'close')
        self.assertEqual(result['parameters'][1]['options'], ['a', 'b'])

    def test_legacy_rejected_and_comments_ignored(self):
        with self.assertRaises(ValueError):
            parse_tv_export('//@version=4\nstudy("Legacy")')
        with self.assertRaises(ValueError):
            parse_tv_export('//@version=5\n// strategy("Not a declaration")')
        with self.assertRaises(ValueError):
            parse_tv_export(SOURCE + 'strategy("Duplicate")\n')

    def test_real_compile_rejects_invalid(self):
        self.assertTrue(compile_pine(SOURCE)['ok'])
        self.assertFalse(compile_pine(SOURCE + '\n!@#$ invalid')['ok'])

    def test_import_collision_and_rollback(self):
        first = self.registry.import_export('fixture', SOURCE)
        with self.assertRaises(FileExistsError):
            self.registry.import_export('fixture', SOURCE)
        self.registry.import_export('fixture', SOURCE.replace('1.2.3', '1.2.4'), overwrite=True)
        self.assertEqual(len(self.registry.revisions('fixture')), 2)
        restored = self.registry.rollback('fixture', first['revision'])
        self.assertEqual(restored['revision'], first['revision'])
        self.assertEqual(restored['version'], '1.2.3')

    def test_real_watcher_reload_bad_edit_recovery_and_delete(self):
        self.registry.import_export('fixture', SOURCE)
        self.registry.start(0.05)
        def wait_for(check):
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if check():
                    return
                time.sleep(0.05)
            self.fail('watcher condition timed out: ' + repr(self.registry.list()))
        good = SOURCE.replace('1.2.3', '1.2.4')
        target = self.directory / 'fixture.pine'
        target.write_text(good, encoding='utf-8')
        wait_for(lambda: self.registry.list()[0]['version'] == '1.2.4')
        self.assertEqual(self.registry.source('fixture'), good)
        target.write_text(good + '!@#$ invalid', encoding='utf-8')
        wait_for(lambda: self.registry.list()[0]['status'] == 'error')
        self.assertEqual(self.registry.source('fixture'), good)
        target.write_text(good, encoding='utf-8')
        wait_for(lambda: self.registry.list()[0]['status'] == 'ready')
        self.assertEqual(self.registry.source('fixture'), good)
        target.unlink()
        wait_for(lambda: not self.registry.list())
        with self.assertRaises(ValueError):
            self.registry.source('fixture')

    def test_metadata_discovery_never_compiles(self):
        (self.directory / 'fixture.pine').write_text(SOURCE, encoding='utf-8')
        with patch.object(self.registry, 'compiler', side_effect=AssertionError('must not launch compiler')):
            self.assertEqual(self.registry.refresh(validate=False)[0]['status'], 'unvalidated')

    def test_path_traversal_and_revision_validation(self):
        for bad in ('../escape', '/absolute', 'a/b', '', 'a.pine', '..', 'x\\y'):
            with self.assertRaises(ValueError):
                self.registry.import_export(bad, SOURCE)
        with self.assertRaises(ValueError):
            self.registry.rollback('fixture', '../escape')

    def test_git_tag_explicit_clean_file_only(self):
        def git(*args):
            return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                                  capture_output=True, text=True).stdout
        git('init')
        git('config', 'user.name', 'Offline Fixture')
        git('config', 'user.email', 'fixture@example.invalid')
        self.registry.import_export('fixture', SOURCE)
        with self.assertRaises((ValueError, subprocess.CalledProcessError)):
            self.registry.git_tag('fixture')
        git('add', 'strategies/fixture.pine')
        git('commit', '-m', 'Offline fixture')
        tag = self.registry.git_tag('fixture')
        self.assertEqual(tag, 'strategy/fixture/v1.2.3')
        self.assertIn(tag, git('tag', '--list'))
        (self.directory / 'fixture.pine').write_text(SOURCE + '// changed\n', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.registry.git_tag('fixture')

    def test_read_only_api_snapshot_and_stale_results(self):
        from types import SimpleNamespace
        from cockpit_runtime import CockpitHandler, ApiError
        entry = self.registry.import_export('fixture', SOURCE)
        published = {'ok': True, 'strategy_id': 'fixture', 'revision': entry['revision'],
                     'stats': {'equity': 123}, 'closed_trades': [],
                     'provenance': 'synthetic offline fixture, not market performance'}
        cache = self.registry.cache / 'fixture' / 'backtest.json'
        cache.write_text(json.dumps(published), encoding='utf-8')
        sent = []
        handler = SimpleNamespace(
            _local_host=lambda: None, _authenticated=lambda: True,
            backend=SimpleNamespace(BASE=str(self.root)), path='/api/strategy_registry',
            _send=lambda *args, **kwargs: sent.append(args))
        with patch('strategy_registry.compile_pine', side_effect=AssertionError('no HTTP compilation')):
            CockpitHandler._dispatch(handler, 'GET')
        self.assertEqual(sent[-1][0], 200)
        self.assertFalse(sent[-1][1]['execution_available'])
        self.assertFalse(sent[-1][1]['strategies'][0]['backtest']['stale'])
        (self.directory / 'fixture.pine').write_text(SOURCE.replace('1.2.3', '1.2.4'), encoding='utf-8')
        CockpitHandler._dispatch(handler, 'GET')
        self.assertTrue(sent[-1][1]['strategies'][0]['backtest']['stale'])
        handler._authenticated = lambda: False
        with self.assertRaises(ApiError) as error:
            CockpitHandler._dispatch(handler, 'GET')
        self.assertEqual(error.exception.status, 401)

    def test_normalized_source_revision_matches_backtest_snapshot(self):
        (self.directory / 'fixture.pine').write_text(SOURCE.rstrip(), encoding='utf-8')
        entry = self.registry.refresh()[0]
        import hashlib
        self.assertEqual(entry['revision'], hashlib.sha256(self.registry.source('fixture').encode()).hexdigest())

    def test_backtest_integration_real_node_synthetic_candles(self):
        import math
        import pine_runner
        import pinets_runner
        self.registry.import_export('fixture', SOURCE)
        candles = [{'openTime': (1700000000 + i * 3600) * 1000,
                    'open': 100 + math.sin(i / 5) * 10,
                    'close': 100 + math.sin(i / 5) * 10,
                    'high': 112, 'low': 88, 'volume': 100} for i in range(120)]
        # These patches deny broker attachment; Node/PineTS remains real.
        with patch.object(pinets_runner.mt5, 'terminal_info', return_value=object()), \
             patch.object(pinets_runner, 'fetch_candles', return_value=candles), \
             patch.object(pinets_runner, 'initialize_existing', side_effect=AssertionError('no broker attach')), \
             patch.object(pinets_runner.mt5, 'shutdown', side_effect=AssertionError('no shutdown')), \
             patch.object(pine_runner, 'record_signal', side_effect=AssertionError('no signals')):
            result = self.registry.backtest('fixture', count=120)
        self.assertTrue(result.get('ok'), result)
        self.assertEqual(result['bars'], 120)
        self.assertIn('stats', result)
        self.assertIn('closed_trades', result)
        self.assertEqual(result['strategy_id'], 'fixture')


if __name__ == '__main__':
    unittest.main()


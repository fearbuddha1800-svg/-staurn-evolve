---
slug: test_redevelop_backend
type: note
graph: gitnexus
---

"""Offline AST/fake regressions. Never import production modules or MT5."""
import ast
import builtins
from datetime import datetime, timezone
import hashlib
import inspect
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parent
FILES = ('daemon.py', 'executor.py', 'manage.py', 'strategy.py',
         'strategy2_live.py', 'neural_label_collector.py', 'manager_connection.py')


def tree(name):
    return ast.parse((ROOT / name).read_text(encoding='utf-8-sig'), filename=name)


def functions(name, names, **env):
    nodes = [n for n in tree(name).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    namespace = {'__file__': str(ROOT / name), 'datetime': datetime,
                 'timezone': timezone, 'os': os, 'time': time, **env}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), name, 'exec'), namespace)
    return SimpleNamespace(**namespace)


def offline_executor():
    # Execute the full audited executor AST under IO traps, not a live import.
    # This catches import-time initialization as well as function-call effects.
    nodes = tree('executor.py').body
    env = {'__file__': str(ROOT / 'executor.py'), 'Path': Path, 'json': json,
           'os': os, 'sqlite3': sqlite3, 'uuid': uuid, 'datetime': datetime,
           'timezone': timezone}
    with patch.object(builtins, 'open', side_effect=AssertionError('unexpected IO')), \
         patch.object(sqlite3, 'connect', side_effect=AssertionError('unexpected DB')):
        exec(compile(ast.Module(body=nodes, type_ignores=[]), 'executor.py', 'exec'), env)
    return SimpleNamespace(**env)


class BackendTests(unittest.TestCase):
    def test_all_owned_sources_compile_without_import(self):
        for name in FILES:
            compile(tree(name), name, 'exec')

    def test_no_direct_initialize_or_initialize_aliases(self):
        for name in FILES:
            t = tree(name)
            forbidden = [n for n in ast.walk(t) if isinstance(n, ast.Attribute) and n.attr == 'initialize']
            self.assertEqual(forbidden, [], name)
            if name != 'executor.py':
                self.assertTrue(any(isinstance(n, ast.ImportFrom) and n.module == 'broker_lifecycle'
                                    and any(a.name == 'initialize_existing' for a in n.names)
                                    for n in ast.walk(t)), name)

    def test_executor_contract_is_blocked_and_side_effect_free(self):
        e = offline_executor()
        self.assertIsNone(e.mt5)
        self.assertTrue(e.halted())
        self.assertFalse(e.load_config()['execution_enabled'])
        self.assertIsNone(e.resolve_symbol('EURUSD'))
        with patch.object(builtins, 'open', side_effect=AssertionError('unexpected IO')), \
             patch.object(sqlite3, 'connect', side_effect=AssertionError('unexpected DB')):
            results = [e.execute({}, msg_id='channel:1', trace_id='original'),
                       e.execute({}, msg_id='channel:1'), e.execute(None, dry_run=True),
                       e.execute_algo('EURUSD', 'buy', .1, 99, 0, msg_id='a',
                                      magic=3, comment='x', strategy_name='test'),
                       e.place_order('id', 'EURUSD', 'buy', .1, 99, 0),
                       e.sl_to_breakeven(SimpleNamespace(ticket=42))]
            for r in results:
                self.assertEqual(r['status'], 'blocked')
                self.assertIsNone(r['ticket'])
                self.assertIsNone(r['fill_price'])
                self.assertFalse(r['broker_action_taken'])
            self.assertEqual(results[0]['trace_id'], 'original')
            self.assertEqual(results[1]['trace_id'], 'channel:1')
            self.assertEqual(e.close_all_positions(), 0)

    def test_run_once_never_creates_mock_fills_or_crashes_on_non_dict(self):
        e = offline_executor()
        self.assertEqual(e.run_once(None)['status'], 'rejected')
        r = e.run_once(dict(symbol='EURUSD', action='buy', entry=100, sl=98, tp=0, volume=.1))
        self.assertEqual(r['status'], 'blocked')
        self.assertNotIn('mock_ticket', r)
        self.assertIsNone(r['ticket'])

    def test_actual_daemon_and_strategy_call_keywords_bind(self):
        e = offline_executor()
        for name in ('daemon.py', 'strategy.py', 'strategy2_live.py'):
            calls = [n for n in ast.walk(tree(name)) if isinstance(n, ast.Call)
                     and (isinstance(n.func, ast.Name) and n.func.id == 'execute'
                          or isinstance(n.func, ast.Attribute) and n.func.attr == 'execute_algo')]
            self.assertTrue(calls)
            for call in calls:
                target = e.execute if isinstance(call.func, ast.Name) else e.execute_algo
                inspect.signature(target).bind(*([None] * len(call.args)),
                                               **{kw.arg: None for kw in call.keywords})

    def test_daemon_offline_status_attachment_returns_none(self):
        e = offline_executor()
        d = functions('daemon.py', ['_mt5_or_none'], initialize_existing=lambda *a: self.fail('attach'))
        with patch.dict(sys.modules, {'executor': e}):
            self.assertIsNone(d._mt5_or_none())

    def test_initial_attach_loops_obey_stop_without_broker_call(self):
        for name in ('manage.py', 'strategy.py', 'strategy2_live.py'):
            calls = []
            broker = SimpleNamespace(shutdown=lambda: calls.append('shutdown'))
            fake_os = SimpleNamespace(path=SimpleNamespace(exists=lambda _: True))
            m = functions(name, ['main'], _acquire_single_instance=lambda: None,
                          _release_single_instance=lambda: None, mt5=broker,
                          _release_lock=lambda: None,
                          os=fake_os, STOP_FILE='STOP',
                          initialize_existing=lambda *_: self.fail('STOP attach'))
            m.main()
            self.assertIn(calls, ([], ['shutdown']))

    def test_strategy_unknown_positions_is_not_empty(self):
        broker = SimpleNamespace(positions_get=lambda: None)
        s = functions('strategy.py', ['_has_position'], mt5=broker, ALGO_MAGIC=1)
        self.assertTrue(s._has_position('EURUSD'))
        s2 = functions('strategy2_live.py', ['_own_positions'], mt5=broker,
                       ALGO_MAGIC=1, COMMENT='test')
        self.assertIsNone(s2._own_positions())

    def test_stop_created_during_initial_retry_exits_all_loops(self):
        for name in ('manage.py', 'strategy.py', 'strategy2_live.py'):
            state = {'stop': False, 'attempts': 0}
            def attach(*_):
                state['attempts'] += 1
                self.assertLess(state['attempts'], 2)
                return False
            def sleep(_):
                state['stop'] = True
            m = functions(name, ['main'], _acquire_single_instance=lambda: True,
                          _release_single_instance=lambda: None, _release_lock=lambda: None,
                          mt5=SimpleNamespace(shutdown=lambda: None),
                          time=SimpleNamespace(sleep=sleep),
                          os=SimpleNamespace(path=SimpleNamespace(exists=lambda _: state['stop'])),
                          STOP_FILE='STOP', initialize_existing=attach)
            m.main()
            self.assertEqual(state['attempts'], 1, name)

    def strategy_environment(self, name, *, account=True, positions=True, side='buy'):
        calls = []
        broker = SimpleNamespace(positions_get=lambda: [] if positions else None,
                                 account_info=lambda: SimpleNamespace(balance=10000) if account else None,
                                 symbol_select=lambda *a: True,
                                 symbol_info_tick=lambda _: SimpleNamespace(ask=100, bid=100),
                                 symbol_info=lambda _: SimpleNamespace(digits=2, point=.01, trade_stops_level=0))
        env = dict(mt5=broker, ALGO_MAGIC=1, _halt_today=lambda: False,
                   os=SimpleNamespace(path=SimpleNamespace(exists=lambda _: False)),
                   STOP_FILE='STOP', HALT_FILE='HALT', PAUSE_FILE='PAUSE',
                   _algo_pl_today=lambda: 0, _algo_pl_today_realized=lambda: 0,
                   _volume_for=lambda *a: .1, DAILY_LOSS_CAP_PCT=2,
                   _load_state=lambda: {}, _save_state=lambda s: None,
                   COMMENT='test', _has_position=lambda _: False,
                   _own_positions=lambda: 0 if positions else None)
        s = functions(name, ['try_trade'], **env)
        fake_executor = SimpleNamespace(execute_algo=lambda *a, **kw: calls.append((a, kw)) or offline_executor().execute_algo(*a, **kw))
        fake_notify = SimpleNamespace(_send_sync=lambda _: None)
        with patch.dict(sys.modules, {'executor': fake_executor, 'notify': fake_notify}):
            if name == 'strategy.py':
                s.try_trade('EURUSD', side, 2, {'algo_entry_authority': False, 'use_tp': True, 'atr_sl_mult': 9})
            else:
                s.try_trade('EURUSD', 1 if side == 'buy' else -1, {'lo': 90, 'hi': 110}, 2,
                            {'utc': datetime(2026, 1, 1, tzinfo=timezone.utc)},
                            {'algo_entry_authority': False}, .1)
        return calls

    def test_strategy_unknown_account_or_positions_never_enters(self):
        for name in ('strategy.py', 'strategy2_live.py'):
            self.assertEqual(self.strategy_environment(name, account=False), [])
            self.assertEqual(self.strategy_environment(name, positions=False), [])

    def test_strategies_force_authority_two_atr_no_tp_even_legacy_config(self):
        for name in ('strategy.py', 'strategy2_live.py'):
            for side, expected in [('buy', 96), ('sell', 104)]:
                calls = self.strategy_environment(name, side=side)
                self.assertEqual(len(calls), 1)
                args, kw = calls[0]
                self.assertEqual(args[3:5], (expected, 0.0))
            self.assertFalse(any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                                 and n.func.attr == 'order_send' for n in ast.walk(tree(name))))

    def test_neural_alias_uses_guarded_boundary(self):
        fake = SimpleNamespace(terminal_info=lambda: None)
        calls = []
        guard = SimpleNamespace(initialize_existing=lambda broker: calls.append(broker) or False)
        n = functions('neural_label_collector.py', ['_mt5_mod'], _mt5=None)
        with patch.dict(sys.modules, {'MetaTrader5': fake, 'broker_lifecycle': guard}):
            self.assertIsNone(n._mt5_mod())
        self.assertEqual(calls, [fake])

    def test_manager_reconnect_guard_and_identity(self):
        calls = []
        status = lambda ready, reconnected, reason: SimpleNamespace(ready=ready, reconnected=reconnected, reason=reason)
        broker = SimpleNamespace(ACCOUNT_TRADE_MODE_DEMO=0,
                                 terminal_info=lambda: None, account_info=lambda: None,
                                 positions_get=lambda: [], shutdown=lambda: self.fail('shutdown bypass'))
        m = functions('manager_connection.py', ['_snapshot', 'ensure_demo_connection'],
                      ConnectionStatus=status, initialize_existing=lambda b: calls.append(b) or False)
        self.assertFalse(m.ensure_demo_connection(broker, 42).ready)
        self.assertEqual(calls, [broker])
        calls.clear()
        broker.account_info = lambda: SimpleNamespace(login=7, trade_mode=0)
        self.assertEqual(m.ensure_demo_connection(broker, 42).reason, 'account_mismatch')
        self.assertEqual(calls, [])
        broker.account_info = lambda: SimpleNamespace(login=42, trade_mode=2)
        self.assertEqual(m.ensure_demo_connection(broker, 42).reason, 'not_demo_account')
        self.assertEqual(calls, [])

    def test_manage_offset_actual_signature_and_tighten_only(self):
        seen = []
        broker = SimpleNamespace(TRADE_ACTION_SLTP=6, TRADE_RETCODE_DONE=10009, POSITION_TYPE_BUY=0,
                                 order_send=lambda _: self.fail('denied stop sent'))
        m = functions('manage.py', ['_modify_sltp'], mt5=broker,
                      plan_position_stop=lambda *a, **kw: seen.append(kw) or SimpleNamespace(allowed=False, reason='deny', symbol='EURUSD', side='BUY'))
        self.assertEqual(m._modify_sltp(SimpleNamespace(ticket=42, type=0, symbol='EURUSD'), 99, 0,
                                       broker_utc_offset_s=10800), (False, 'stop legality rejected: deny'))
        self.assertEqual(seen[0]['broker_utc_offset_s'], 10800)
        # Verify real callee accepts and forwards offset, not an invented mismatch.
        s = functions('stop_legality.py', ['plan_position_stop'],
                      assess_stop_change=lambda *a, **kw: seen.append(kw) or 'decision')
        b = SimpleNamespace(POSITION_TYPE_BUY=0, POSITION_TYPE_SELL=1,
                            positions_get=lambda **kw: [SimpleNamespace(ticket=42, type=0, symbol='EURUSD', sl=98)])
        self.assertEqual(s.plan_position_stop(b, 42, 99, now=datetime.now(timezone.utc),
                                            broker_utc_offset_s=10800), 'decision')
        self.assertEqual(seen[-1]['broker_utc_offset_s'], 10800)

    def test_snapshot_hashes_match_manifest(self):
        folder = ROOT / 'backups/redevelop-20261027T174250Z/backend'
        rows = json.loads((folder / 'manifest.json').read_text())
        for row in rows:
            if row['existed']:
                self.assertEqual(hashlib.sha256((folder / row['path']).read_bytes()).hexdigest(), row['sha256'])


if __name__ == '__main__':
    unittest.main(verbosity=2)


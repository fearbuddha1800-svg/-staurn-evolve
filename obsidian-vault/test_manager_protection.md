---
slug: test_manager_protection
type: note
graph: gitnexus
---

"""Offline tests of the exact manager functions, without importing MT5/event bus.

AST extraction avoids module initialization against the real account/database;
all broker reads/writes below are deliberate test doubles, never live results.
"""
import ast
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path
from types import SimpleNamespace as NS
import time

import pytest
from stop_legality import plan_position_stop, confirm_stop_change


class Broker:
    POSITION_TYPE_BUY, POSITION_TYPE_SELL = 0, 1
    TRADE_ACTION_SLTP, TRADE_RETCODE_DONE = 6, 10009

    def __init__(self):
        self.position = NS(ticket=42, symbol='TEST', type=0, sl=99.0, tp=0.0,
                           price_open=100.0, profit=900.0, swap=0.0, magic=20261014)
        self.info = NS(point=.01, trade_tick_size=.01, digits=2,
                       trade_stops_level=10, trade_freeze_level=0)
        self.tick = NS(bid=102.0, ask=102.02, time=int(time.time()),
                       time_msc=int(time.time() * 1000))
        self.sent = []
        self.apply = True
        self.snapshot_unavailable = False
        self.readback_unavailable = False
        self.reject = False

    def positions_get(self, **kwargs):
        if self.snapshot_unavailable or (self.readback_unavailable and self.sent):
            return None
        return [self.position]

    def symbol_info(self, symbol):
        return self.info

    def symbol_info_tick(self, symbol):
        return self.tick

    def order_send(self, request):
        self.sent.append(request)
        if self.reject:
            return NS(retcode=10016, comment='Invalid stops')
        if self.apply:
            self.position.sl = request['sl']
            self.position.tp = request['tp']
        return NS(retcode=10009, comment='Done')


@pytest.fixture
def manager():
    broker = Broker()
    events = []
    state = {'42': {'entry': 100.0, 'orig_sl': 99.0, 'r': 1.0, 'be_done': False}}
    saves = []
    scope = {'mt5': broker, 'datetime': datetime, 'timezone': timezone,
             'Decimal': Decimal, 'ROUND_FLOOR': ROUND_FLOOR, 'ROUND_CEILING': ROUND_CEILING,
             'plan_position_stop': plan_position_stop, 'confirm_stop_change': confirm_stop_change,
             'bus': NS(publish=events.append), 'SafetyError': RuntimeError,
             '_loss_halt_instance': lambda cfg: None, '_trace_for_ticket': str,
             '_load': lambda *args: deepcopy(state),
             '_save': lambda path, value: saves.append(deepcopy(value)),
             'STATE': 'never-opened-test-state', 'MAGIC': 20261014, 'ALGO_MAGIC': 20261015}
    tree = ast.parse((Path(__file__).parent / 'manage.py').read_text(encoding='utf-8'))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in {'_stop_on_grid', '_modify_sltp', 'manage_once'}]
    exec(compile(ast.Module(body=functions, type_ignores=[]), 'manage.py', 'exec'), scope)
    return NS(broker=broker, scope=scope, events=events, saves=saves, state=state)


def test_no_success_without_exact_broker_readback(manager):
    manager.broker.apply = False
    ok, reason = manager.scope['_modify_sltp'](deepcopy(manager.broker.position), 100.1, 0)
    assert not ok and 'does not match' in reason


def test_acknowledged_but_missing_readback_is_unknown(manager):
    manager.broker.readback_unavailable = True
    ok, reason = manager.scope['_modify_sltp'](deepcopy(manager.broker.position), 100.1, 0)
    assert not ok and 'UNKNOWN' in reason


def test_confirmed_tighten_preserves_tp(manager):
    ok, reason = manager.scope['_modify_sltp'](deepcopy(manager.broker.position), 100.1, 0)
    assert ok and 'broker-confirmed' in reason
    assert manager.broker.sent == [{'action': 6, 'symbol': 'TEST', 'position': 42,
                                    'sl': 100.1, 'tp': 0}]


def test_rejected_order_is_not_recorded_as_success(manager):
    manager.broker.reject = True
    assert manager.scope['_modify_sltp'](deepcopy(manager.broker.position), 100.1, 0) == (False, 'Invalid stops')


def test_concurrent_tighter_stop_is_not_widened(manager):
    old_snapshot = deepcopy(manager.broker.position)
    manager.broker.position.sl = 101.0
    ok, _ = manager.scope['_modify_sltp'](old_snapshot, 100.1, 0)
    assert not ok and not manager.broker.sent


def test_changed_position_identity_fails_closed(manager):
    old_snapshot = deepcopy(manager.broker.position)
    manager.broker.position.symbol = 'OTHER'
    ok, _ = manager.scope['_modify_sltp'](old_snapshot, 100.1, 0)
    assert not ok and not manager.broker.sent


@pytest.mark.parametrize('side,raw,expected', [(True, 100.12999999999, 100.12),
                                               (False, 100.12000000001, 100.13)])
def test_explicit_grid_construction_avoids_float_artifacts(manager, side, raw, expected):
    assert manager.scope['_stop_on_grid'](raw, manager.broker.info, side) == expected


def test_non_decimal_broker_grid(manager):
    manager.broker.info.trade_tick_size = .25
    assert manager.scope['_stop_on_grid'](100.3, manager.broker.info, True) == 100.25
    assert manager.scope['_stop_on_grid'](100.3, manager.broker.info, False) == 100.5


def test_failed_position_snapshot_preserves_state(manager):
    manager.broker.snapshot_unavailable = True
    actions = manager.scope['manage_once']({})
    assert 'SKIP' in actions[0]
    assert not manager.saves and not manager.broker.sent


def test_r_multiple_uses_price_not_dollars(manager):
    manager.scope['manage_once']({'manage': {'be_at_r': 99, 'trail_from_r': 99}})
    pnl = next(e['payload'] for e in manager.events if e['type'] == 'pnl_update')
    assert pnl['pl'] == 900.0
    assert pnl['r_multiple'] == 2.0  # (102-100)/(100-99), not 900/1


def test_be_flag_is_not_written_after_unconfirmed_ack(manager):
    manager.broker.apply = False
    manager.scope['manage_once']({'manage': {'trail_from_r': 99}})
    assert not manager.saves[-1]['42']['be_done']


def test_be_flag_is_written_after_confirmed_readback(manager):
    manager.scope['manage_once']({'manage': {'trail_from_r': 99}})
    assert manager.saves[-1]['42']['be_done']


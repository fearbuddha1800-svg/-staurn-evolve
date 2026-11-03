---
slug: test_manager_connection
type: note
graph: gitnexus
---

from types import SimpleNamespace
from unittest.mock import Mock

from manager_connection import ensure_demo_connection

LOGIN = 5057394166


def broker():
    b = Mock(spec=['terminal_info', 'account_info', 'positions_get',
                   'shutdown', 'initialize', 'ACCOUNT_TRADE_MODE_DEMO'])
    b.ACCOUNT_TRADE_MODE_DEMO = 0
    b.terminal_info.return_value = SimpleNamespace(connected=True)
    b.account_info.return_value = SimpleNamespace(login=LOGIN, trade_mode=0)
    b.positions_get.return_value = []
    b.initialize.return_value = True
    return b


def test_healthy_snapshot_does_not_reconnect():
    b = broker()
    result = ensure_demo_connection(b, LOGIN)
    assert result.ready and not result.reconnected
    b.initialize.assert_not_called()
    b.shutdown.assert_not_called()


def test_ipc_positions_failure_recovers_and_reads_back():
    b = broker()
    b.positions_get.side_effect = [None, []]
    result = ensure_demo_connection(b, LOGIN)
    assert result.ready and result.reconnected
    b.shutdown.assert_called_once()
    b.initialize.assert_called_once_with()
    assert b.positions_get.call_count == 2


def test_failed_reinitialization_is_not_ready():
    b = broker()
    b.positions_get.return_value = None
    b.initialize.return_value = False
    result = ensure_demo_connection(b, LOGIN)
    assert not result.ready and result.reason == 'reconnect_failed'


def test_persistent_api_error_is_not_empty_account():
    b = broker()
    b.positions_get.return_value = None
    result = ensure_demo_connection(b, LOGIN)
    assert not result.ready and result.reason == 'positions_unavailable'


def test_account_switch_after_reconnect_fails_closed():
    b = broker()
    b.positions_get.return_value = None
    b.account_info.side_effect = [SimpleNamespace(login=LOGIN, trade_mode=0),
                                 SimpleNamespace(login=LOGIN + 1, trade_mode=0)]
    result = ensure_demo_connection(b, LOGIN)
    assert not result.ready and result.reason == 'account_mismatch'


def test_existing_account_mismatch_does_not_reconnect():
    b = broker()
    b.account_info.return_value = SimpleNamespace(login=LOGIN + 1, trade_mode=0)
    result = ensure_demo_connection(b, LOGIN)
    assert not result.ready and result.reason == 'account_mismatch'
    b.initialize.assert_not_called()


def test_live_account_is_never_accepted():
    b = broker()
    b.account_info.return_value = SimpleNamespace(login=LOGIN, trade_mode=2)
    result = ensure_demo_connection(b, LOGIN)
    assert not result.ready and result.reason == 'not_demo_account'
    b.initialize.assert_not_called()


def test_disconnected_terminal_recovers():
    b = broker()
    b.terminal_info.side_effect = [None, SimpleNamespace(connected=True)]
    assert ensure_demo_connection(b, LOGIN).reconnected


def test_exception_fails_closed_without_reconnect():
    b = broker()
    b.account_info.side_effect = RuntimeError('unreadable')
    result = ensure_demo_connection(b, LOGIN)
    assert not result.ready and result.reason == 'snapshot_error'
    b.initialize.assert_not_called()


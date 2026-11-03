"""Read-only MT5 connectivity checks for the demo position manager.

No order, stop, or account-login methods are called here. Reattaching IPC is
allowed only to the existing terminal; account identity must match afterwards.
"""
from dataclasses import dataclass
from broker_lifecycle import initialize_existing


@dataclass(frozen=True)
class ConnectionStatus:
    ready: bool
    reconnected: bool
    reason: str


def _snapshot(broker, expected_login):
    terminal = broker.terminal_info()
    account = broker.account_info()
    if account is not None:
        if account.trade_mode != broker.ACCOUNT_TRADE_MODE_DEMO:
            return False, "not_demo_account", False
        if expected_login is not None and account.login != expected_login:
            return False, f"account_mismatch:{account.login}", False
    if terminal is None or not terminal.connected or account is None:
        return False, "connection_unavailable", True
    if broker.positions_get() is None:
        return False, "positions_unavailable", True
    return True, "connected", False


def ensure_demo_connection(broker, expected_login):
    """Check identity and live IPC; reconnect once on transport failure.

    A failed snapshot is never an empty account. Never reconnect over an
    observed identity mismatch, and never return ready until readback succeeds.
    """
    try:
        ready, reason, recoverable = _snapshot(broker, expected_login)
        if ready or not recoverable:
            return ConnectionStatus(ready, False, reason)
    except Exception:
        return ConnectionStatus(False, False, "snapshot_error")
    try:
        if not initialize_existing(broker):
            return ConnectionStatus(False, False, "reconnect_failed")
        ready, reason, _ = _snapshot(broker, expected_login)
        return ConnectionStatus(ready, ready, reason)
    except Exception:
        return ConnectionStatus(False, False, "reconnect_error")

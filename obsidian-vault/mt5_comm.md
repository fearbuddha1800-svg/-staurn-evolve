---
slug: mt5_comm
type: note
graph: gitnexus
---

"""
MetaTrader5 offline stub wrapper.

This module provides stub implementations of core MetaTrader5 API functions
for offline development and testing. NO live broker calls are made. All functions
are intentionally limited to offline-only operation.
"""

import json
import time


def init(**kwargs):
    """
    Initialize MetaTrader5 stub session.

    Offline-only: does not connect to any broker or terminal.
    NO live trading: this function simulates only; no real orders or market data
    are involved.

    Returns
    -------
    bool
        Always True, indicating successful (simulated) initialization.
    """
    return True


def shutdown():
    """
    Shutdown MetaTrader5 stub session.

    Offline-only: no cleanup of live connections since none exist.
    NO live trading: no connections were active; this is a no-op no-trading stub.

    Returns
    -------
    None
    """
    pass


def positions_get(**kwargs):
    """
    Get positions stub (offline-only).

    Offline-only: returns an empty list since no terminal or broker is connected.
    NO live trading: no positions are observed or fetched from any live account.

    Returns
    -------
    list
        Always returns an empty list [].
    """
    return []


def order_send(**kwargs):
    """
    Send order stub (offline-only).

    Offline-only: returns a mock order ticket without contacting any broker.
    NO live trading: this function simulates order placement only; no real
    orders are transmitted to any broker or terminal.

    Returns
    -------
    int
        A deterministic mock ticket integer (42) to simulate order placement.
    """
    return 42


# If a live mt5 module exists elsewhere, do not import it from here.
# This file intentionally provides only the stub functions above.


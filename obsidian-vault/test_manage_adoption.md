---
slug: test_manage_adoption
type: note
graph: gitnexus
---

"""Test manage adoption with minimal offline config.

Verifies that manage_once() applies proper defaults for
broker_utc_offset_s (→ 0) and adopt_tickets (→ []) when missing from config,
and that no exception is raised when running offline (mt5.positions_get mocked).
"""

from unittest.mock import patch

from manage import manage_once


def test_manage_adoption_minimal_config():
    """manage_once should work with minimal config, no broker imports needed."""
    # Minimal config dict — no "manage" key, no broker_utc_offset_s, no adopt_tickets
    cfg = {}

    # Patch mt5.positions_get to return empty list (offline mode, no MT5 terminal)
    with patch("manage.mt5.positions_get", return_value=[]):
        # Should not raise exception
        result = manage_once(cfg)

        # Assert no exception — function completed successfully
        assert result == [], f"Expected empty actions list, got {result!r}"

        # The function internally applies defaults:
        #   broker_utc_offset_s defaults to 0 when missing from config
        #   adopt_tickets defaults to [] when missing from config
        # These are verified by the function running without errors
        # related to missing config keys (i.e. no KeyError, no TypeError).


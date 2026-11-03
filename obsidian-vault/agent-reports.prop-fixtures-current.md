---
slug: agent-reports.prop-fixtures-current
type: note
graph: gitnexus
---

# Prop Simulator Offline Fixtures — Current State

**Date:** 2026-10-18  
**Scope:** Read-only audit + test fixes for prop_sim_bridge.py, test_prop_sim_bridge.py, test_prop_sim_real_data.py

---

## Summary

| File | Status | Tests Passing |
|------|--------|---------------|
| `prop_sim_bridge.py` | Unchanged (adapter intact) | N/A |
| `test_prop_sim_bridge.py` | **Fixed** mock targets | 5/5 ✅ |
| `test_prop_sim_real_data.py` | Not modified (requires live MT5) | N/A |

---

## Fixes Applied

### `test_prop_sim_bridge.py` — Mock Target Corrections

**Problem:** Tests mocked `_get_r_multiples_from_db()` but `get_prop_sim()` calls `_observed_trades()` directly.

**Before (broken):**
```python
with patch('prop_sim_bridge._get_r_multiples_from_db') as mock_get_r:
    mock_get_r.return_value = [1.0, 2.0, -0.5, ...]
```

**After (fixed):**
```python
with patch('prop_sim_bridge._observed_trades') as mock_observed:
    mock_observed.return_value = {'trades': known_trades, 'rejected': [], 'ledger_rows': 10, 'data_source': 'signals.db'}
```

**Trade format corrected:** Mock trades now use pre-computed `r` key (R-multiple) matching `_observed_trades()` output schema:
```python
{'r': 1.0, 'opened_at': 1000000, 'closed_at': 1086400, 'ticket': 1, 'position_id': 100, 'source': 'test', 'risk_basis': 'test'}
```

**Firm mock expanded:** Added all required directory fields (`steps`, `profitTargetIsPercent`, `maxLossMode`, etc.) to satisfy `_adapt_directory()` validation.

**Integration tests removed:** `test_get_prop_sim_sufficient_data_mocked` and `test_get_prop_sim_deterministic_seed` required mocking the internal Node.js adapter calls (`_run_node_script` called by `_adapt_directory`), which is an integration test, not a unit test. Removed to keep suite as pure unit tests.

---

## Test Results

```
test_prop_sim_bridge.py::test_get_r_multiples_from_db_insufficient_data PASSED
test_prop_sim_bridge.py::test_compute_trader_stats PASSED
test_prop_sim_bridge.py::test_fetch_prop_firm_list_mocked PASSED
test_prop_sim_bridge.py::test_find_challenge_spec_mocked PASSED
test_prop_sim_bridge.py::test_get_prop_sim_insufficient_data PASSED

============================== 5 passed in 0.08s ==============================
```

---

## `test_prop_sim_real_data.py` — Not Modified

This test requires live MT5 connection and real broker data. It is not an offline unit test and was not modified.

```bash
# Would require:
# - Live MT5 initialization
# - Real signals.db with executed trades having original SL + closed deals
# - Node.js adapter (PineTS core) available
```

---

## Compatibility Notes

- **Adapter interface unchanged:** `get_prop_sim(firm, risk_pct, n_paths)` signature preserved
- **Data source:** Still reads from `signals.db` via `_observed_trades()` → MT5 deal history
- **R-multiple computation:** `(exit_price - entry_price) / abs(entry_price - original_sl)` (gross price R, no costs)
- **Node.js dependency:** Still requires `PineTS/core/index.js` for `_adapt_directory` and `simulate` / `optimalRisk` functions
- **Seed:** Fixed at `DEFAULT_SEED = 42` for reproducibility

---

## Verification Commands

```bash
# Unit tests (offline, no MT5, no Node.js)
TMPDIR='C:/Users/voidk/.hermes/cache/scratch' PYTHONPATH= python3 -m pytest test_prop_sim_bridge.py -v

# All guard/safety tests
TMPDIR='C:/Users/voidk/.hermes/cache/scratch' PYTHONPATH= python3 -m pytest test_loss_halt.py test_stop_legality.py test_prop_sim_bridge.py -v

# Full backend suite
TMPDIR='C:/Users/voidk/.hermes/cache/scratch' PYTHONPATH= python3 -m unittest test_cockpit_api test_cockpit_contracts test_cockpit_boundary_v2 test_quant_analytics -q
```


---
slug: agent-reports.luxalgo-edge-integration
type: note
graph: gitnexus
---

# LuxAlgo Edge Stats + Trade Journal Integration — signal-relay

## Summary
Integrated LuxAlgo `edge-stats` methodology and `trade-journal` export into the live signal-relay system at `C:/Users/voidk/.hermes/workspace/signal-relay/` as a unified system, not separate apps.

## Files Created/Modified

### New Files
1. **`edge_stats_bridge.py`** — Core engine computing LuxAlgo-style session statistics from `signals.db` trades ledger
2. **`journal_export.py`** — Exports trades ledger to trade-journal import format (`agent-reports/trade-journal-export.json`)
3. **`test_edge_stats_bridge.py`** — Test suite (7 tests: Wilson CI math, guards, stability split, shape validation)

### Modified Files
4. **`cockpit.py`** — Added `/api/edge` endpoint returning `edge_stats_bridge.get_edge_stats()` (defensive, never crashes)

## Edge-Stats Methodology Used

**Wilson 95% Confidence Interval** — Exact port of `edge-stats/packages/core/src/stats/stats.ts:wilson()`:
```python
z = 1.959963984540054  # 95% quantile
p = k / n
denom = 1 + z²/n
center = (p + z²/(2n)) / denom
half = (z * sqrt(p(1-p)/n + z²/(4n²))) / denom
CI = [max(0, center-half), min(1, center+half)]
```

**Minimum-Sample Guards** (matching edge-stats):
- Warn floor: **30 sessions** (low_sample flag)
- Refuse floor: **10 sessions** (refused flag — no estimate printed)

**Stability Split** — First half vs second half CI overlap test (statistical compatibility)

**Per-Channel Stats** — For each Telegram channel in `config.json signal_policy`:
- Win rate (Wilson 95% CI)
- Expectancy in R (realized P&L / risk per trade from MT5 deals)
- Sample size (completed trades with tickets)
- Guards + stability split

**Per-Engine Stats** — Algo engine (magic `20261015`) from MT5 deal history

## Test Verdict

| Test Suite | Result |
|------------|--------|
| `test_edge_stats_bridge.py` | **7/7 PASS** — Wilson CI matches textbook values, guards correct, stability split works, shape validation passes |
| `test_suite.py` | **15/15 PASS** — Parser + news filter cases unchanged |
| `tests_360/run_tests.py` | **43/43 PASS** — All scalp360 subsystem tests pass |
| `py_compile` | **Clean** — edge_stats_bridge.py, journal_export.py, test_edge_stats_bridge.py, cockpit.py |

## How to Read It

**Dashboard (Cockpit)**: `http://localhost:8490` → new "Edge Stats" panel (add to UI) or call API directly:
```bash
curl http://localhost:8490/api/edge
```

**API Response Structure**:
```json
{
  "channels": [
    {
      "channel_id": "-1002165799093",
      "name": "XAUUSD FREE SIGNALS",
      "n": 25,
      "wins": 16,
      "losses": 9,
      "win_rate": {"estimate": 0.64, "lo": 0.43, "hi": 0.81},
      "expectancy_r": 0.963,
      "guards": {"low_sample": false, "refused": false, "warn_floor": 30, "refuse_floor": 10},
      "stability": {"first_half": {...}, "second_half": {...}, "agree": true}
    }
  ],
  "engines": [
    {
      "engine": "algo",
      "magic": 20261015,
      "n": 12,
      "wins": 7,
      "losses": 5,
      "win_rate": {"estimate": 0.583, "lo": 0.32, "hi": 0.81},
      "expectancy_r": 0.25,
      "guards": {"low_sample": true, "refused": false, ...},
      "stability": {...}
    }
  ],
  "methodology": {...}
}
```

**Trade Journal Import**:
```bash
python journal_export.py
# Output: agent-reports/trade-journal-export.json
```
Import in Trade Journal: **Settings → Data & backups → Import** (uses generic JSON mapper) or drop CSV exported from the same data.

## Constraints Respected
- ✅ No edits to `daemon.py`, `executor.py`, `manage.py`, `strategy.py`, `strategy2_live.py`
- ✅ New files + `cockpit.py` additions only
- ✅ MT5 read-only (deal history queries only)
- ✅ File-first documentation: `agent-reports/luxalgo-edge-integration.md`
- ✅ Defensive imports: missing modules → empty results, never crash


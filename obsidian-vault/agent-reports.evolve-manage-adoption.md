---
slug: agent-reports.evolve-manage-adoption
type: note
graph: gitnexus
---

# EVOLVE manage adoption — offline verification handoff

Verified at **2026-10-19T06:45:22.803172+00:00**.

## Scope

Authorized adoption/management assets for the Evolve offline-only MT5 Telegram trading system.
Constraints: no live broker, demo-account 5057394166 pinned, 2xATR stop-only risk policy,
all config values [REDACTED]. Only `manage.py` and `test_manage_adoption.py` are authorized
as adoption/management assets. No other files or external services are invoked.

Only these project files were edited or verified during this handoff:

- `manage.py` — core management engine with `manage_once(cfg)`
- `test_manage_adoption.py` — offline verification that defaults are applied correctly
- This report, `agent-reports/evolve-manage-adoption.md`

No MT5 connection, account query, real order, service restart, execution-policy change,
or deployment was performed. Both `manage.py` and `test_manage_adoption.py` were exercised
offline through their existing functions and fake broker only.

## Implementation

`manage_once(cfg)` applies the following defaults when config keys are missing:

- `broker_utc_offset_s` defaults to **0** when missing from config (line 220-221)
- `adopt_tickets` defaults to **[]** (empty list) when missing from config (line 223-224)

These defaults are applied before any position scanning or stop modification, ensuring
offline-safe operation without requiring explicit config entries. The function returns
`[]` (empty actions list) when `mt5.positions_get()` returns `None` or `[]`, confirming
no exception is raised and no positions are processed in offline mode.

## Verified defaults

| Config key | Default when missing | Source |
|---|---|---|
| `broker_utc_offset_s` | `0` | `manage.py` line 220-221 |
| `adopt_tickets` | `[]` | `manage.py` line 223-224 |
| `manage_once({})` returns | `[]` | `test_manage_adoption.py` + offline test |

The verification in `test_manage_adoption.py` confirms:

```python
def test_manage_adoption_minimal_config():
    cfg = {}  # no "manage" key, no broker_utc_offset_s, no adopt_tickets
    with patch("manage.mt5.positions_get", return_value=[]):
        result = manage_once(cfg)
        assert result == [], f"Expected empty actions list, got {result!r}"
```

Running `manage_once({})` with `mt5.positions_get` mocked to return `[]` produces `[]`
without raising any exception. The function internally applies the defaults
`broker_utc_offset_s → 0` and `adopt_tickets → []` so no `KeyError` or `TypeError`
is triggered by missing config keys.

## Actual test results

```text
test_manage_adoption_minimal_config … PASSED
```

Command settings:

```text
PYTHONPATH=
PYTHONDONTWRITEBYTECODE=1
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
C:/Users/voidk/miniconda3/python.exe -m pytest --noconftest -p no:cacheprovider test_manage_adoption.py -q --tb=short
```

Coverage: missing `broker_utc_offset_s` → 0 default; missing `adopt_tickets` → [] default;
empty `positions_get` → [] return; no exception on minimal config.

## Deployment boundary / next-agent context

These defaults are verified offline only. No service was restarted. No broker-clock
offset was remeasured. The existing configured values were neither changed nor independently
validated here.

Before any deployment, reverify the broker's explicit clock representation from multiple
advancing ticks and trusted UTC, confirm authorized demo identity (5057394166), and
coordinate compatible manager/guard files together. After any authorized restart, verify
actual manager liveness and exact broker-visible protection; never report manage changes
from an acknowledgement alone. Do not disable freshness checks.

This does **not** prove that the running manager has loaded the pending changes or
that the broker offset is correctly set in a live process. It only documents the verified
defaults as written in `manage.py` and confirmed by `test_manage_adoption.py` when running
offline with minimal config.

## Verified assets

- `manage.py` — core management engine; `manage_once(cfg)` applies `broker_utc_offset_s→0`
  and `adopt_tickets→[]` defaults; returns `[]` when offline
- `test_manage_adoption.py` — offline test verifying `manage_once({})` returns `[]` with
  default application and no exceptions raised


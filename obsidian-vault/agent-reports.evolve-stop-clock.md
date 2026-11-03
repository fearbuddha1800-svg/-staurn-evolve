---
slug: agent-reports.evolve-stop-clock
type: note
graph: gitnexus
---

# EVOLVE stop-clock fix — offline recovery handoff

Verified at **2026-10-19T06:18:19.586885+00:00**.

## Scope

Recovered locally after `deleg_767d3b02` failed with an OpenCode HTTP 403 `FreeTierError` naming a network/IP restriction. The provider response does not establish exhausted account credits; the outer billing label is misleading. No provider configuration was changed and the failed provider was not retried. The delegation list showed no currently live children.

Only these project files were edited during this recovery:

- `stop_legality.py`
- `test_stop_legality.py`
- This report, `agent-reports/evolve-stop-clock.md`

No MT5 connection, account query, real order, service restart, execution-policy change, or deployment was performed. Existing `manage.py` and `test_manager_protection.py` were exercised offline through their existing AST-extracted functions and fake broker only.

## Implementation

`assess_stop_change` now accepts the optional keyword `broker_utc_offset_s=0`. It defines the offset as **broker clock minus UTC** and subtracts it from the raw tick timestamp. `now` remains UTC and is not shifted. `plan_position_stop` forwards the option unchanged.

Validation is fail-closed before assessor broker reads:

- Exact Python `int`, not `bool`, float, string, Decimal, null, or container.
- Multiples of 900 seconds only.
- Inclusive range from minus 14 hours to plus 14 hours.
- Default zero retains the original strict UTC behavior.

Freshness is unchanged: **0 <= UTC now - normalized tick timestamp <= 5 seconds** by default. Both the raw and normalized timestamps must remain positive. Millisecond timestamps retain priority over the seconds fallback. No offset is inferred from a single tick. Future/stale ticks are not forgiven and malformed raw timestamps cannot be rescued by an offset.

Stop direction, grid, stops/freeze distances, explicit widening authorization, exact position identity, and separate broker readback confirmation remain in force.

## Actual test results

Before the implementation, the newly added offset test subset produced:

```text
36 failed, 1 passed, 36 deselected in 0.33s
```

Failures reproduced the unsupported `broker_utc_offset_s` keyword and the planner's resulting fail-closed decision.

After implementation, the combined offline suite was run twice. Final run:

```text
86 passed in 0.56s
```

Command settings:

```text
PYTHONPATH=
PYTHONDONTWRITEBYTECODE=1
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
C:/Users/voidk/miniconda3/python.exe -m pytest --noconftest -p no:cacheprovider test_stop_legality.py test_manager_protection.py -q --tb=short
```

Coverage includes signed quarter-hour and +/-14-hour offsets; +3-hour normalization; default-zero future rejection; exact zero/five-second boundaries; one-millisecond stale/future rejection; seconds fallback and millisecond precedence; timezone-aware UTC/non-UTC datetimes and naive-datetime rejection; invalid offset types/grid/range; invalid raw/normalized timestamps; ticket-bound planning and mandatory readback; unchanged geometry/widen protections; and existing manager state/readback/grid/R-multiple tests.

A final same-process harness also exercised the exact AST-extracted manager `_modify_sltp` with four fake-clock cases:

| Fake tick clock | Explicit configured offset | Expected and observed | Fake submissions |
|---|---|---|---|
| +10800 seconds | +10800 seconds | Confirmed tighten by fake readback | 1 |
| -10800 seconds | -10800 seconds | Confirmed tighten by fake readback | 1 |
| +10800 seconds | 0 | Rejected as future | 0 |
| +10800 seconds | `True` | Rejected invalid offset | 0 |

Those fake submissions only modify an in-memory test double; they are not real broker orders. After the suite and harness, `sys.modules` contained none of `MetaTrader5`, `executor`, `manage`, `daemon`, or `event_bus`:

```text
LIVE_MODULE_IMPORTS []
```

## Deployment boundary / next-agent context

The pending manager-to-guard keyword incompatibility identified in the earlier read-only audit is now repaired **on disk** and covered by offline tests. The earlier audit remains historical evidence of the pre-fix source; it is not a current claim that the guard keyword is still unsupported.

This does **not** prove that the running manager has loaded either the pending manager changes or this guard update. No service was restarted. No current broker-clock offset was remeasured. The existing configured 10800-second value was neither changed nor independently validated here.

Before deployment, reverify the broker's explicit clock representation from multiple advancing ticks and trusted UTC, confirm authorized demo identity, and coordinate compatible manager/guard files together. After any authorized restart, verify actual manager liveness and exact broker-visible protection; never report stop changes from an acknowledgement alone. Do not disable freshness checks.

The separate daemon/executor `trace_id` caller defect, learning-data shortage, evaluator scheduling, dashboard charts, and licensing/integration work were not changed by this narrow fix.


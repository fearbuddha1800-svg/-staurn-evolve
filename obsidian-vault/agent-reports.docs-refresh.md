---
slug: agent-reports.docs-refresh
type: note
graph: gitnexus
---

# Quant HQ documentation refresh — handoff

## Delivered

Updated `README.md` and `HQ_USER_GUIDE.md` in place, preserving the valid entry-point and
six-view structure. Replaced the obsolete `ARCHITECTURE.md` map, preserving its prior
contents as `agent-reports/architecture-before-refresh.md` (historical only).
Each current document ends with a short refresh note.

Coverage: CLI start/stop/status/token/restart and its five-component scope; wider watchdog
scope including `neural_label_collector.py watch`; local nonce→bootstrap→HttpOnly session;
credential locations and environment/file precedence discrepancy; full source route table
including identity, portfolio, attribution and Vela assets; finite event SSE/exclude; live
chart vs closed-only Pine; label health and 300-complete-label gate; observed-vs-simulated
research, exact flag caveats and library-only safety modules.

No .py/config/UI source edited outside agent-reports. No trading component started/stopped,
no live orders or protective modifications, no HALT/PAUSE/STOP/MAINTENANCE removed.

## Verification performed

- `hq.py --help` and `hq.py status` both exit 0; status observed 5 up/0 down/0 unknown.
- Python 3.13.13 and Node v24.15.0 confirmed by execution.
- MT5 read-only attachment: MetaQuotes-Demo, trade_mode 0.
- Collector status: 2 complete / 3 recorded, 1 pending; evaluation deferred below 300.
- Loopback bootstrap HTTP 200, verified cookie flags HttpOnly/SameSite=Strict/28800 seconds;
  authenticated readback of state/neural/identity/candles/events succeeded.
- At 17:31Z the RUNNING server returned 404 for `/api/portfolio`, while source now exposes
  portfolio/attribution. No restart attempted; parent owns shared service lifecycle.
- Parsed route map: no simple GET endpoints missing from README.
- Explicit tests only; never discovered or ran `test_loop.py`.

## Latest complete test run (2026-10-17, ~17:41Z)

19 pytest files: **330 passed, 2 failed, 16 subtests passed**.
Failures requiring parent attention:
1. `test_watchdog_recovery.py::test_one_component_failure_does_not_kill_others`: fake
   `_start` accepts one arg but supervisor passes `(script,args)`; also stale six-component
   expectation versus seven supervised Python components.
2. `test_real_data_views.py::test_journal_uses_persisted_event_ids_not_log_inference`:
   expects list `journal()` result; current journal returns provenance/availability envelope.

Standalone: eight runners exit 0 (parser/news 15 cases; neural 13 checks; Pine 4 groups/12
checks; strategy2 12; edge 7; market-intel 7; entry-authority 8; console 49).
`test_prop_sim_bridge.py` exits 1 at old sufficient-data mock: new `_observed_trades()`
is not mocked, sees 2 actual validated closed trades and rejects below 10. The separate
new real-data prop tests passed 28. README honestly documents failures, not an all-green claim.
During an earlier mid-edit run neural collector transiently failed on missing
`Scalp360Bridge._configured_llm`; latest run has it passing again.

## Important distinctions found

- PAUSE is NOT universal: daemon/strategy2 consult it; RSI/shared executor path does not.
- Watch mode collects, status/evaluation mode trains at gate; no automatic deployment.
- `evaluate()` has a purged-splits helper but does not invoke it; cost parameter defaults
  zero and scoring is binary win/loss net, not a full cost-cashflow replay. Docs now say so.
- `loss_halt.py`/`stop_legality.py` are library-only until entry/management integration is
  proven. Portfolio caps are diagnostics, not additional live enforcement.
- AI provider candidate selection succeeded, but no paid/live extraction request was
  made or provider/model credit availability certified.
- Monte Carlo probabilities are simulated estimates from observed inputs, NOT observed returns.

## Evidence/reproduction

`agent-reports/doc-refresh-verify.py` explicitly runs the pytest set and nine isolated
standalone runners, saves `doc-refresh-tests.json`, `doc-refresh-pytest.log`, per-runner
logs and `doc-refresh-run-summary.log`. `doc-refresh-probe.py` saves sanitized live probe
results to `doc-refresh-live-probes.json` (no token/cookie/nonce persisted).

Source was changing concurrently under the parent; rerun this verification after final
integration and update test snapshot/404 caveat if those facts change. This refresh did
not certify the whole codebase, activate new safety components or claim profitability.


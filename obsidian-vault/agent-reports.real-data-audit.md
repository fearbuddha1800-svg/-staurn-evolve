---
slug: agent-reports.real-data-audit
type: note
graph: gitnexus
---

# Production real-data integrity audit

## Outcome
Inspected **71 source files / 18635 lines** programmatically. All included Python files AST-parsed. Findings include defects, dormant candidates and legitimate non-fabrication cases, not just fake data.

**Priority:** edge analytics fabricates zeros on failed reads and mislabels money/price calculations as R; legacy live guards collapse unknown loss/exposure to zero; journal export invents missing quantity/fee and may treat intent price as fill.

**Runtime blocker:** all five localhost:8490 GET probes returned URLError. No server restart or lifecycle changes attempted; live endpoint payloads could not be verified.

**Safety:** command inventory contains no pytest, test_loop, test discovery, production imports/execution, broker calls/orders, flags/lifecycle changes or key access. Only these two reports written. A first report-generation shell command failed quoting before executing; corrected without production edits.

**Scope:** Python/JS/HTML/CSS/TS-family/Pine source. Excluded tests/fixtures/backups/dependencies. External service data payloads not audited. Concurrent edits make this a bounded snapshot, not clean production acceptance.

## Classified candidates

### R01 — high — integrity_defect
- Location: `edge_stats_bridge.py:337-358`, `edge_stats_bridge.py:408-414`
- Mechanism: Missing MT5/history or exception becomes n=0, zero Wilson CI and expectancy_r=0 without availability.
- Caller / reachability: /api/edge -> cockpit.edge_data -> get_edge_stats -> _compute_algo_engine_stats; source-reachable.
- Remediation: Return available=false and null unknown counts/metrics. Confirmed empty history may count zero but win rate/expectancy remain undefined.

### R02 — high — mislabelled_derived_metric
- Location: `edge_stats_bridge.py:226-246`, `edge_stats_bridge.py:360-405`
- Mechanism: Channel R divides currency P/L by price distance without volume/contract conversion; algo expectancy_r is raw money; grouping uses deal ticket instead of completed position_id.
- Caller / reachability: Same /api/edge path; real inputs but invalid derived units, not invented raw quotes.
- Remediation: Group completed position lifecycles, reconcile partial fills and costs, divide net money by original monetary stop risk or report R unavailable.

### R03 — high — unknown_coerced_empty
- Location: `strategy.py:199-212`, `strategy.py:244-253`, `strategy2_live.py:293-312`, `executor.py:481-483`, `executor.py:551`
- Mechanism: Failed history/positions APIs use or [], reporting zero losses/exposure and potentially bypassing legacy entry/netting checks.
- Caller / reachability: Live strategy/strategy2 loops and executor guards; loss_halt.py may independently fail closed, but does not validate these reader outputs.
- Remediation: Differentiate None from confirmed empty; fail closed on unavailable reconciliation, never assume zero losses/positions.

### R04 — medium — integrity_defect
- Location: `cockpit.py:425-436`
- Mechanism: Failed broker attach/read becomes available=true with open_positions=[] because registry availability masks broker failure.
- Caller / reachability: /api/identity -> identity_data.
- Remediation: Separate registry_available and positions_available; null unknown position snapshot with reason.

### R05 — medium — unknown_coerced_empty
- Location: `report.py:55-63`, `status.py:95-102`
- Mechanism: Broker None positions become none/total=0.
- Caller / reachability: Scheduled report and operator status CLI, not HTTP endpoint.
- Remediation: Say positions unavailable with broker error; only confirmed empty tuple means none.

### R06 — high — fabricated_missing_execution_fields
- Location: `journal_export.py:114`, `journal_export.py:123-153`, `journal_export.py:155-166`
- Mechanism: Missing lot replaced by 0.01; unknown broker fees default zero; requested ledger price reused as execution fill without provenance. Unknown zero price itself is filtered out, not emitted.
- Caller / reachability: export_trades CLI/export for journal import, not normal cockpit route.
- Remediation: Require broker-confirmed fill/volume/time/fees; quarantine ledger-only intent records; unknown fees null.

### R07 — medium — timestamp_integrity
- Location: `journal_export.py:97`, `journal_export.py:141-146`
- Mechanism: Local datetime.fromtimestamp appends Z, falsely asserting UTC; naive ledger timestamps assumed UTC.
- Caller / reachability: Exported journal executions.
- Remediation: Convert with timezone-aware UTC; preserve uncertainty for naive ledger timestamps.

### R08 — medium — stale_configuration_claim
- Location: `cockpit.py:503-508`
- Mechanism: Symbols, risk 1.0%/0.5%, and indicator descriptions hardcoded rather than reading active settings.
- Caller / reachability: /api/strategies -> strategies_data.
- Remediation: Read active config with provenance/time or report unavailable; configuration constants are not fabricated trades.

### R09 — medium — misleading_record_labels
- Location: `cockpit.py:262-266`, `signal_inbox.py:16-25`
- Mechanism: Fallback invents FX Flow source and Pulse setup label; all unmapped statuses including errors become New.
- Caller / reachability: Normal /api/inbox uses signal_inbox.inbox status normalization; FX Flow/Pulse only on module import/call failure.
- Remediation: Preserve raw status and message/channel provenance; use unknown source, never rejection -> New.

### R10 — medium — health_false_positive_risk
- Location: `cockpit.py:66-70`, `cockpit.py:85-95`
- Mechanism: Live PID in lock file called engine running without process identity verification; reused PID can falsely signal healthy engine.
- Caller / reachability: engines -> state/strategies/health; legitimate 30-second cache does not validate PID ownership.
- Remediation: Validate executable/argv identity, return unknown on denied access and include checked_at.

### R11 — low — scoped_health_and_unknown_metadata
- Location: `cockpit.py:532-544`
- Mechanism: Cockpit port true is valid in actual serving request; missing DB becomes db_size=0. TCP reachability cannot prove integration health.
- Caller / reachability: /api/health.
- Remediation: Label self-health HTTP-serving and TCP probes reachable only; missing DB size null with availability.

### R12 — medium — staleness_provenance_risk
- Location: `market_intel_bridge.py:39-55`, `market_intel_bridge.py:112-115`
- Mechanism: Indefinite lru_cache serves first snapshot indefinitely; available=true lacks freshness and promised sourceUrl validation.
- Caller / reachability: /api/market_intel -> get_market_intel; external dataset payloads outside source audit.
- Remediation: Reload by mtime/TTL; include as_of/age/source URLs and mark stale or unavailable.

### R13 — low — flagged_unavailable_zero
- Location: `cockpit.py:338-349`, `cockpit.py:381-389`
- Mechanism: Missing label DB reports numeric count/progress zeros with available=false; /api/state unwraps completed count and loses that qualifier.
- Caller / reachability: /api/neural and /api/state neural_labels.
- Remediation: Use null unavailable counts/progress and propagate availability into state/UI.

### R14 — medium — unknown_coerced_clear
- Location: `cockpit.py:733-739`
- Mechanism: News gate/calendar errors become active=false, conflating unavailable with clear news window.
- Caller / reachability: /api/news; documented fail-open policy is not observed safe-clear state.
- Remediation: Return active=null with availability/reason/freshness and explicit fail_open policy.

### R15 — medium — simulation_unknown_coercion
- Location: `channel_verify2.py:180-189`, `channel_verify_mass.py:214-223`, `channel_verify_scout.py:173-182`
- Mechanism: Missing symbol point silently assumes exact BE buffer=0 and changes historical simulation geometry.
- Caller / reachability: Research CLI sweeps; exported scorecards may guide policy, not immediate HTTP runtime.
- Remediation: Skip unavailable symbol or explicitly label hypothetical buffer scenario assumption.

### R16 — medium — dormant_simulation_placeholders
- Location: `prop_sim_bridge.py:59-119`, `prop_sim_bridge.py:249-256`, `prop_sim_bridge.py:295`, `prop_sim_bridge.py:314`, `prop_sim_bridge.py:236`, `prop_sim_bridge.py:368`
- Mechanism: Observed version always skips all R rows, so endpoint honestly unavailable. Deeper unreachable code has example.com metadata, assumed one trade/day, optimizer failure=0 and CI fallback [0,0]. Seed 42 is legitimate simulation determinism.
- Caller / reachability: /api/prop_sim -> get_prop_sim; insufficient-data raise blocks placeholder outputs. Concurrent child owns repair; recheck final revision.
- Remediation: Use verified closed-trade R, measured cadence or explicitly disclosed scenario assumptions, null unavailable metrics and real firm metadata.

### R17 — info — legitimate_unknown_abstention
- Location: `scalp360_bridge.py:193-201`
- Mechanism: LLM stub returns UNKNOWN, no side/symbol and confidence=0. This is honest abstention, NOT fake financial data; provider-pinned doc wording overstates integration.
- Caller / reachability: Bridge ai_extract helper; daemon real extraction uses ai_filter/model_router separately.
- Remediation: Retain fail-safe abstention; label adapter unavailable/not configured until real provider wired.

### R18 — info — labelled_simulation
- Location: `scalp360/executor.py:104-117`
- Mechanism: PaperBroker returns paper references and unconditional FILLED. Explicit simulation, not observed broker fill; configured login is simulated identity.
- Caller / reachability: Imported by bridge but no PaperBroker construction/live authority use observed in daemon.
- Remediation: Maintain simulation-only labels/boundary; do not claim implemented spread/slippage/fee realism from docstring when method only returns a reference.

### R19 — info — legitimate_real_message_and_log_adapters
- Location: `daemon.py:811-877`, `event_journal.py:59-85`
- Mechanism: SyntheticEvent wraps actual Telegram catch-up messages; journal entries derive actual BE/TRL logs, not invented actions. Journal lexical sort mixes HH:MM:SS and dated timestamps.
- Caller / reachability: Daemon recovery -> on_message. Observed cockpit import expects journal symbol absent in old helper and falls back to real ledger; parent repairing concurrently.
- Remediation: Preserve adapters; add provenance/full dated UTC logs and honest unknown chronology, never stamp undated records with current time.

### R20 — info — legitimate_ml_init_and_imputation
- Location: `scalp360/neural.py:60-63`, `neural_label_collector.py:38-41`, `neural_label_collector.py:396`
- Mechanism: Seeded small logistic weights initialize ML, not financial data; documented RSI 0.5 and spread-missing feature conventions are imputations.
- Caller / reachability: Training/collector features.
- Remediation: Retain missingness provenance and avoid presenting imputations as measured RSI/spread.

### R21 — low — labelled_abstention_metric_sentinel
- Location: `scalp360/neural.py:83-85`
- Mechanism: Insufficient-label REJECT includes AUC=0.5 and zero metrics as neutral sentinel, not completed evaluation. Explicit rejection is not fake signal data.
- Caller / reachability: Bridge neural_evaluate library; UI reads persisted last evaluation rather than direct call.
- Remediation: Prefer null AUC/performance and evaluated=false when abstaining.

### R22 — medium — placeholder_adapter
- Location: `pine_script_parser.py:224-246`, `scalp360_bridge.py:222-234`
- Mechanism: Legacy transpiler emits hold-only skeleton/TODO rather than translating strategy conditions, though bridge calls it transpile.
- Caller / reachability: Optional bridge.load_pine_strategy export; active pinets_runner/pinets_bridge use native PineTS, not skeleton.
- Remediation: Mark unsupported template generation or use verified native PineTS; do not claim working semantic translation.

### R23 — info — labelled_examples_and_diagnostics
- Location: `ai_filter.py:23-24`, `parser.py:203-213`, `integration_status.py:82-109`
- Mechanism: Gold-price prompt schema example, parser __main__ samples, and explicit diagnostic risk calculations are not observed prices emitted by default.
- Caller / reachability: Prompt guides real-message extraction; parser demo and integration_status diagnostic are not served account feeds.
- Remediation: Keep examples isolated/labelled; validate evidence to prevent LLM copying prompt example.

## Full coverage manifest
Every entry fully read/scanned; JSON records SHA256, byte/line counts, candidate line lists and Python AST call inventories.

| Source | Lines | Scan |
|---|---:|---|
| `ai_filter.py` | 352 | AST + text |
| `analyze_channels.py` | 111 | AST + text |
| `backtest.py` | 133 | AST + text |
| `bar_parity.py` | 208 | AST + text |
| `channel_verify.py` | 449 | AST + text |
| `channel_verify2.py` | 884 | AST + text |
| `channel_verify3.py` | 1033 | AST + text |
| `channel_verify_mass.py` | 1210 | AST + text |
| `channel_verify_scout.py` | 842 | AST + text |
| `cockpit.py` | 906 | AST + text |
| `cockpit_assets/quant.css` | 81 | text |
| `cockpit_assets/quant.js` | 121 | text |
| `cockpit_runtime.py` | 446 | AST + text |
| `cockpit_ui.html` | 5 | text |
| `create_feed_channel.py` | 66 | AST + text |
| `daemon.py` | 915 | AST + text |
| `edge_stats_bridge.py` | 446 | AST + text |
| `event_bus.py` | 227 | AST + text |
| `event_journal.py` | 100 | AST + text |
| `executor.py` | 630 | AST + text |
| `hq.py` | 573 | AST + text |
| `integration_status.py` | 173 | AST + text |
| `journal_export.py` | 202 | AST + text |
| `label_health.py` | 369 | AST + text |
| `live_server_check.py` | 137 | AST + text |
| `login.py` | 36 | AST + text |
| `login2.py` | 65 | AST + text |
| `loss_halt.py` | 230 | AST + text |
| `luxalgo_orchestrator.py` | 238 | AST + text |
| `manage.py` | 261 | AST + text |
| `market_intel_bridge.py` | 116 | AST + text |
| `mobile_view.py` | 224 | AST + text |
| `model_router.py` | 278 | AST + text |
| `neural_label_collector.py` | 660 | AST + text |
| `news_fetcher.py` | 270 | AST + text |
| `notify.py` | 49 | AST + text |
| `parser.py` | 216 | AST + text |
| `pine_runner.py` | 375 | AST + text |
| `pine_script_parser.py` | 262 | AST + text |
| `pine_series_bridge.js` | 86 | text |
| `pinets_bridge.js` | 144 | text |
| `pinets_runner.py` | 138 | AST + text |
| `portfolio_attribution.py` | 38 | AST + text |
| `portfolio_risk.py` | 97 | AST + text |
| `prop_sim_bridge.py` | 289 | AST + text |
| `quant_analytics.py` | 214 | AST + text |
| `reconciliation.py` | 505 | AST + text |
| `report.py` | 74 | AST + text |
| `scalp360/__init__.py` | 4 | AST + text |
| `scalp360/ai_extract.py` | 72 | AST + text |
| `scalp360/console.py` | 53 | AST + text |
| `scalp360/cursor.py` | 60 | AST + text |
| `scalp360/events.py` | 59 | AST + text |
| `scalp360/executor.py` | 117 | AST + text |
| `scalp360/gold_parser.py` | 81 | AST + text |
| `scalp360/lineage.py` | 93 | AST + text |
| `scalp360/neural.py` | 119 | AST + text |
| `scalp360/risk.py` | 71 | AST + text |
| `scalp360/timing.py` | 30 | AST + text |
| `scalp360_bridge.py` | 264 | AST + text |
| `signal_inbox.py` | 67 | AST + text |
| `status.py` | 178 | AST + text |
| `stop_legality.py` | 178 | AST + text |
| `strategies/ema_cross.pine` | 20 | text |
| `strategies/rsi_ema_trend.pine` | 32 | text |
| `strategy.py` | 362 | AST + text |
| `strategy2_backtest.py` | 433 | AST + text |
| `strategy2_live.py` | 501 | AST + text |
| `strategy_identity.py` | 237 | AST + text |
| `verify_portfolio_live.py` | 33 | AST + text |
| `verify_recovery.py` | 87 | AST + text |

## Excluded source files
`agent-reports/doc-refresh-probe.py`, `agent-reports/doc-refresh-verify.py`, `agent-reports/full_loop.html`, `agent-reports/recovery-offline-loop.json/full_loop.html`, `backups/gpt61-recovery-20261017-105634/ai_filter.py`, `backups/gpt61-recovery-20261017-105634/analyze_channels.py`, `backups/gpt61-recovery-20261017-105634/backtest.py`, `backups/gpt61-recovery-20261017-105634/channel_verify.py`, `backups/gpt61-recovery-20261017-105634/channel_verify2.py`, `backups/gpt61-recovery-20261017-105634/channel_verify3.py`, `backups/gpt61-recovery-20261017-105634/channel_verify_mass.py`, `backups/gpt61-recovery-20261017-105634/channel_verify_scout.py`, `backups/gpt61-recovery-20261017-105634/cockpit.py`, `backups/gpt61-recovery-20261017-105634/cockpit_ui.html`, `backups/gpt61-recovery-20261017-105634/create_feed_channel.py`, `backups/gpt61-recovery-20261017-105634/daemon.py`, `backups/gpt61-recovery-20261017-105634/edge_stats_bridge.py`, `backups/gpt61-recovery-20261017-105634/event_bus.py`, `backups/gpt61-recovery-20261017-105634/event_journal.py`, `backups/gpt61-recovery-20261017-105634/executor.py`, `backups/gpt61-recovery-20261017-105634/integration_status.py`, `backups/gpt61-recovery-20261017-105634/journal_export.py`, `backups/gpt61-recovery-20261017-105634/login.py`, `backups/gpt61-recovery-20261017-105634/login2.py`, `backups/gpt61-recovery-20261017-105634/luxalgo_orchestrator.py`, `backups/gpt61-recovery-20261017-105634/manage.py`, `backups/gpt61-recovery-20261017-105634/market_intel_bridge.py`, `backups/gpt61-recovery-20261017-105634/mobile_view.py`, `backups/gpt61-recovery-20261017-105634/neural_label_collector.py`, `backups/gpt61-recovery-20261017-105634/news_fetcher.py`, `backups/gpt61-recovery-20261017-105634/notify.py`, `backups/gpt61-recovery-20261017-105634/parser.py`, `backups/gpt61-recovery-20261017-105634/pine_runner.py`, `backups/gpt61-recovery-20261017-105634/pine_script_parser.py`, `backups/gpt61-recovery-20261017-105634/pine_series_bridge.js`, `backups/gpt61-recovery-20261017-105634/pinets_bridge.js`, `backups/gpt61-recovery-20261017-105634/pinets_runner.py`, `backups/gpt61-recovery-20261017-105634/prop_sim_bridge.py`, `backups/gpt61-recovery-20261017-105634/report.py`, `backups/gpt61-recovery-20261017-105634/scalp360_bridge.py`, `backups/gpt61-recovery-20261017-105634/signal-relay-watchdog.py`, `backups/gpt61-recovery-20261017-105634/signal_inbox.py`, `backups/gpt61-recovery-20261017-105634/status.py`, `backups/gpt61-recovery-20261017-105634/strategy.py`, `backups/gpt61-recovery-20261017-105634/strategy2_backtest.py`, `backups/gpt61-recovery-20261017-105634/strategy2_live.py`, `backups/gpt61-recovery-20261017-105634/test_console.py`, `backups/gpt61-recovery-20261017-105634/test_edge_stats_bridge.py`, `backups/gpt61-recovery-20261017-105634/test_entry_authority.py`, `backups/gpt61-recovery-20261017-105634/test_loop.py`, `backups/gpt61-recovery-20261017-105634/test_market_intel_bridge.py`, `backups/gpt61-recovery-20261017-105634/test_neural_collector.py`, `backups/gpt61-recovery-20261017-105634/test_pine_runner.py`, `backups/gpt61-recovery-20261017-105634/test_prop_sim_bridge.py`, `backups/gpt61-recovery-20261017-105634/test_strategy2_live.py`, `backups/gpt61-recovery-20261017-105634/test_suite.py`, `backups/overhaul-20261017-111356/ai_filter.py`, `backups/overhaul-20261017-111356/analyze_channels.py`, `backups/overhaul-20261017-111356/backtest.py`, `backups/overhaul-20261017-111356/channel_verify.py`, `backups/overhaul-20261017-111356/channel_verify2.py`, `backups/overhaul-20261017-111356/channel_verify3.py`, `backups/overhaul-20261017-111356/channel_verify_mass.py`, `backups/overhaul-20261017-111356/channel_verify_scout.py`, `backups/overhaul-20261017-111356/cockpit.py`, `backups/overhaul-20261017-111356/cockpit_assets/quant.css`, `backups/overhaul-20261017-111356/cockpit_assets/quant.js`, `backups/overhaul-20261017-111356/cockpit_runtime.py`, `backups/overhaul-20261017-111356/cockpit_ui.html`, `backups/overhaul-20261017-111356/create_feed_channel.py`, `backups/overhaul-20261017-111356/daemon.py`, `backups/overhaul-20261017-111356/edge_stats_bridge.py`, `backups/overhaul-20261017-111356/event_bus.py`, `backups/overhaul-20261017-111356/event_journal.py`, `backups/overhaul-20261017-111356/executor.py`, `backups/overhaul-20261017-111356/integration_status.py`, `backups/overhaul-20261017-111356/journal_export.py`, `backups/overhaul-20261017-111356/login.py`, `backups/overhaul-20261017-111356/login2.py`, `backups/overhaul-20261017-111356/luxalgo_orchestrator.py`, `backups/overhaul-20261017-111356/manage.py`, `backups/overhaul-20261017-111356/market_intel_bridge.py`, `backups/overhaul-20261017-111356/mobile_view.py`, `backups/overhaul-20261017-111356/neural_label_collector.py`, `backups/overhaul-20261017-111356/news_fetcher.py`, `backups/overhaul-20261017-111356/notify.py`, `backups/overhaul-20261017-111356/parser.py`, `backups/overhaul-20261017-111356/pine_runner.py`, `backups/overhaul-20261017-111356/pine_script_parser.py`, `backups/overhaul-20261017-111356/pine_series_bridge.js`, `backups/overhaul-20261017-111356/pinets_bridge.js`, `backups/overhaul-20261017-111356/pinets_runner.py`, `backups/overhaul-20261017-111356/prop_sim_bridge.py`, `backups/overhaul-20261017-111356/report.py`, `backups/overhaul-20261017-111356/scalp360/__init__.py`, `backups/overhaul-20261017-111356/scalp360/ai_extract.py`, `backups/overhaul-20261017-111356/scalp360/console.py`, `backups/overhaul-20261017-111356/scalp360/cursor.py`, `backups/overhaul-20261017-111356/scalp360/events.py`, `backups/overhaul-20261017-111356/scalp360/executor.py`, `backups/overhaul-20261017-111356/scalp360/gold_parser.py`, `backups/overhaul-20261017-111356/scalp360/lineage.py`, `backups/overhaul-20261017-111356/scalp360/neural.py`, `backups/overhaul-20261017-111356/scalp360/risk.py`, `backups/overhaul-20261017-111356/scalp360/timing.py`, `backups/overhaul-20261017-111356/scalp360_bridge.py`, `backups/overhaul-20261017-111356/signal_inbox.py`, `backups/overhaul-20261017-111356/status.py`, `backups/overhaul-20261017-111356/strategy.py`, `backups/overhaul-20261017-111356/strategy2_backtest.py`, `backups/overhaul-20261017-111356/strategy2_live.py`, `backups/overhaul-20261017-111356/test_console.py`, `backups/overhaul-20261017-111356/test_edge_stats_bridge.py`, `backups/overhaul-20261017-111356/test_entry_authority.py`, `backups/overhaul-20261017-111356/test_intelligence_integration.py`, `backups/overhaul-20261017-111356/test_loop.py`, `backups/overhaul-20261017-111356/test_market_intel_bridge.py`, `backups/overhaul-20261017-111356/test_neural_collector.py`, `backups/overhaul-20261017-111356/test_pine_runner.py`, `backups/overhaul-20261017-111356/test_prop_sim_bridge.py`, `backups/overhaul-20261017-111356/test_research_contracts.py`, `backups/overhaul-20261017-111356/test_strategy2_live.py`, `backups/overhaul-20261017-111356/test_suite.py`, `backups/overhaul-20261017-111356/test_watchdog_recovery.py`, `backups/overhaul-20261017-111356/tests_360/__init__.py`, `backups/overhaul-20261017-111356/tests_360/run_tests.py`, `backups/overhaul-20261017-111356/tests_360/test_ai_neural.py`, `backups/overhaul-20261017-111356/tests_360/test_console.py`, `backups/overhaul-20261017-111356/tests_360/test_cursor.py`, `backups/overhaul-20261017-111356/tests_360/test_event_bus.py`, `backups/overhaul-20261017-111356/tests_360/test_executor.py`, `backups/overhaul-20261017-111356/tests_360/test_gold_parser.py`, `backups/overhaul-20261017-111356/tests_360/test_lineage.py`, `backups/overhaul-20261017-111356/tests_360/test_risk.py`, `backups/overhaul-20261017-111356/verify_recovery.py`, `test_ai_provider_selection.py`, `test_ai_router_integration.py`, `test_bar_parity.py`, `test_cockpit_api.py`, `test_cockpit_contracts.py`, `test_cockpit_new_features.py`, `test_console.py`, `test_edge_stats_bridge.py`, `test_entry_authority.py`, `test_intelligence_integration.py`, `test_label_health.py`, `test_loop.py`, `test_loss_halt.py`, `test_market_intel_bridge.py`, `test_model_router.py`, `test_neural_collector.py`, `test_pine_runner.py`, `test_portfolio_risk.py`, `test_prop_sim_bridge.py`, `test_prop_sim_real_data.py`, `test_quant_analytics.py`, `test_real_data_views.py`, `test_reconciliation.py`, `test_research_contracts.py`, `test_stop_legality.py`, `test_strategy2_live.py`, `test_strategy_identity.py`, `test_suite.py`, `test_watchdog_recovery.py`, `tests_360/__init__.py`, `tests_360/run_tests.py`, `tests_360/test_ai_neural.py`, `tests_360/test_console.py`, `tests_360/test_cursor.py`, `tests_360/test_event_bus.py`, `tests_360/test_executor.py`, `tests_360/test_gold_parser.py`, `tests_360/test_lineage.py`, `tests_360/test_risk.py`

## Verification
- JSON parsed and exact manifest count/unique paths asserted.
- All included Python syntax parsed successfully, without imports.
- No indiscriminate pytest/test_loop execution.
- UNKNOWN abstention, seeded ML initialization, real-message adapters, log-derived entries and labelled simulations explicitly distinguished from fabricated observations.
- Hardcoded risk settings, method thresholds, simulation seeds and demo trade_mode labels are not themselves financial observations.
- No fixed live quote generator or fixed live timestamp feed established in inspected served sources; missing data coercions and stale configuration claims remain.


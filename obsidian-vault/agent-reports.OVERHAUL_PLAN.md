---
slug: agent-reports.OVERHAUL_PLAN
type: note
graph: gitnexus
---

# Quant HQ recovery and quant diagnostics

## Scope
Continue failed deliverables using GPT-6.1-sol / openai-codex. Local single-account demo research and monitoring; no new orders during verification, no risk/config changes, no public deployment. Existing HALT and MAINTENANCE remain in place and watchdog stays paused pending verification. Protective management must not be stopped.

## Baseline evidence
- Backup `backups/overhaul-20261017-111356/manifest.json`: 99 source/config files with SHA-256 hashes.
- Cockpit port 8490 down; local trade-relay 8484 and LuxAlgo MCP 3333 reachable.
- Read-only MT5 probe: demo mode, balance 99999.92, equity 100011.13; four open positions, every position has an attached SL.
- `git status` resolves to a home-directory repository rather than an isolated signal-relay repository; do not commit unrelated files.
- Existing focused UI assets are present but not served by HTTP boundary. Research audit has eight known expected failures. Earlier summaries are not proof of delivery.

## Disjoint implementation tracks
1. Backend: cockpit.py/runtime, API tests, strict static asset allowlist, authentication/data units, /api/quant.
2. Frontend: HTML/CSS/JS, focused views, accessible responsive high-DPI charts, real quant integration and design documentation.
3. Research: Pine/neural eight open contract defects, eliminate expected failures after verified fixes.
4. Integration auditor: read-only event/MCP/execution/supervisor audit.
5. Parent: quant_analytics.py + explicit offline tests, consolidated runner, read-only deployment/browser verification, review, operator documentation and delivery ledger.

## Quant contract
Unlevered closed H1 price returns: per-bar volatility, observed maximum drawdown, historical 95% loss quantile and expected shortfall with tail sample warnings; exact timestamp-aligned correlation. Not strategy returns, forecasts, edge certification or annualized Sharpe. Current stop-risk in account currency uses MT5 order_calc_profit and fails unknown on unavailable valuations. Stop risk is not guaranteed maximum loss (gaps/slippage). Missing data is null/unavailable, never zero-filled.

## Acceptance
- Explicit isolated test scripts only; never discover live test_loop.py.
- No xfail counted as a pass; total tests/counts collected programmatically.
- Real Node PineTS compiler and plots exercised with labelled synthetic bars; read-only MT5 bars exercised separately.
- Every named frontend control/view tested in desktop and mobile browser; API 401 unauthenticated, authenticated JSON; no token in source/storage/logs.
- Fresh spec review then quality review; no critical unresolved defects concealed.
- Machine-readable evidence report, focused operator guide, delivery ledger with limitations; Mem0 handoff.


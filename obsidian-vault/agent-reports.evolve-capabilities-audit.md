---
slug: agent-reports.evolve-capabilities-audit
type: note
graph: gitnexus
---

# EVOLVE capabilities and neural-readiness audit

**Snapshot:** `2026-10-19T06:23:05.791704+00:00` UTC.
**Verdict:** audit complete; the system is **not** verified as fully integrated, executable end-to-end, or ready for model promotion.

## Scope and evidence rules

- Repository root: `C:/Users/voidk/.hermes/workspace/luxalgo`.
- Application root: `C:/Users/voidk/.hermes/workspace/signal-relay`.
- Immediate child directories containing `.git` were enumerated and deduplicated: **11 repositories**. `luxalgo_manager.py` is a file, not another repository. The sibling `workspace/trade-relay` is reported separately.
- Source, package manifests, local artifacts and a bounded SQLite read transaction were inspected. The database was opened with `mode=ro` and `PRAGMA query_only=ON`.
- No execution modules were imported, and no broker, HTTP/MCP endpoint, live process inventory, service start/stop/restart, strategy run, model fit, order, source edit or configuration edit was performed.
- An isolated frontend function was exercised with explicitly synthetic numeric fixtures in a Node VM without `fetch`, `require`, `window` or `process`. Those fixtures are **not** presented as broker data.
- Only the requested JSON and Markdown reports were written. Package artifact presence and source wiring are reported separately from runtime execution.

## Repository inventory: installed is not integrated

For every row below, **functional package execution was not tested in this audit**. That is an unverified state, not a fabricated pass or a blanket runtime failure.

| Repository | Observed `dist` directories | Actual wiring / boundary |
|---|---|---|
| `edge-stats` | `packages/web` | Python Wilson-statistics equivalent + hosted MCP reports; no direct local-core consumption proved. |
| `luxalgo-mcp-server` | `root` | Built HTTP entry; manager/orchestrator wiring declared. No live service/tool calls checked. |
| `market-trackers` | `packages/cli`, `packages/core`, `packages/mcp` | Built source engine, but cockpit consumes separate dump files, not this ingestion engine. |
| `market-trackers-data` | None observed; see source/export caveats below | Five expected local JSON lists are present and directly read by the market-intel bridge. |
| `PineTS` | `root` | Direct CJS/Node bridge exists; native runner is dry-run. HTTP Pine is intentionally blocked. |
| `pinets-cli` | `root` | CLI artifact exists; HQ runtime uses a separate bridge, not this CLI. |
| `prop-firm-sim` | `packages/cli`, `packages/core`, `packages/mcp` | Core/directory imports are wired, but sample and explicit-firm gates prevent a demonstrated result. |
| `trade-journal` | None observed; see source/export caveats below | Compatible exporter exists. Current cockpit journal is an event journal, not journal-core. |
| `Vela` | `root` | Bundle exists and is allowlisted; current charts are custom canvas, not Vela. |
| `Vela-pinets` | `root` | Bundle exists and is allowlisted; no current plugin initialization found. |
| `whale-options` | `packages/cli`, `packages/core`, `packages/dashboard`, `packages/mcp` | Built packages exist; cockpit explicitly reports whale analysis unavailable. |

The JSON companion records exact local Git HEADs, manifest names/versions/license strings, dependency-directory presence, entry points, artifact checks, declared script names and per-repository evidence. A Git HEAD does not assert a clean worktree.

### Important distinctions

1. **Edge Stats has two different paths.** `edge_stats_bridge.py` implements Wilson statistics in Python and is consumed by `cockpit.edge_data()` (`cockpit.py:229,742-750`). That is not execution of the checked-out TypeScript engine. Separately, `luxalgo_orchestrator.py:132-163,202-212` calls MCP `edge_*` tools; the MCP server reads hosted precomputed reports (`luxalgo-mcp-server/src/tools/edge/tools.ts:1-21,89-109`). A BTCUSDT coverage/report response would not establish XAUUSD/EURUSD coverage. The local core exports TypeScript source (`edge-stats/packages/core/package.json:7-11`), so no `core/dist` is not, by itself, evidence of a broken engine.

2. **Market Trackers data is wired, but local ingestion is not proved.** `market_intel_bridge.py:10-41,44-83,89-115` directly reads the separate data checkout. The MCP tools have their own published-dump client (`luxalgo-mcp-server/src/tools/trackers/tools.ts:1-42`). Neither path proves that the local `market-trackers` collector is scheduled, currently updating or generating predictive trading signals.

3. **Journal export is not journal integration.** `journal_export.py:1-8,19-28,35-63` defines a compatible execution export; it was not run because it writes another output and can query MT5. The cockpit uses `event_journal.journal()` (`cockpit.py:235,273-284`), not the LuxAlgo round-trip engine. The journal package core exports TypeScript source (`trade-journal/packages/core/package.json:4-10`); absent `dist` alone is not a failure diagnosis. MCP `journal_*` tools instead access the authenticated user’s hosted LuxAlgo app journal (`luxalgo-mcp-server/src/tools/journal/tools.ts:1-16,42-45`).

4. **Whale Options remains unavailable to the cockpit.** Built CLI/core/dashboard/MCP directories exist, but no verified feed/collector/analysis-to-UI pipeline was found. `market_intel_bridge.py:99-115` explicitly returns unavailable whale analysis. The inspected general MCP module manifest does not register a whale-options module. No equities/options result may be relabeled as verified spot-gold whale flow.

5. **Prop simulation has real gates, not a demonstrated outcome.** `prop_sim_bridge.py:14-17,255-300` requires **10 validated closed trades** and an explicit supported firm/challenge selector. Only **6 total ledger rows** exist at the snapshot, and only **2 completed neural labels**; neither is a simulation result. The HTTP wrapper calls `get_prop_sim(n_paths=...)` without exposing a firm selector (`cockpit.py:613-624`; `cockpit_runtime.py:379,399-400`). Core `index.js` and directory `index.js` exist; they were not invoked.

## Current chart library and Pine execution

### The current frontend is not a Vela chart instance

- Active HTML script sources are `/assets/quant-client.js` and `/assets/quant.js`. The document has `overview-chart` and `chart` canvases (`cockpit_ui.html:11,14,17`).
- `quant.js:214-241` renders candles and plots using `canvas.getContext('2d', ...)`; no Vela import, instance or Vela-pinets initialization was found in this controller.
- `/vela/vela.global.js` and `/vela/vela-pinets.global.min.js` are authenticated static-asset allowlist entries (`cockpit_runtime.py:417-440`), and both local bundle files exist. An allowlisted bundle is not a loaded library.
- **Current defect reproduced offline:** extracting only `updateTelemetry()` and giving it valid-shaped synthetic candles raised **`ReferenceError: price is not defined`**. Its call is at `quant.js:24`; the formatter is declared only inside `drawChart()` at `quant.js:228`. `loadChart()` calls telemetry before its draw step (`quant.js:200-211`). The audit did not patch this defect or load the live cockpit.

### PineTS is source-wired; HTTP Pine remains intentionally unavailable

- Actual local path: `pine_runner.run_strategy()` → `pinets_runner.run_pine_strategy()` → `node pinets_bridge.js` → `luxalgo/PineTS/dist/pinets.min.cjs` (`pine_runner.py:138-171`; `pinets_runner.py:108-151`; `pinets_bridge.js:8-35`). The CJS file exists and bridge syntax parses, but no fresh Pine strategy/broker-data execution was performed.
- The registry has **3 enabled paper entries**, and `paper_mode` is true. `pine_runner.py:1-11` is dry-run by construction: there is no live-order path to enable merely by changing the paper flag. `pinets-cli` is not the consumer used by this bridge.
- Route source deliberately raises **503** for both `GET /api/pine_series` and `POST /api/pine/compile` until a credential-free OS-isolated worker is configured (`cockpit_runtime.py:346-351,383-398`). `quant.js:242` likewise reports unavailability. These are source findings, not HTTP requests performed by this audit.
- Preserve this boundary. Local-file selection or an in-process runner is not OS isolation, and installed open-source code does not grant protected TradingView/LuxAlgo strategy source access.

## Local public-data snapshot

All expected files parsed as JSON lists. These are **local file row counts**, not unique filings, live quotes or freshness guarantees.

| Path under `market-trackers-data` | Rows |
|---|---:|
| `congress/trades/latest.json` | 58 |
| `insider/transactions/latest.json` | 1413 |
| `contracts/awards/latest.json` | 9987 |
| `lobbying/filings/latest.json` | 225 |
| `short-volume/daily/latest.json` | 12213 |

No updater or source-publication freshness was tested. The trackers tools describe CC0 public-record data with primary-source receipts; record data is not a validated predictive signal.

## Neural training: collection exists; readiness and activation do not

### Database snapshot

| Measurement | Observed |
|---|---:|
| Recorded labels | 3 |
| Completed outcomes | 2 |
| Pending outcomes | 1 |
| Completed positive outcomes | 0 |
| Completed zero outcomes | 2 |
| Minimum completed samples | 300 |
| More completed outcomes needed to reach that count | 298 |

The completed outcomes are both losses under the collector’s binary labeling rule. Reaching 300 alone would not establish class diversity, holdout reliability or economic edge. Feature JSON objects are present; the recorded snapshots report `bars_used=80`. No model was trained or promoted.

### The claimed supervised auto-training trigger is absent

- The known watchdog declares `neural_label_collector.py` with `watch` (`C:/Users/voidk/.hermes/scripts/signal-relay-watchdog.py:113-124`). Its actual process liveness was intentionally not queried.
- `watch()` loops over `backfill_once()` and sleep (`neural_label_collector.py:608-626`). It does not call evaluation.
- The CLI `watch` branch returns before the threshold logic (`neural_label_collector.py:632-655`). A separate `status`/`backfill` invocation can call `run_evaluation()` once complete labels reach 300. That is not the supervised watch loop automatically retraining.
- AST scanning of root application Python, `scalp360`, and the known watchdog found the collector → bridge → evaluator chain but no watch-loop evaluation caller. Arbitrary external schedules and other launchers were not audited; this is a scoped negative finding, not a claim about every possible cron job.

### What the evaluator really implements

- `LogisticChallenger` is a small logistic-regression SGD classifier, not a deep neural network (`scalp360/neural.py:57-75`).
- Below 300 samples, `evaluate()` returns an insufficient-label rejection (`scalp360/neural.py:77-85`).
- It uses a chronological last-20% holdout and a validation tail for score-threshold selection (`scalp360/neural.py:87-98`). `purged_splits()` is defined/imported but is **not called** by `evaluate()`; claimed purge/embargo protection is therefore not in that execution path (`neural.py:45-55`; `scalp360_bridge.py:23,235-238`).
- `get_training_data()` returns fixed-layout feature vectors plus binary outcomes, not realized after-cost R (`neural_label_collector.py:391-443`). The evaluator scores unit wins/losses and defaults `cost_per_trade` to zero (`neural.py:79,99-106`); the bridge passes only `min_samples` (`scalp360_bridge.py:235-238`). This is not a validated after-cost trading evaluation.
- The hard-coded promotion condition is `AUC >= 0.58 AND model_net > baseline_net > 0`; `KEEP_SHADOW` starts at AUC 0.55 (`neural.py:104-106`). The configured `neural_holdout_auc_min` is not forwarded to the evaluator.
- `PROMOTE` is a report/event decision. The inspected evaluator/collector call chain does not serialize a champion, atomically activate it in execution, or implement a deployment/rollback switch (`neural.py:107-119`; `neural_label_collector.py:449-470`). An evaluation decision is not active trading intelligence.
- The UI correctly says readiness does not activate/promote a model (`quant.js:83-100`), and `/api/neural` is sample readiness/health reporting (`cockpit.py:381-390`).

## Service, authentication and licensing boundaries

- `luxalgo_manager.py` declares the local MCP HTTP service on 3333 and the separate sibling `trade-relay` on 8484. The relay CLI artifact exists, but neither service was queried or started here.
- The MCP `node-http` entry uses the **hosted** surface even when bound locally. Local-only broker modules are excluded (`luxalgo-mcp-server/src/entries/node-http.ts:14-28`; `src/entries/hosted.ts:1-10,22-26`). Do not assume the local URL exposes every stdio/local tool.
- Protected app tools require real user authorization; the app decides plan access, returning 401/403 where applicable (`src/auth/access-context.ts:2-18`). Open-source source code is not a subscription unlock.
- Observed manifest licenses include Vela **Apache-2.0**, PineTS and Vela-pinets **AGPL-3.0-only**, pinets-cli **AGPL-3.0-or-later**, and MIT for the listed supporting code packages. These copied labels are not a legal-compliance determination or proof of rights to third-party data/private scripts.
- Manager status labels a repository built if either `dist` **or just `package.json`** exists (`luxalgo_manager.py:111-127`). This can overstate runtime readiness and must not be used as an execution-test count.

## Minimal next safe changes — not performed

1. **chart-formatter-scope** (high): The real current frontend telemetry function throws price is not defined before chart load completes. Next: Repair formatter scope with finite-value handling and an isolated regression test, preserving approved appearance; this audit does not edit the frontend.

2. **chart-library-not-wired** (high): Vela and Vela-pinets artifacts are present but neither is loaded/initialized by the active frontend. Next: Decide whether to preserve custom canvas or intentionally integrate the real Vela library, then verify the chosen renderer in a separate authorized browser test.

3. **http-pine-isolation** (safety-boundary): Both HTTP Pine routes deliberately raise 503; source selection is not OS isolation. Next: Provide a credential-free, restricted worker with resource/network/filesystem boundaries before enabling HTTP code execution; retain 503 until then.

4. **learning-not-ready** (high): Only 2 completed outcomes (both losses), 1 pending and no evaluation trigger in the supervised watch loop. Next: Keep collecting validated real labels. Implement idempotent evaluation scheduling separately, with count/class/quality gates and no automatic trading promotion.

5. **evaluation-protocol-incomplete** (high): Purging/embargo are not used; after-cost score is binary proxy/default zero cost; PROMOTE is not model deployment. Next: Use event-time-aware purged validation, actual after-cost R, immutable evaluated artifacts and separate approval/activation/rollback controls before deployment.

6. **prop-sim-data-selector** (medium): At least 10 validated closed samples and an explicit firm selector are required; the entire ledger has only 6 rows and HTTP wrapper supplies no firm. Next: Expose explicit validated firm/challenge selection and wait for sufficient genuine outcomes; do not fabricate samples or relax rule gates.

7. **installed-not-executed** (medium): Local package checkouts, dist presence, source-based Python equivalents and MCP visibility are not end-to-end runtime evidence. Next: Create scoped per-capability offline execution checks, then separately authorized service/broker tests with exact provenance; do not count an absent runtime check as failure or success.

8. **protected-service-boundaries** (external): Hosted HTTP surface excludes local broker modules; app-backed protected tools require real authentication/plan authorization. Next: Use the legitimate matching MCP surface and authorized account. Never infer entitlement or bypass it from a public checkout.

## Verification and handoff

- **13 Python source files** parsed successfully with `ast.parse`; no application modules were imported.
- **3 JavaScript files** passed `node --check`: `pinets_bridge.js`, `cockpit_assets/quant.js`, and the actual loaded `cockpit_assets/quant-client.js`.
- **1 isolated frontend defect reproduced:** `updateTelemetry()` throws `price is not defined` when candles exist. Syntax success does not detect this lexical-scope failure.
- **0 functional package-runtime checks** and **0 live endpoint/broker checks** were performed. Installed/build/wiring evidence is not upgraded to a runtime pass.
- The JSON includes SHA-256 hashes of 15 inspected application source/asset files, exact call sites, repository metadata, artifact booleans, sample counts and all blockers. Counts were generated/checked programmatically, not inferred from directory names or previous claims.
- Recovery followed the supplied OpenCode `403 FreeTierError`, which describes a **network/IP policy restriction**, not established exhausted credits. No attempt was made to bypass it or re-dispatch to the same blocked free endpoint.

**Outputs:** `agent-reports/evolve-capabilities-audit.json` and `agent-reports/evolve-capabilities-audit.md` only. No trading or model deployment occurred. A downstream worker should read these as an evidence-backed audit, not as instructions to restart services, remove guardrails or activate a model.


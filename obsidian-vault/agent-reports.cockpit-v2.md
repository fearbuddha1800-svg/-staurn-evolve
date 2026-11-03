---
slug: agent-reports.cockpit-v2
type: note
graph: gitnexus
---

# Cockpit v2 — scalp360 Integration Metrics

**File:** `cockpit.py` (live dashboard, :8490) — additive change, no existing panel removed.
**Verified:** `py_compile` clean; `test_suite.py` **ALL PASS** (exit 0); in-process HTTP smoke test on scratch port 8497 exercised every endpoint (all 200 JSON).

## New panels (after the Event Journal, same dark card styling)

1. **Neural Readiness** — labels collected, min needed (300), progress bar (turns green when ready), and once ready: last evaluation AUC + decision badge (PROMOTE green / KEEP_SHADOW amber / REJECT red). Before readiness shows "collecting — N labels to go".
2. **Latency** — p50/p95/p99 (seconds) per pipeline stage in a table. Stages are recorded through the bridge's `StageTimer`: cockpit read-path stages (`ledger`, `inbox`, `journal`, `history`, `positions`, `trace`) plus the scalp360 endpoints themselves (`neural`, `lineage`, `pine`).
3. **Lineage** — last 5 intents from the `intents` table (intent_id, source, symbol, side, state with colored state badges) proving signal→intent→order→position.
4. **Pine Strategies** — registered strategies from `config.json` `pine_strategies` with enabled/disabled and paper/live badges.

Frontend polls via a new `tickScalp()` every 5s (`Promise.all` over the four endpoints, per-fetch try/catch so one failure never kills the tick). All API-sourced strings go through the existing `esc()` sanitizer, matching the file's documented innerHTML policy.

## New endpoints (all defensive: missing tables/files → empty, JSON responses)

| Endpoint | Source |
|---|---|
| `GET /api/neural` | `SELECT COUNT(*)` on `neural_labels` (live signals.db, read-only URI); min from `scalp360_bridge.BridgeConfig().neural_min_labels` (300); last eval probed from a `neural_eval` table then `neural_eval.json`, else null |
| `GET /api/latency` | `scalp360_bridge.latency_snapshot()` → `{stage: {n, p50, p95, p99, max}}` |
| `GET /api/lineage` | last 5 rows of `intents` ordered by `created_at DESC` |
| `GET /api/pine` | `config.json` `pine_strategies` (list-of-records and dict-map shapes both normalized) |

`/api/state` now also includes **`neural_labels`** (count) and **`pine_count`** (count).

## Key design decisions

- **Cockpit stays read-only for signals.db.** The bridge instance powering `latency_snapshot()` is built on an **in-memory** DB (`make_bridge(":memory:")` — same pattern the bridge's own `__main__` uses), so cockpit never writes schema/data to the live DB. All live-DB reads use `mode=ro` URI connections.
- **Bridge import is fully defensive** (`try/except` at module import); if the scalp360 package is ever missing, `_stage()` degrades to `contextlib.nullcontext()` and every new endpoint still serves (empty) JSON. `NEURAL_MIN_LABELS` falls back to 300.
- **Latency is real, not static:** existing read functions (`ledger`, `day_pl`, `inbox_data`, `journal_data`, the positions block in `state()`, and `trace` at its call site) now time themselves through the bridge StageTimer, so the panel populates from live traffic. Daemon-side stages will appear in its own process's snapshot when that wiring lands.
- **Parallel-build tolerance:** `neural_label_collector.py` and `integration_status.py` do not exist yet; neither does a `pine_strategies` config block or any scalp360 table in the live DB. Everything renders correct empty states today. `pine_strategies` accepts both plausible config shapes. `neural_eval_last()` probes two plausible persistence conventions — **when the collector lands, confirm where it persists eval results and align if needed**.

## Verification transcript (condensed)

- `python -m py_compile cockpit.py` → clean.
- Live DB (no scalp360 tables): `/api/neural` → `{"count":0,"min_needed":300,"ready":false,"progress":0.0,"last_eval":null}`; `/api/lineage` → `[]`; `/api/pine` → `[]`.
- Temp DB with 7 labels + 5 intents + eval row: count 7, progress 0.0233, `last_eval {auc: 0.612, decision: "KEEP_SHADOW"}`, 5 lineage rows newest-first.
- Temp configs: list-form, dict-form, missing block, missing file → all correct (`[]` when absent).
- Missing DB file entirely → all endpoints still return empty JSON (no crash).
- HTTP smoke: all endpoints 200; page contains Signal Inbox / Execution Lifecycle / Event Journal / Mobile / TRACE plus the 4 new panels; state carries `neural_labels`/`pine_count`.
- `test_suite.py` (miniconda python, the MT5 interpreter): 15/15 cases + news filter → **ALL PASS**, exit 0.

Note for operators: the running cockpit process serves the old code until restarted; restart is out of scope here (no running-service disruption was made).


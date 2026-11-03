---
slug: agent-reports.overhaul-integration-audit
type: note
graph: gitnexus
---

# Read-only integration and execution-safety audit

Audit snapshot: 2026-10-17T15:18:37Z. Repository: `C:/Users/voidk/.hermes/workspace/signal-relay`.

## Scope and evidence boundaries

Read current source, ARCHITECTURE.md, selected installed LuxAlgo source, configuration, and actual localhost MCP tools/list. No source/config changes, service lifecycle calls, broker calls, journal writes, or orders. Only this report is written. Offline tests use fake MT5 and isolated SQLite; bytecode and pytest cache writes disabled. No project-wide pytest discovery or test_loop.py execution.

Parent-provided runtime snapshot (not independently reverified): ports 8484/3333 up, 8490 down; HALT and MAINTENANCE present; watchdog paused; four demo positions with SL. An empty command-line process inventory is **not** evidence that engines are down. This audit does not authorize removing holds or restarting anything.

**Outcome:** cross-process intelligence consumption has real passing regressions and honest unknown alpha fields. The execution authorities still lack several invariant checks and atomic admission. Supervisor duplicate suppression remains unsafe for empty process command lines. Installed repositories and tools are not proof of strategy validity or usable local analytics.

## Verified tests and probes

Executed exactly:

```bash
PYTHONPATH= PYTHONDONTWRITEBYTECODE=1 C:/Users/voidk/miniconda3/python.exe -m pytest -q -p no:cacheprovider test_intelligence_integration.py test_watchdog_recovery.py
```

Result: **34 passed in 1.73s**, exit 0. Covers second-process publish/recovery, exact-symbol isolation, expiry, future/bad timestamps, evidence thresholds, unavailable recovery, existing HALT, supervisor hold files, config parsing, supervisor OS single-flight lock, exact checkout identity, syntax checks and environment stripping. These passes do not establish the missing invariants below.

`test_luxalgo_orchestrator.py` is absent; a recursive non-backup search found no copy. Consequently no orchestrator unit suite was run under that name.

Read-only MCP SDK initialize + tools/list against `http://localhost:3333/mcp`, HTTP/SSE/session deadlines 5 seconds, enclosing subprocess bound 30 seconds: **42 tools** returned, exit 0. No tools/call was sent. Data retrieval/authenticated journal operations remain untested.

Additional AST-only harnesses executed the real selected function bodies without importing live executor/event_bus or touching broker/database files. Fake `order_send` was not needed: dry_run stopped before sends. Results:

- `execute_algo(... lot=.01, sl=None, tp=0, dry_run=True)` with `risk.require_sl=true`: `dry_run_ok`.
- `execute_algo(... lot=1.0, sl=1900, dry_run=True)` with `risk.max_lot_per_trade=.1`: `dry_run_ok`, returned lot `1.0`.
- `execute_algo(... valid stops, account_info() -> None, dry_run=True)`: `dry_run_ok`.
- Real `_guards` separately evaluated with account None, lot 1.0, max-lot .1, otherwise normal fake broker/empty ledger: `(True, '')`.
- Two real `_guards` evaluations for the same key before a ledger insert with daily cap 1: `[(True, ''), (True, '')]`. Demonstrates the admission TOCTOU, not actual duplicate orders.
- Watchdog `_running('daemon.py')` with one alive-looking Python process record whose `cmdline=[]`: `False` rather than unknown/refuse.

## Priority defects

### P1 — Mandatory SL and lot cap are not execution-authority invariants

**Locations:** executor.py:141-146, 160-192, 195-231, 324-325, 355-359, 410-505; config.json:27-35.

`_guards` accepts `lot` but never uses it. `_norm_volume` clamps to broker min/max, not configured cap, and rounds to nearest step. `execute()` checks require_sl, but `execute_algo()` does not: `_validate_stops` explicitly permits `sl=None`, then the request writes `sl or 0.0`. Explicit `execute(... lot=...)` also bypasses `_compute_lot`'s configured cap. Algo callers currently compute stops/cap themselves, but that is not a safe single entry authority for future callers or malformed values. Min-lot clamp/round-up can exceed a risk budget.

**Reproduction:** dry-run and actual `_guards` AST harness outputs above. All were isolated; no orders.

**Fix:** enforce finite positive lot, risk cap, mandatory finite protective SL, valid side and broker geometry centrally for both APIs; floor to step and reject below-min sizing rather than clamp up. Do not rely on caller sizing. Regression matrix: None/0/NaN/inf SL; negative/zero/NaN lot; explicit lot over cap; fractional step; min-lot exceeding risk. Assert no `order_send` on rejection. Current HALT is a separate mitigation, not a fix.

### P1 — Netting/unknown broker-state protection is incomplete and fail-open

**Locations:** executor.py:195-231, 282-386, 455-472.

Telegram `execute()` has no netting-merge guard. Algo guard says fail-closed but `if acct and ...` silently permits `account_info() is None`, and `(positions_get() or [])` treats an API failure as confirmed-empty on netting accounts. `_guards` skips free-margin enforcement when acct is None. An entry can therefore merge an existing netting position or be approved with unknown account state.

**Reproduction:** real `_guards` and execute_algo dry-run with account None approve as above; code inspection establishes missing Telegram branch and None-to-empty conversion.

**Fix:** one shared account-mode/positions snapshot guard for both entry origins. Reject unknown account/mode/position inventory. Distinguish empty tuple from None. Test each branch plus hedging/no-merge behavior. Do not confuse demo status with hedging mode.

### P1 — Shared functions do not provide atomic cross-process entry admission

**Locations:** executor.py:207-231, 325, 386-399, 450, 505-520, 593-604.

Dedupe and daily count are read checks, connection closes before send, and ledger insertion happens after broker response. There is no unique msg_id constraint, transactional reservation, or shared admission lock. Independently running daemon/strategy/strategy2 can all pass capacity/daily checks, then send. Duplicate daemon instances can both pass msg_id dedupe. A crash after fill/before record leaves no durable submitted/unknown claim in this authority; scalp360 lineage exists but these send paths do not consult it.

**Reproduction:** two real guard calls before insert both approve the same key with daily cap 1. This is a deterministic representation of the schedule, not a claim that a duplicate fill occurred.

**Fix:** durable unique intent reservation in `BEGIN IMMEDIATE` plus cross-process aggregate risk/cap reservation, explicit submitted/unknown state, and reconciliation before retry. Release only confirmed rejected reservations. Test two subprocesses racing the same and different keys, max-open/daily capacity, and crash windows with fake broker. Protective exits must remain independent.

### P1 — Empty command-line inventory defeats watchdog duplicate prevention; engine PID files are not locks

**Locations:** external `.hermes/scripts/signal-relay-watchdog.py`:41-66, 111-117; daemon.py:115-147, manage.py:73-105. Related legacy engine helpers should be migrated consistently.

Supervisor handles raised AccessDenied as uncertainty, but `info['cmdline']` being None/[] simply yields no arguments and eventually `False`, authorizing spawn. This is especially relevant given the parent's empty inventory. Child daemon/manage helpers likewise return `bool(cl) and script_marker in cl`: a live Python with empty successful CIM stdout is considered stale. `_acquire_single_instance` is read-then-overwrite PID text, not an OS-held exclusion lock; two starts can both pass and overwrite each other. Unconditional release can then delete another instance's PID file.

Supervisor's OS lock correctly serializes watchdog ticks, but does not cover an already-running engine or unrelated Startup/manual starter.

**Reproduction:** mocked alive Python + empty cmdline -> watchdog False; code inspection of engine lock acquisition. Existing tests cover similar basenames/other checkouts, not empty/inaccessible identity or competing engine starts.

**Fix:** OS-held per-engine lock (or named mutex), held for engine lifetime; PID metadata is diagnostic only. For detection, unknown command identity must stay unknown, not down; corroborate verified locks. Add empty/None cmdline, AccessDenied during iterator prefetch, PID reuse, simultaneous launch and lock-release ownership tests. Do not restart merely to reproduce.

### P2 — Rollback switches can bypass shared HALT/risk/intelligence authority

**Locations:** strategy.py:247-250, 279-301; strategy2_live.py:409-435; config.json:74,83.

Both active configs currently set `algo_entry_authority=true` (good). Setting a rollback flag false re-enables direct exposure-increasing `order_send`. Strategy.py's direct path has only local algo/day/STOP checks, not the shared HALT/daily/global/symbol/news/intelligence checks. Rollback should select implementation, never remove safety invariants.

**Fix:** remove exposure-increasing legacy sends or put immutable central safety validation/reservation around all send implementations. Add a test with flag false + HALT and assert zero sends. Scope PAUSE explicitly: `_guards` checks HALT only; a daemon DM pause is not a universal pause of every entry origin. `paper_mode=true` is Pine documentation, not a global broker kill switch.

### P2 — Local market-intelligence cache never refreshes or declares source age

**Locations:** market_intel_bridge.py:39-55, 74-115; cockpit.py:531-536.

Unbounded lru_cache caches both loaded lists and None forever per kind. Updating a daily JSON dump does not refresh an existing cockpit process; a first missing-file request remains unavailable even after data installation. Successful responses report `available=true` without ingestion time, file age, TTL, or stale status.

**Reproduction:** call `_load_data(kind)` once, replace/create its source file, call again: cached object/None remains. This follows the functools cache contract; no production files were modified to demonstrate it.

**Fix:** cache on mtime/content identity or short TTL, include source/lastIngestedAt/observed_at/stale and errors separately, and test initially-missing then installed and successful-file refresh. Public filings are historical records, not a live regime signal.

### P2 — Orchestrator overall availability can stay green on a cached catalog during outage

**Locations:** luxalgo_orchestrator.py:146-160, 162-198.

Discovery caches successful catalogs for an hour; overall `status['available'] = bool(self.catalog)` means catalog availability, not current connection or selected data success. If MCP dies after discovery, selected report calls can be unavailable while engine status still says available. Tracker status includes last_ingested_at but no age assessment; catalog's per-dataset stale flag and edge report builtAt are not elevated into status freshness. Observed-at is poll time, not source freshness.

**Fix:** separate transport_connected, catalog_cached_at/age, selected-feed availability, source builtAt/lastIngestedAt and stale status. Keep raw provenance/report. Test cache-hit + disconnected adapter, stale upstream data with a successful transport, and missing explicit selection. This defect does not imply stale data can currently trigger decay: alpha_decay remains None.

### P2 — Repo/build and full-local-MCP status are overclaimed

**Locations:** luxalgo/luxalgo_manager.py:48-53, 57-68, 105-117, 121-130; luxalgo-mcp-server/src/entries/node-http.ts:18-23; src/entries/hosted.ts:1-5,22-26.

Manager `built` is true if either root dist exists **or package.json exists**. A source checkout is marked built. The launched node-http entry explicitly constructs a **hosted** server, excluding local broker tools, despite manager description calling :3333 the full local ecosystem. Actual tools/list returned 42 tools and **zero broker_* tools**. The separate Hermes stdio local integration may expose brokers, but that is a distinct surface; it was not called here.

Manager mcp-test probes the hosted internet endpoint, not the local SDK contract, and considers any HTTPError reachable (even errors not indicating healthy MCP). TCP-open checks establish listener presence only. Manager start also has a check-then-spawn race across independent callers and does not verify process identity/readiness; watchdog single-flight does not cover all manager invocations.

**Fix:** report present/install/build/runtime/tool-capability separately using real entry artifacts and SDK discovery; describe HTTP hosted-like vs stdio local accurately. Use service OS locks and bounded readiness handshake. Do not change HTTP exposure to add brokers without an explicit security review.

### P2 — Local Edge Stats bridge is not a trustworthy realized-R/channel scoring source

**Locations:** edge_stats_bridge.py:188-217, 226-246; daemon.py:623-628; event_bus.py:117-123.

Bridge joins trade msg_id against events.event_id. Current publishers use UUID event_id and chat:message trace_id, so this generally drops channel attribution. Even if a row matches, `_compute_r_multiple` divides account-currency P&L by price distance, omitting lot and tick value/size, and uses `history_deals_get(ticket=order_ticket)` as though it were a position's full close history. This is not dimensionless realized R and can miss closes. The file calls itself LuxAlgo-style; it is a Python implementation, not proof that the local LuxAlgo engine is executing.

**Fix:** use durable source/trace/intent/ticket lineage, filled entry and immutable original money-at-risk, full position closing deals including all costs/partial exits, and closed-only outcome samples. Test different lots/tick specs and order/deal/position IDs. Do not use current stats for channel promotion, alpha decay or auto-risk adjustment.

### P2 — Prop simulator bridge cannot consume actual local closed outcomes

**Locations:** prop_sim_bridge.py:59-119 (especially 94-116), 27-35.

`_get_r_multiples_from_db()` always continues and never appends any R, even with executed/closed ledger rows. Thus local-data simulation is permanently insufficient, not simply waiting for ten trades. Built simulator packages/tool exposure do not establish this bridge works. `_fetch_prop_firm_list` also lacks a network timeout if this path becomes reachable.

**Fix:** first implement a reconciled closed-trade R ledger, then drive the real simulator with its current contract, bounded network/process calls and fixture schemas. Preserve honest insufficient-data responses until then; do not fabricate trader profiles.

### P2 — Event publication is best-effort, not durable or idempotent delivery

**Locations:** event_bus.py:125-151, 176-211; executor.py:579-590.

Memory is appended before persistence; `_persist` swallows failure; caller receives event_id and callbacks run even if no durable row exists. Other processes cannot see the memory-only event. `INSERT OR REPLACE` also permits same-event-id overwrites and re-fires callbacks on repeat publish. Thus the bus is not an exactly-once order/audit queue. With intelligence_history ordering by rowid, replacing an older same-ID event can make it the latest arrival again within TTL; broker/control provenance must not rely on unprotected writer-supplied source strings.

**Fix:** document telemetry semantics, return/emit durable-write outcome, preserve immutable event IDs, and use a durable order outbox/intents for safety-critical transitions. Add locked/read-only DB and repeated event-id tests. Retain the dedicated read-only intelligence path's no-memory-fallback behavior.

## Confirmed positive integration properties

- `event_bus.intelligence_history` (153-174) reads SQLite cross-process, matches exact symbol plus orchestrator source/type, bounds results to 64 and read timeout to .25 seconds, orders by arrival rowid, and returns [] on read errors instead of stale memory. Executor re-reads it at each guard, not process-local subscriptions.
- Executor intelligence filter (33-75) requires fresh envelope **and** observed_at within 300 seconds, real booleans, finite numeric evidence, sample/reference >=30, after-cost baseline positive/current negative, confidence >=.95, nonblank method/source. Latest per preset supersedes prior state, including unavailable/recovery. Unknown, stale and informational data do not create new blocks. This is an optional advisory blocker, not an availability fail-closed gate.
- Current orchestrator uses SDK Streamable HTTP `/mcp`, discovered names, correct `edge_report {symbol,preset}`, `trackers_latest {dataset,limit}`, result isError handling, bounded response size, timeouts and capped reconnect backoff. Its OS-held singleton is better than legacy PID files.
- Current orchestration does **not** invent alpha decay: `edge_data.alpha_decay=None`. Regime explicitly unavailable because public-record counts are not a validated model. Whale/options explicitly unavailable because no market-wide options-flow tool exists on this surface. These unknowns are legitimate, not missing implementations to fill with a heuristic.
- MCP edge source explicitly serves historical conditional frequencies, with builtAt/N/Wilson/stability caveats (edge/tools.ts:1-16,132). Tracker source explicitly says public records with provenance, no scores/predictions (trackers/tools.ts:1-11). Neither validates a trading strategy.
- Pine runner is dry-run by construction: pine_runner.py:7-11 never imports executor and never sends. Its config flags do not arm live trading.

## Actual installed integrations versus claims

Filesystem inventory confirmed all eleven named LuxAlgo repository directories. Root dist exists for PineTS, pinets-cli, Vela, Vela-pinets and luxalgo-mcp-server. No root dist for edge-stats, trade-journal, prop-firm-sim, whale-options, market-trackers or market-trackers-data; lack of root dist is **not** proof monorepo packages are unbuilt. Specifically prop-firm-sim packages/core/dist/index.js and packages/cli/dist/index.js both exist; edge-stats packages/core/dist/index.js does not. package.json presence is not a build test.

All five market_intel_bridge local latest.json paths exist (congress trades, insider transactions, contracts awards, lobbying filings, short-volume daily). Their freshness/content integrity was not attested by file existence.

Actual :3333 tool families: Library (9), propfirms (12), trackers (4), edge (3), account (1), journal (13): 42 total, no broker family. Tool availability is verified; actual upstream edge/trackers data retrieval and authenticated journal availability were not exercised. Installed whale-options repo is not an options-flow MCP capability. Installed Vela/PineTS is not proof of profitable strategies. Local prop/edge bridge limitations above remain independent of successful MCP discovery.

## order_send inventory classification (current non-backup code)

- executor.py:386 signal entry; :505 algo entry.
- strategy.py:301 and strategy2_live.py:435 legacy exposure-increasing entries behind currently-true authority flags.
- daemon.py:417 owner-authorized close; executor.py:535 close; executor.py:571 BE SLTP; manage.py:150 protective SLTP. These are not entry-authority violations by themselves.
- test_loop.py:97,:383 contain broker-order paths; **not run**.

## Recommended remediation order and acceptance

1. Keep existing holds. Fix central finite-value/SL/lot/account-state invariants; add fake-broker negative tests.
2. Add atomic durable admission/reconciliation; remove guard-bypassing rollback sends. Exercise races/crash windows offline.
3. Replace engine PID exclusion with lifetime OS locks; test unknown identity and multiple launch sources before supervisor resume.
4. Correct capability/build/freshness reporting and local analytics lineage; keep unsupported alpha fields unknown.
5. Add the missing orchestrator contract suite using injected adapters plus an explicit bounded localhost SDK smoke test. Extend market cache and analytics tests; no broad project pytest because unsafe broker tests coexist.

No live execution, fill/exit lifecycle, restart recovery on real engines, profitable edge, market-wide whale model, or validated decay model is claimed by this audit. Full report is the only created file.


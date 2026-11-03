---
slug: agent-reports.recovery-acceptance
type: note
graph: gitnexus
---

# Recovery scope and acceptance gates

Source: direct request to continue failed-agent deliverables and overhaul the signal-relay system with GPT-6.1-sol. Existing behavior/risk policy is preserved; this is not permission to increase exposure or sell a service.

## Current failure evidence
- cockpit.py: raw legacy HTML embedded after state() causes Python SyntaxError.
- daemon.log: executor subscribes to bus before defining/importing it, causing NameError.
- Multiple old dashboard/intelligence processes existed. Only those stale services were stopped; protective management was retained.
- Public frontend/server contained the same hardcoded credential; this is not meaningful authentication.
- LuxAlgo orchestrator contains placeholder inference and invalid data assumptions; event types and cross-process transport were incomplete.

## Gates
1. Source-preserving backups with SHA-256 manifest (created before edits).
2. Authenticated GPT-6.1-sol/openai-codex workers, disjoint ownership.
3. HALT and watchdog pause during changes; MAINTENANCE prevents accidental restarts.
4. Backend preserves all named routes and correct types/errors; compiler uses real PineTS, no broker writes.
5. Frontend has focused views, working controls, real data/empty/stale/error states, desktop/mobile proof.
6. Events persist and intelligence is visible cross-process; no fabricated regime/whale/alpha claims.
7. Existing isolated regression scripts plus new tests pass; offline lifecycle harness reports zero network/orders.
8. Parent reads exact targets after deploying services, verifies no duplicates, resumes previous operations only after gates.
9. Delivery ledger enumerates recovered historical failures and explicit remaining limits; no commercial-readiness/profit claims.

## Ownership
- Backend worker: cockpit.py, optional cockpit helper modules, API tests.
- Frontend worker: cockpit_ui.html, cockpit_assets, design documentation.
- Intelligence worker: executor import, event bus, typed LuxAlgo status flow, orchestrator tests.
- Research worker: historical failure inventory, Pine/neural gap audit, research contracts.
- Parent: supervisor, test runner, final review, deployment/lifecycle, live read-only/browser verification, operator docs.

## Explicit non-goals
No public deployment, new broker account, live test orders, risk increases, customer onboarding/billing or unsandboxed remote Pine execution. ML promotion requires adequate prospectively collected evidence. Subscription authentication is not exported into the trading bot.


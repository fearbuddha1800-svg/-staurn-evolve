---
slug: docs.DEVELOPER_GUIDE
type: note
graph: gitnexus
---

# Developer guide

## Local workflow
Start with ARCHITECTURE.md, ARCHITECTURE_PACKAGING.md, DELIVERY_LEDGER.md and REMAINING_BLOCKERS.md. Inspect current code rather than trusting historical line numbers. Use a feature branch and an isolated config/database with dummy credentials; do not run daemon, strategy, manager, watchdog or arbitrary pytest integration modules on a production account. Pin the interpreter (`python3` and `pip` may target different installations); use `python -m pip` or an explicit uv interpreter. Inspect each test's setup and entry point before running it. Syntax-check changed files without importing trading modules. Existing boundary tests use isolated HTTP fixtures; run them explicitly. No migration or replay against the live ledger during development.

## Adding strategies
`strategy.py` / `strategy2_live.py` produce algorithmic candidates; `executor.py` owns entry execution and durable loss/entry guards. Preserve existing account identity, symbol resolution, data freshness, 2-ATR/no-TP authority contracts and idempotency. Inspect `test_evolve_entry_contract.py`, `test_redevelop_backend.py`, and current executor signatures before changing call sites. Do not send orders directly from a strategy or UI. Emit traceable intent/event identifiers and distinguish proposed, attempted, executed, rejected and broker-confirmed states.

For dry research Pine, add a trusted `.pine` file under strategies and a disabled-by-default config record:
```json
{"pine_strategies":[{"name":"example","enabled":false,"paper":true,"path":"strategies/example.pine","symbol":"XAUUSD","timeframe":"H1"}]}
```
Merge the record into an isolated config; do not replace the production config with this fragment. `pine_runner.py` accepts list/map records, normalizes defaults, and records `pine_signal` rows only. It never imports executor; paper=false does not create a live execution path. Test with saved candles, deterministic expected signals, warmup, stale/missing data and no broker-order calls. A live adapter needs a separately reviewed intent-to-executor integration, not a boolean flip.

## Extending PineTS
The Python `pinets_runner.py` strategy helper calls `pinets_bridge.js`; series research uses `pine_series_bridge.js`. Node must resolve the installed PineTS dependency in the intended workspace. Add a small deterministic saved-bar fixture for every supported language feature, explicit closed-bar indexing and expected plot/signal output. Test unsupported syntax, missing dependency, invalid/empty JSON, nonfinite series, long-running code, timeout and child cleanup. Preserve bounded source/bars/runtime/concurrency. Do not silently fall back to fake plots, zero prices or an unrelated transpilation result.

HTTP `/api/pine_series` and `/api/pine/compile` intentionally return 503. A subprocess inheriting environment/filesystem is NOT a sandbox. Enabling HTTP execution requires an OS-isolated, credential-free worker, resource limits, cancellation and adversarial tests; never wire the existing broker-capable offline helpers directly to HTTP. Validate Windows subprocess semantics and process-tree cleanup explicitly.

## Custom guards
Inspect `loss_halt.py`, `stop_legality.py`, current executor entry calls, and manager modification path. Return structured deny/allow decisions with reason/evidence; fail closed on missing identity, stale quotes or unavailable risk inputs. Avoid mutable process-global business state; durable latches require atomic persistence and tested restart behavior. Apply guards before all affected broker sends, not just one strategy. Entry guards and stop-modification legality solve different problems: do not disable existing-position risk management just because entries are paused.

Required tests: exact-boundary values; missing/stale data; reconnect/account mismatch; repeat call/idempotency; persisted latch after restart; denied path makes zero order_send calls; both buy/sell stop legality and tighten-only rules. Use test_loss_halt.py and test_stop_legality.py patterns with fake brokers. Historical ledger notes are not proof of current coverage. Document explicit fallback behavior, especially legacy algo authority modes; never widen authority implicitly.

## MCP server development
Adjacent LuxAlgo and trade-relay services have their own ownership/lifecycle. Inspect their current schemas and launch configuration; do not invent ports, tool names or credentials. For a new read-only Python service, a minimal FastMCP skeleton is:
```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("relay-observation")
@mcp.tool()
def status() -> dict:
    """Return an isolated read-only health snapshot, never broker credentials."""
    return {"available": False, "reason": "adapter not configured"}
if __name__ == "__main__":
    mcp.run(transport="stdio")
```
This is an illustrative scaffold, not an installed or operational server. Pin the SDK version and implement a read-only adapter with explicit schemas, bounds, timeouts, provenance and availability semantics before registering. Keep stdout for protocol traffic and log to stderr. Do not expose token/session files or broker attachment/reset actions. Mutation tools, if ever required, need separate authorization, account allowlists, idempotency and audited confirmation; never smuggle them through a generic 'status' tool. Test with an MCP client in an isolated process; malformed arguments, denied scope and unavailable provider must be tested without a real order endpoint. Registration/configuration is profile-specific and must not alter another Hermes profile.

## Contract maintenance
Change dispatch + docs/openapi.json + isolated API tests together. Run `python docs/validate_docs.py`. Keep spec exact about 404 aliases, fail-closed Pine 503, finite SSE and HTTP-200 unavailable payloads. Backend snapshots are extensible; add stable schemas only when grounded in code and fixtures. Link new procedures and diagram changes from docs/README.md. Never publish production data or raw token responses as examples.


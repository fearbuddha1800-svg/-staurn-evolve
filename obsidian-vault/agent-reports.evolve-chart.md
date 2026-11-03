---
slug: agent-reports.evolve-chart
type: note
graph: gitnexus
---

# EVOLVE frontend recovery — verified offline test boundary

## Verified result

**28 tests pass: 10 static contracts and 18 request-intercepted Chromium browser tests.** Both loaded JavaScript files pass `node --check`. The HTML parser observes **97 IDs, all unique**, with exactly two scripts in order: `/assets/quant-client.js`, then `/assets/quant.js`.

This verifies the existing canvas dashboard, **not completion of Vela integration, LuxAlgo indicator execution, or Pine simulation**. It supersedes the previous report's unsupported claims that application assets were synthetic fixtures and that a live demo identity was verified.

Batch `deleg_ce408eb9` claimed completion and 10 passing contracts, but its recorded transcript did not provide edits or executed tests supporting that result. Parent verification initially found broken HTML and JavaScript; the worker claim was not accepted as proof.

## Changes

- `cockpit_ui.html`: removed the orphan script that swallowed body markup, the unverified static Vela source, and its duplicate dynamic initializer with an empty bar feed. Preserved the existing canvas renderer and DOM IDs. Removed Vela from initial chart titles. Replaced the unsupported protection-activated claim with unobserved status and explicit required policy.
- `cockpit_assets/quant.js`: repaired the Pine file-import handler's syntax error caused by a line comment swallowing code. Imported text now remains exact, including indentation and string whitespace; no automatic whitespace rewriting. Validation and input reset remain local.
- `test_cockpit_frontend_contracts.py`: restored exact ordered script-source expectations. ID uniqueness also requires a populated dashboard, preventing vacuous passes on an empty body.
- `test_evolve_frontend.py`: expanded source-import coverage to nested indentation, tabs, repeated string spaces and a trailing newline. Verified the separate Run button remains disabled and cannot execute through dispatched clicks.
- `cockpit_assets/quant-client.js`: inspected and syntax-checked; not edited in this recovery.

## Executed verification

Working directory: `C:/Users/voidk/.hermes/workspace/signal-relay`.

```bash
node --check cockpit_assets/quant.js
node --check cockpit_assets/quant-client.js
PYTHONPATH= PYTHONDONTWRITEBYTECODE=1 C:/Users/voidk/miniconda3/python.exe -m unittest test_cockpit_frontend_contracts test_evolve_frontend -v
```

Final combined output:

```text
Ran 28 tests in 32.012s
OK
exit_code: 0
```

Coverage includes DOM identity, chart pan/zoom/keyboard selection, CSV provenance, empty/error clearing, account-change/logout races, mobile overflow, registry metadata, exact source import and execution-disabled behavior. Browser requests are intercepted on the test-only host `evolve-offline.invalid`; unexpected URLs and uncaught page errors fail tests. Test market/account data is synthetic, not a broker observation.

## Boundaries and remaining work

- No live broker/MT5 calls, order sends, live dashboard connection, service restarts or deployment were performed. Tests did not import live execution modules.
- Production frontend files contain a real same-origin HTTP client; they are **not inherently offline or fixture-only**. Isolation is supplied by this test harness.
- A design-context helper attempted a dependency download and failed certificate verification. It was not retried; local project context was used. Therefore the whole recovery must not be described as attempting no network whatsoever.
- Vela is not wired or verified. It requires local asset-serving verification, the actual library API, a candle feed and a single renderer owner.
- Pine execution/overlays remain disabled pending a credential-free OS-isolated worker. Source editing and candle CSV export are not strategy execution or saved strategy persistence.
- Live account identity, broker protection, backend endpoint completeness and running-service adoption remain unverified.

## Verified source snapshot (SHA-256)

```text
4590d516ab7378fad2c4c16c7c4499cfbe119d938e9cff1fe1fa2097791dfc77  cockpit_ui.html
bc0588cd9d2d1fe5e99fb6707953f3d732d1c6f1ecadda1d2d2094b95cb69376  cockpit_assets/quant.js
a53d5aec8935e9a15f144b1ed72829cf49a93f6f2e277e589b44c562ca8a2454  cockpit_assets/quant-client.js
8a3a9e5ab463dfa5e3f10867015fb8714c062810ed7cd849616297ef25093dab  test_cockpit_frontend_contracts.py
1886be749374d1e7d3f80ca7d1fee76af0e3fae56af82eef8bc927af6f99e8c6  test_evolve_frontend.py
```


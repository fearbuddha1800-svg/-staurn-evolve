---
slug: agent-reports.matrix-panels-verification
type: note
graph: gitnexus
---

# Matrix research panels verification

Implemented six read-only panels in cockpit_assets/matrix-panels.js with matrix-panels.css, HTML host/script integration and cockpit_runtime.py asset allowlist additions. Existing quant.js and quant-client.js were not edited by this task. Panel preferences persist visibility, order and config without storing API payloads.

Verified with Node syntax check and Python py_compile. In a real browser at localhost:8490, injected the new module into the live HTML (asset route was still 404 in the already-running process). Six panel cards rendered, HQMatrix.registerPanel existed, collapse persisted across navigation, and foreground polling returned real results: LuxAlgo, Edge and Market Intel observed successfully; Prop Firm Sim reported observational-mode disablement; Neural Health returned Route not found; PineTS reported isolated worker unavailable. These errors were displayed rather than replaced with fabricated results.

Deployment caveat: the existing process serves updated HTML but does not yet know newly allowlisted asset paths. An approved cockpit process restart is needed before normal script/style loading works. No trading service was restarted. Browser injection verifies rendering and live responses, not normal asset deployment. An attempted isolated verification HTTP server exited with a Python quoting syntax error and did not remain running.


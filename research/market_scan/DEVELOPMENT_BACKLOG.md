# Research-driven development backlog

Status: proposed acceptance gates, not completed features. Preserve the active
Pine-parity task; do not spawn overlapping owners or deploy this proposal.

| Priority / task | Scope and candidate integration point | Acceptance before promotion |
| --- | --- | --- |
| P0 / native-compile | Current EA and its actual include closure | Real MetaEditor version/log, zero errors, explained warnings and EX5/source hashes; local terminal access is still required |
| P0 / pine-parity | Inspect existing bar_parity.py, Pine runners and tests with GitNexus first | Identical fixtures, explicit supported constructs, confirmation/availability timestamps and no future dependence; an independent Pine oracle is required before claiming cross-runtime parity |
| P0 / risk-invariants | Inspect portfolio_risk.py, stop_legality.py, loss_halt.py and broker lifecycle before editing | Zero oversized lots, stop-distance violations or duplicate intents across deterministic rejection, partial-fill, timeout and restart cases |
| P0 / feed-health | Inspect cockpit_runtime.py and current read-only frontend before integrating design | Missing, stale, disconnected and query-error states remain distinct; last-observed timestamp visible; unknown balances/exposure never become zero |
| P1 / signal-lineage | Inspect signal_provenance.py, parser/ingestion and event contracts | Every accepted/rejected signal has stable source identity, parser version, TTL/reason; duplicate/reordered/edited messages cannot create duplicate executable intents |
| P1 / model-manifest | Replace any fixed-output or heuristic AI claim only after review | Versioned real model, chronological data splits, feature schema, held-out predictions/calibration, source-runtime→ONNX parity and fail-closed corrupt/missing artifact tests |
| P1 / workstation-ui | Adapt research/market_scan/design as a proposal, reuse current stack | Real API contract; clear current vs last-known states; keyboard/mobile checks; no broker actions added implicitly; no synthetic fixture data shown as live |
| P1 / research-refresh | collector.py and source catalog | Small explicit URL batches, robots outcomes, hash/date, no protected-code copying, claims kept distinct from facts; retain collection failures |
| P2 / market-package | Standalone native product and optional companion relationship | Applicable current Market rules reviewed; deployment dependencies disclosed; evidence for every commercial claim; no release inferred from unit tests |

Each task needs exact file leases, impact callers/processes/risk, a test plan and
independent review before integration. Candidate filenames are starting points,
not blanket edit authorization or proof their existing implementations satisfy
these requirements. Existing runtime was not modified by this research task.

The six-system engineering findings specify quantitative fixture proposals for
Pine conversion, model parity, ingestion and reconciliation. Freeze those thresholds
before evaluation; revise them with recorded reasons rather than tune to a desired
result. Do not treat an arbitrary case count as statistical proof of trading edge.

Suggested next slice: complete a closed-bar Pine reference fixture and its expected
decisions, then attach source-age/rejection details to the existing read-only UI.
Native MT5 execution stays blocked until its separate prerequisites are met.

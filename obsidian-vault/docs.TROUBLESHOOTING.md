---
slug: docs.TROUBLESHOOTING
type: note
graph: gitnexus
---

# Troubleshooting

## First response
Hold new entries; preserve open-position supervision. Collect redacted UTC timestamp, component, exact exception/retcode/comment, last_error, broker identity and data age, flags, trace/ticket and nearby event evidence. `python hq.py status` is observational; watchdog/start/restart are not. Never repeatedly send an order to diagnose a failure. Roll back code/config changes before widening permissions. Escalate unknown broker outcomes for reconciliation.

## MT5 retcodes and connection failures
Confirm the installed MetaTrader5 constants and broker result comment; do not treat this reference as an exhaustive broker-specific mapping.

|Retcode|Typical meaning|Safe response|
|---|---|---|
|10009|DONE|Reconcile ticket/fills; not every request type uses identical completion semantics.|
|10008 / 10010|PLACED / DONE_PARTIAL|Check orders/deals and remaining exposure; do not resend the full volume.|
|10004 / 10020 / 10021|Requote / price changed / price off|Inspect fresh tick, market session, spread; retry only through reviewed idempotent policy.|
|10013 / 10014|Invalid request / volume|Inspect symbol constraints, lot min/max/step and request fields offline.|
|10015 / 10016|Invalid price / stops|Inspect digits, tick size, stop/freeze distance, side, current quote age and tighten-only legality. Never remove SL just to get a fill.|
|10017 / 10018 / 10019|Trading disabled / market closed / insufficient money|Keep hold; inspect permissions/session/exposure, never auto-enable or increase risk.|
|10024|Too many requests|Bounded backoff; reconcile uncertain previous outcomes first.|
|10026 / 10027|Server/client disables algorithmic trading|Operator reviews policy; dashboard must not enable it.|
|10031|Connection failure|Follow guarded MT5 reconnection runbook and validate account identity.|

A None result or exception is not a denial proof: inspect last_error and broker history. Manager account_mismatch/not_demo_account is an intentional safety block. Do not bypass manager_connection.py or broker_lifecycle.py. REST 200 availability snapshots do not prove terminal connectivity.

## Telegram flood waits / authorization / locked session
For FloodWaitError, honor Telegram's supplied wait duration and stop overlapping collectors/logins; use bounded backoff and record next retry, not rapid retries or account rotation. For revoked authorization, follow re-auth runbook with one session owner and local interactive code entry. For SQLite session lock, identify exact process owners before touching telethon.session; never delete a live session or copy a WAL database naively. A research scanner should use its private backup session, not attach the live daemon session. Verify channel access/IDs and parser rejection separately from transport health. Do not replay old messages into an executing daemon to test transport.

## PineTS compilation and series failures
HTTP 503 'credential-free OS-isolated worker not configured' is expected fail-closed behavior, not a Node installation bug. Do not enable HTTP offline helpers to remove it. Authenticated 404 on `/api/pine/series` is an old spelling; use `/api/pine_series` (still 503). 400 indicates chart/path/body validation; 413 indicates source/body size. Offline trusted research failures: check Node path/version, dependency resolution, exact .pine path and supported syntax, saved candle schema/closed bars, bridge stderr/exit code and JSON output. Reproduce in an isolated saved-data fixture; never replace failures with simulated live plots. Timeout requires process-tree cleanup verification, not an unbounded timeout increase.

## Neural gate unmet
`/api/neural` exposes completed vs collected vs pending counts; `/api/neural.health` does not exist. Count readiness is not training approval. The collector links labels to tickets and closed outcomes; partial closes/history lag/missing SL R-basis can defer labels. Review `neural_label_collector.py status` and diagnostic evaluation artifact `signals.db.neural_eval.json` without manufacturing outcomes or lowering thresholds. Current minimum is configuration/code-derived (commonly 300), not a guarantee that 300 rows suffice.

`evaluate_collection_gate()` counts provenance via neural_labels -> neural_label_map -> trades with status='executed'. Too few verified labels forces CONTINUE; diagnostic PROMOTE becomes KEEP_SHADOW because a live shadow-inference consumer is not wired. The report explicitly notes purged splits not invoked by evaluation, threshold selection and binary-win/loss scoring limitations. Resolve provenance and missing integration; never relabel imported/synthetic outcomes as executed or interpret diagnostic metrics as activation. Collector remains read-only to MT5; protect that boundary.

## Other symptom checklist
* 401: fresh local bootstrap/session or approved credential; do not expose token in a URL/log. 403: exact loopback Host/port and same-origin Origin, no remote proxy workaround.
* HTTP 200 but no intelligence/simulation: examine available/reason and source timestamps; lack of records is unavailable, not zero risk. Preserve market provenance.sourceUrl.
* SSE disconnect: finite snapshot ends with [DONE] by design; use another bounded history request.
* Duplicate processes: MAINTENANCE, inspect exact paths and owning scheduler; do not kill broad name patterns or remove locks blindly.
* Missing news: inspect news refresh result and age of retained calendar; old artifact retained after fetch failure is not fresh evidence.
* Stop rejected: inspect preflight reason, stop/freeze constraints, side and quote freshness; do not widen a protected stop automatically.
* UI port up but stale: inspect backend health/identity and event timestamps, then isolated API boundary tests. Do not declare success solely on an HTTP status.

Escalation packet: redacted identity, timestamps, route/method/status or retcode, relevant event/trace IDs, flags, source revision and reproduction on isolated data. Exclude config secrets, .cockpit-token, telethon sessions and raw /api/token responses. Keep entries held until evidence resolves uncertainty.


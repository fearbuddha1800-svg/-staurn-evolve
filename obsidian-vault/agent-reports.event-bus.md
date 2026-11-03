---
slug: agent-reports.event-bus
type: note
graph: gitnexus
---

# Event bus design (signal-relay)

## Goal
One in-process pub/sub nervous system so every tool (daemon, executor, manage,
strategy, strategy2_live, cockpit, neural) publishes to / subscribes from a
single bus, with SQLite persistence so the signal→intent→order→position→close
chain survives restarts and is queryable by trace_id.

## Files
- NEW: `event_bus.py` — EventBus class, envelope, 15 event types, `bus` singleton
- EXTEND (no replacement): `scalp360/events.py` — adds `BUS_EVENT_TYPES` frozenset
- BRIDGED: `daemon.py`, `executor.py`, `manage.py`, `strategy.py`, `strategy2_live.py`, `cockpit.py`, `neural.py`
- ENDPOINT: `GET /api/events` on cockpit (last 100 events, `?trace_id=` filter, `?stream=1` SSE)
- TESTS: `tests_360/test_event_bus.py`, added to `tests_360/run_tests.py` SUITES

## Envelope
{event_id, ts, type, source, payload, trace_id}; event_id/ts auto-filled;
trace_id defaults to a fresh uuid but components pass the chain id.

## Event types (15)
signal_received, zone_parsed, risk_approved, order_placed, order_filled,
position_opened, position_closed, pnl_update, neural_prediction,
channel_score_update, engine_status, alert, halt_triggered, pine_signal,
breakout_signal

## Traceability contract
- daemon: trace_id = msg_id ("<chat_id>:<message id>"); publishes signal_received
  + zone_parsed; passes trace_id into executor.execute()
- executor: order_placed/order_filled/position_opened on fill, keyed by trace_id
- manage: position_closed (trace_id recovered from trades.msg_id by ticket),
  pnl_update per position per pass, alert on BE/trail failure
- strategy / strategy2_live: breakout_signal on fill (engine discriminator in
  payload, per-day trace_id)
- cockpit: engine_status at startup; /api/events replays last 100 events
- neural: neural_prediction on each evaluate() run
- Query: GET /api/events?trace_id=<msg_id> → full chain newest-first

## Persistence
SQLite table `events(event_id, ts, type, source, payload, trace_id)` in
signals.db with indexes on trace_id/type/ts; WAL mode, 30s connect timeout;
subscriber exceptions never break publishing or persistence.


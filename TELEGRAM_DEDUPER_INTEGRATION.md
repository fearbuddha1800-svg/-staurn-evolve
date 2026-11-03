# Telegram receipt dedupe / integration sketch

## Delivered and scope

`telegram_deduper.py` uses the existing `parser.parse_signal` for all five channels.
Numeric IDs come from this repository's `analyze_channels.py` (lines 16–26), not title matching.
`test_telegram_deduper.py` exercises parsing, durable replay, edits, isolation, atomic concurrency,
metadata retention, management messages, missing SL and event selection.
No daemon, watchdog, collector, trading config, production database or cron changes are applied.
The watchdog cron `3e28ede5f34b` remains untouched; do not resume it as part of deploying this sketch.

## Meaning of the 95% observation

The supplied context says `pnl_update` accounted for about 95% of `/api/events` volume.
This is NOT a fuzzy text-match threshold or a promise of a 95% reduction on every batch.
Use the existing `/api/events?exclude=pnl_update` option for event consumers.
Apply exclusion before SQL LIMIT/pagination; preserve raw SQLite events and event IDs.
`non_pnl_events()` is the offline equivalent and preserves all other events in order.
Report actual excluded/input counts per observation window; 95 of 100 in tests is a fixture,
not measured live traffic. Do not remove repeated close/SL/TP events merely for similar text.

## Ingest integration (shadow first)

Construct one `TelegramDeduper('telegram_dedupe_shadow.db')` in the existing daemon.
Do NOT open another Telethon client or share its writable session with a sidecar.
After existing sender/channel allow-list checks and existing raw-message audit persistence:

```python
# Sketch inside the current channel handler; no new Telegram connection.
if channel_id in CHANNELS:
    observation = deduper.process(channel_id, event.message.id, effective_text,
                                  metadata=receipt_metadata)
    # Record observation.status + receipt_key alongside existing trace_id.
    # Continue the original processing path unchanged during shadow rollout.
```

`receipt_metadata` should include original/reply peer+message IDs, forwarding origin,
Telegram timestamp and edit timestamp (serialize dates as ISO strings).
`effective_text` must be the existing pipeline's canonical text after OCR; metadata-only
changes do not create a revision. Empty media-only messages are `needs_ocr_or_empty`.
After OCR the changed text becomes an edit requiring review, not a new automatic trade.
Normalize neither numeric IDs nor message content inside this receipt layer.

Status contract:
- `candidate`: parsed entry with SL; still needs all existing execution gates.
- `duplicate`: exact same channel/message/text receipt previously observed.
- `edit_review`: changed text on the same message; never a new auto-entry.
- `not_entry`: route to existing chatter/management classification, not entry routing.
- `missing_sl`: reject entry under existing require_sl policy.
- `needs_ocr_or_empty`: keep for existing OCR/audit path.

Different message IDs and different channels remain distinct even with identical text.
Cross-channel content similarity is not proof of a duplicate trade. Any future semantic
candidate linking must preserve the original receipts and use explicit source/reply lineage,
entry/SL/TP geometry and a reviewed time window; never fuzzy-suppress SL or management changes.

Before enabling duplicate suppression, connect claims to the existing durable execution
ledger/outbox and reconcile pending receipts on startup. A SQLite receipt claim followed by
an order-send is NOT an atomic exactly-once operation. This module deliberately cannot
place trades and must not replace the daemon's current idempotency controls.
Retain the active 1% risk, require_sl and all stop/lock/authority gates unchanged.

## Neural collector supervision

Keep `neural_label_collector.py` read-only with respect to MT5. Do not attach it to Telegram.
The existing CLI is `python neural_label_collector.py watch [secs]` (default 15 seconds).
Add its supervision to the existing watchdog only after reviewing STOP semantics:

1. Under the watchdog's existing OS supervisor lock, match the exact Python executable,
   absolute collector path and `watch` argument, not a substring or unrelated process name.
2. Respect the collector's own STOP file and global intentional stop controls before spawn;
   never restart a deliberately stopped collector. Run at most one collector writer.
3. Start with the same detached/Windows-compatible process helper already used by the
   watchdog, correct repository cwd, and a dedicated rotating collector log.
4. Monitor process liveness plus last successful collection timestamp. A live but stale
   collector is unhealthy; report it rather than spawn a competing instance.
5. Keep the cron paused until operator approval; a 15-minute watchdog is crash recovery,
   not proof of uninterrupted observation. Prefer a persistent supervisor for tighter SLA.

The collector continues deriving labels from real signals.db trade/ticket lineage and
read-only MT5 deals/rates, not from deduper statuses or channel claims of profit.
Preserve original signal/trace/ticket IDs. Never create training labels for rejected,
duplicate, pending, unexecuted or edited signals solely from parsed Telegram text.
P&L heartbeat filtering is only for event views, not the collector's deal/outcome evidence.

## Offline usage / verification

From `C:/Users/voidk/.hermes/workspace/signal-relay`:

```text
python -m unittest test_telegram_deduper -v
python telegram_deduper.py receipts.jsonl --db telegram_dedupe_shadow.db
python telegram_deduper.py events.jsonl --events
```

Receipt JSONL fields: integer `channel_id`, positive integer `message_id`, string `text`,
optional JSON-object `metadata`. Event JSONL uses the event bus envelope's `type` field.
Use separate databases for separate logical consumers. Replaying receipt input deliberately
returns duplicates after the initial run; retain the first run's observations for audit.
No live Telegram or MT5 verification is implied by the offline tests.

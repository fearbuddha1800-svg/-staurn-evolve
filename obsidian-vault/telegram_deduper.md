---
slug: telegram_deduper
type: note
graph: gitnexus
---

"""Offline/shadow Telegram receipt dedupe and lossless non-PnL event selection.

No Telegram session, MT5 connection, order routing, or live-config mutation.
The reported 95% is event volume attributable to pnl_update, NOT a text-similarity
threshold. Exact receipt dedupe is durable; edited messages require review.
"""
from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable, Iterator, Mapping

CHANNELS = {
    -1002369502254: "Best Signal Forex",
    -1002692333123: "XAUUSD PRO SIGNAL",
    -1001920020352: "Grow Trading",
    -1002165799093: "XAUUSD FREE SIGNALS",
    -1001284268486: "Easy Forex OFFICIAL",
}


@dataclass(frozen=True)
class Decision:
    channel_id: int
    message_id: int
    revision: str
    status: str
    parsed: dict[str, Any]
    # This is an observation identity, not an execution or training-label ID.
    receipt_key: str


def non_pnl_events(events: Iterable[Mapping[str, Any]]) -> Iterator[Mapping[str, Any]]:
    """Consumer-side exclusion only: never delete persisted event evidence.

    Trade lifecycle/SL/TP/close events always survive, including repeated ones.
    The SQLite HTTP endpoint should filter BEFORE LIMIT for correct pagination.
    """
    for event in events:
        if event.get("type") != "pnl_update":
            yield event


class TelegramDeduper:
    """Atomic receipt claims for one logical consumer using a dedicated SQLite DB.

    Do not use as an exactly-once order-send primitive: commit and order_send are
    not one transaction. A crash after claim needs existing ledger reconciliation.
    Raw receipts remain in the daemon's existing audit stream; this DB stores only
    hashes, parse evidence and reply/forward/edit metadata supplied by the caller.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        if self.db_path == ":memory:":
            raise ValueError("use a persistent file (each operation opens a connection)")
        with closing(self._connect()) as conn, conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS telegram_dedupe_receipts (
                channel_id INTEGER NOT NULL, message_id INTEGER NOT NULL,
                revision TEXT NOT NULL, status TEXT NOT NULL,
                parsed_json TEXT NOT NULL, metadata_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (channel_id, message_id, revision))""")

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def process(self, channel_id: int, message_id: int, text: str,
                *, metadata: Mapping[str, Any] | None = None) -> Decision:
        # Reject strings/bools rather than silently repairing source identifiers.
        if type(channel_id) is not int or channel_id not in CHANNELS:
            raise ValueError("channel_id must be one of the five numeric channel IDs")
        if type(message_id) is not int or message_id <= 0:
            raise ValueError("message_id must be a positive integer")
        if not isinstance(text, str):
            raise TypeError("text must be a string; OCR belongs to the existing pipeline")
        revision = sha256(text.encode("utf-8")).hexdigest()
        key = f"{channel_id}:{message_id}:{revision}"
        # Use the deployed parser, not a competing set of signal heuristics.
        from parser import parse_signal
        parsed = parse_signal(text)
        metadata_json = json.dumps(dict(metadata or {}), sort_keys=True, allow_nan=False)
        parsed_json = json.dumps(parsed, sort_keys=True, allow_nan=False)
        with closing(self._connect()) as conn, conn:
            conn.execute("BEGIN IMMEDIATE")
            prior = conn.execute(
                "SELECT parsed_json FROM telegram_dedupe_receipts "
                "WHERE channel_id=? AND message_id=? AND revision=?",
                (channel_id, message_id, revision)).fetchone()
            if prior:
                return Decision(channel_id, message_id, revision, "duplicate",
                                json.loads(prior[0]), key)
            edited = conn.execute(
                "SELECT 1 FROM telegram_dedupe_receipts WHERE channel_id=? AND message_id=?",
                (channel_id, message_id)).fetchone()
            if edited:
                status = "edit_review"
            elif not text.strip():
                status = "needs_ocr_or_empty"
            elif not parsed.get("parse_ok"):
                status = "not_entry"
            elif parsed.get("sl") is None:
                status = "missing_sl"
            else:
                status = "candidate"  # never authority to send a trade
            conn.execute("INSERT INTO telegram_dedupe_receipts "
                         "(channel_id,message_id,revision,status,parsed_json,metadata_json) "
                         "VALUES (?,?,?,?,?,?)",
                         (channel_id, message_id, revision, status, parsed_json, metadata_json))
        return Decision(channel_id, message_id, revision, status, parsed, key)


def main() -> None:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("input", type=Path, help="JSONL receipts or events; never connects to Telegram")
    cli.add_argument("--db", type=Path, help="Dedicated persistent shadow dedupe database")
    cli.add_argument("--events", action="store_true", help="Filter pnl_update; no database writes")
    args = cli.parse_args()
    if not args.events and args.db is None:
        cli.error("--db is required for Telegram receipt mode")
    deduper = None if args.events else TelegramDeduper(args.db)
    with args.input.open(encoding="utf-8-sig") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
                if args.events:
                    for event in non_pnl_events([row]):
                        print(json.dumps(event, ensure_ascii=False, allow_nan=False))
                else:
                    result = deduper.process(row["channel_id"], row["message_id"],
                                             row.get("text", ""), metadata=row.get("metadata"))
                    print(json.dumps(asdict(result), ensure_ascii=False, allow_nan=False))
            except (ValueError, KeyError, TypeError) as exc:
                raise SystemExit(f"line {line_no}: {exc}") from exc


if __name__ == "__main__":
    main()

## Links from
- [[test_telegram_deduper]]

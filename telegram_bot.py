"""
Telegram Bot - Offline Core

This module provides an offline skeleton for Telegram long-polling / webhook
operation. It is designed for signal-dm filtering and message receipt
without any live broker or order dispatch.

Usage:
    from telegram_bot import fetch_updates, parse_dm

    updates = fetch_updates()
    for update in updates:
        dm_text = parse_dm(update)
        # process signal text
"""

import json
import time
from typing import Any, Dict, List


def fetch_updates() -> List[Dict[str, Any]]:
    """
    Return mock Telegram updates for offline testing.

    In a live deployment this would connect to Telegram's long-polling
    or webhook endpoint. Currently returns a static list of update
    dicts simulating received messages.

    Returns:
        List of update dicts as returned by Telegram API.
    """
    return [
        {
            "update_id": 1,
            "message": {
                "message_id": 1,
                "from": {"id": 123456, "is_bot": False, "first_name": "Alice"},
                "chat": {"id": 123456, "type": "private"},
                "date": int(time.time()),
                "text": "/start",
            },
        },
        {
            "update_id": 2,
            "message": {
                "message_id": 2,
                "from": {"id": 987654, "is_bot": False, "first_name": "Bob"},
                "chat": {"id": 987654, "type": "private"},
                "date": int(time.time()),
                "text": "Buy EUR/USD at 1.05",
            },
        },
    ]


def parse_dm(event: Dict[str, Any]) -> str:
    """
    Extract the signal text from a direct‑message event.

    Looks for a "text" field in the nested message dict and returns it
    stripped of leading/trailing whitespace. If the event does not contain
    a textual payload, returns an empty string.

    Args:
        event: A single update dict as returned by fetch_updates().

    Returns:
        The message text, or '' if none found.
    """
    message = event.get("message") or {}
    text = message.get("text")
    if text:
        return text.strip()
    return ""


# ---------------------------------------------------------------------------
# Skeleton entry‑point (offline only — no live broker integration)
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Run a minimal offline poll loop.

    Repeatedly calls fetch_updates(), runs each through parse_dm(),
    and prints any detected DM text. No orders are dispatched.
    """
    print("Telegram offline core running (no broker).")
    while True:
        updates = fetch_updates()
        for upd in updates:
            dm_text = parse_dm(upd)
            if dm_text:
                print(f"DM signal text: {dm_text}")
        time.sleep(2)


if __name__ == "__main__":
    main()
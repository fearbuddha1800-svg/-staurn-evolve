---
slug: notify
type: note
graph: gitnexus
---

"""Notify: push messages into the user's Hermes Telegram chat via the Hermes bot.

Reads TELEGRAM_BOT_TOKEN from ~/.hermes/.env at runtime (never stored here).
The Hermes gateway polls getUpdates; this only SENDS, so there is no conflict.
"""
import json
import os
import re
import urllib.parse
import urllib.request

HERMES_ENV = os.path.join(os.path.expanduser("~"), ".hermes", ".env")
CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


def _bot_token():
    with open(HERMES_ENV, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = re.match(r"\s*TELEGRAM_BOT_TOKEN\s*=\s*(\S+)", line)
            if m:
                return m.group(1).strip().strip('"').strip("'")
    raise RuntimeError("TELEGRAM_BOT_TOKEN not found in ~/.hermes/.env")


def _send_sync(text: str, chat_id: str = None) -> bool:
    if chat_id is None:
        with open(CONFIG, "r", encoding="utf-8") as f:
            chat_id = json.load(f).get("notify_chat_id", "")
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{_bot_token()}/sendMessage", data=data)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()).get("ok", False)
    except Exception as e:  # noqa: BLE001
        print("notify failed:", e)
        return False


async def send(text: str, chat_id: str = None) -> bool:
    """Async wrapper: daemon.py awaits this."""
    return _send_sync(text, chat_id)


if __name__ == "__main__":
    import asyncio
    import sys
    ok = asyncio.run(send(sys.argv[1] if len(sys.argv) > 1 else "signal-relay: notify channel test"))
    print("sent:", ok)

## Links from
- [[daemon]]
- [[strategy]]
- [[strategy2_live]]

---
slug: alert_dispatcher
type: note
graph: gitnexus
---

"""Alert Dispatcher for PineTS signals.

Sends alerts when a new signal is detected:
  1. Telegram (optional — requires TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID env)
  2. Event bus (cockpit subscribes — already handled by signal_watcher.publish)
  3. Stdout log (always)

Configure:
  export TELEGRAM_BOT_TOKEN="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
  export TELEGRAM_CHAT_ID="-1004403985547"   # Signal Relay Feed channel
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import Any


def _telegram_configured() -> bool:
    return bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"))


def send_telegram(payload: dict[str, Any]) -> bool:
    """Send a signal alert to Telegram via the Bot API. Returns True on success."""
    if not _telegram_configured():
        return False
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    ai = payload.get("ai", {}) or {}
    text = (
        f"🎯 *PineTS Signal*\n"
        f"*{payload['symbol']} {payload['timeframe']}* — {payload['strategy_name']}\n"
        f"Action: *{payload['action'].upper()}* @ `{payload['price']}`\n"
        f"SL: `{payload.get('sl') or '—'}`  TP: `{payload.get('tp') or '—'}`\n"
        f"AI confidence: {ai.get('confidence') or 'n/a'}\n"
        f"Hash: `{payload['signal_hash']}`"
    )
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_notification": False,
    }).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except Exception as exc:  # noqa: BLE001
        print(f"Telegram alert failed: {exc}")
        return False


def dispatch(payload: dict[str, Any]) -> None:
    """Dispatch a signal alert through all configured channels."""
    telegram_ok = send_telegram(payload)
    print(f"[ALERT] {payload['symbol']} {payload['action']} @ {payload['price']} "
          f"(AI={payload.get('ai', {}).get('confidence') or 'n/a'}) "
          f"{'[telegram OK]' if telegram_ok else '[telegram not configured]'}")


__all__ = ["dispatch", "send_telegram"]

## Links from
- [[signal_watcher]]

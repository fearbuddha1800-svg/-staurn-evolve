---
slug: login
type: note
graph: gitnexus
---

"""One-time Telethon login: python login.py +1XXXXXXXXXX
Sends the login code to the phone's Telegram app, then waits for the code on stdin.
Run interactively (pty). Saves the persistent session used by daemon.py."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daemon import SESSION, _env_creds  # noqa: E402


async def main():
    from telethon import TelegramClient
    api_id, api_hash = _env_creds()
    if not (api_id and api_hash):
        print("NO CREDS: telegram_creds.json missing api_id/api_hash")
        sys.exit(1)
    phone = sys.argv[1] if len(sys.argv) > 1 else ""
    if not phone.startswith("+"):
        print("Pass phone with country code, e.g. +16315652252")
        sys.exit(1)
    print(f"connecting with api_id={api_id} ...", flush=True)
    client = TelegramClient(SESSION, api_id, api_hash)
    try:
        await client.start(phone=phone)  # prompts ONLY for the code
    except Exception as e:  # noqa: BLE001
        print(f"LOGIN FAILED: {type(e).__name__}: {e}", flush=True)
        await client.disconnect()
        sys.exit(2)
    me = await client.get_me()
    print(f"LOGGED IN as {me.first_name} (@{me.username}) id={me.id}", flush=True)
    print("Session saved:", SESSION, flush=True)
    await client.disconnect()


asyncio.run(main())


"""Create the 'Signal Relay Feed' Telegram channel, promote the notify bot to
admin, and print the bot-API chat id to wire into trade-relay .env."""
import asyncio
import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daemon import SESSION, _env_creds  # noqa: E402

TITLE = "Signal Relay Feed"


def bot_username():
    env = open(os.path.join(os.path.expanduser("~"), ".hermes", ".env"),
              encoding="utf-8", errors="ignore").read()
    tok = re.search(r"TELEGRAM_BOT_TOKEN=(\S+)", env).group(1)
    with urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/getMe", timeout=15) as r:
        return json.loads(r.read())["result"]["username"]


async def main():
    from telethon import TelegramClient
    from telethon.tl.functions.channels import CreateChannelRequest, EditAdminRequest
    from telethon.tl.types import ChatAdminRights
    api_id, api_hash = _env_creds()
    c = TelegramClient(SESSION, api_id, api_hash)
    await c.connect()
    if not await c.is_user_authorized():
        print("NOT_AUTHORIZED")
        return
    uname = bot_username()
    print("notify bot: @" + uname)
    # find existing channel with the same title (idempotent)
    async for d in c.iter_dialogs(limit=200):
        if getattr(d, "title", None) == TITLE and d.is_channel:
            print(f"EXISTS already, chat id: {d.id}")
            ch = d.entity
            break
    else:
        res = await c(CreateChannelRequest(
            title=TITLE, about="Automated signal-relay + trade-relay activity feed",
            megagroup=False))
        ch = next(x for x in res.chats if getattr(x, "title", None) == TITLE)
        print(f"CREATED, raw id: {ch.id}")
    # promote the bot so it can post
    bot = await c.get_entity(uname)
    rights = ChatAdminRights(post_messages=True, edit_messages=True, delete_messages=True,
                             invite_users=False, change_info=False, pin_messages=True,
                             add_admins=False, anonymous=False, manage_call=False,
                             other=True)
    try:
        await c(EditAdminRequest(channel=ch, user_id=bot, admin_rights=rights))
        print("BOT PROMOTED: @" + uname)
    except Exception as e:  # noqa: BLE001
        print("PROMOTE FAILED (maybe already admin):", type(e).__name__, str(e)[:120])
    chat_id = int(f"-100{ch.id}") if ch.id > 0 else ch.id
    if not str(chat_id).startswith("-100"):
        chat_id = int(f"-100{abs(ch.id)}")
    print("BOT_API_CHAT_ID=", chat_id)
    await c.disconnect()


asyncio.run(main())

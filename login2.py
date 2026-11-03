"""Two-phase Telethon login (robust, no interactive retry loop).
Phase 1: python login_send.py +1XXXXXXXXXX  -> sends code, prints WHERE it was
         delivered, saves phone_code_hash to login_state.json
Phase 2: python login_sign.py 83377      -> signs in with the stored hash
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daemon import SESSION, _env_creds  # noqa: E402

STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login_state.json")


async def send_phase():
    from telethon import TelegramClient
    api_id, api_hash = _env_creds()
    phone = sys.argv[1]
    force_sms = "--sms" in sys.argv[2:]
    client = TelegramClient(SESSION, api_id, api_hash)
    await client.connect()
    if await client.is_user_authorized():
        print("ALREADY_AUTHORIZED")
        await client.disconnect()
        return
    sent = await client.send_code_request(phone, force_sms=force_sms)
    t = type(sent.type).__name__
    print(f"CODE_SENT channel={t} timeout={getattr(sent, 'timeout', '?')}s")
    nxt = getattr(sent, "next_type", None)
    if nxt:
        print("NEXT_CHANNEL_IF_MISSED:", type(nxt).__name__)
    with open(STATE, "w") as f:
        json.dump({"phone": phone, "phone_code_hash": sent.phone_code_hash}, f)
    await client.disconnect()
    print("WAITING_FOR_CODE")


async def sign_phase():
    from telethon import TelegramClient
    api_id, api_hash = _env_creds()
    code = sys.argv[1].strip()
    with open(STATE) as f:
        st = json.load(f)
    client = TelegramClient(SESSION, api_id, api_hash)
    await client.connect()
    try:
        me = await client.sign_in(phone=st["phone"], code=code,
                                  phone_code_hash=st["phone_code_hash"])
    except Exception as e:  # noqa: BLE001
        print(f"SIGN_IN_FAILED {type(e).__name__}: {e}")
        await client.disconnect()
        sys.exit(2)
    me = await client.get_me()
    print(f"LOGGED_IN as {me.first_name} (@{me.username}) id={me.id}")
    print("SESSION_SAVED", SESSION)
    await client.disconnect()


if __name__ == "__main__":
    if sys.argv[1:] and sys.argv[1] == "sign":
        asyncio.run(sign_phase())
    else:
        asyncio.run(send_phase())

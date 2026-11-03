---
slug: agent-reports.telegram-console
type: note
graph: gitnexus
---

# Telegram Control Console (DM commands) — 2026-10-16

The owner (Telegram user id **8877588890**, @v01dkrawl7er) now commands the
signal-relay from the **DM chat with the relay's Telethon account**. Shipped in
`daemon.py` (+ small `status.py` readout, + `test_console.py`). **executor.py,
manage.py, strategy.py, config.json untouched** (verified: only daemon.py,
status.py, test_console.py modified).

## Commands (case-insensitive, tolerate leading '/', extra whitespace)

| Command | Action | Reply |
|---|---|---|
| `status` | read MT5 account + positions + ledger | balance/equity/free margin, every open position (#ticket symbol DIR lots SL P/L + total P/L), engine uptime, mode + HALT/PAUSE state, last 3 ledger rows |
| `close <ticket>` | close that EXACT position (fetched via `mt5.positions_get(ticket=…)`) | `closed #N SYMBOL DIR lots (filled @ p) \| P/L at close ±X.XX`, or `no open position #N`, or usage/reject detail |
| `closeall` | `executor.close_all_positions()` (fallback: per-ticket close if the helper is ever removed) | `closeall: closed n/m position(s) \| P/L at close ±X.XX` |
| `pause` | touch `PAUSE` file next to daemon.py | confirmation; NEW signal entries blocked |
| `resume` | delete `PAUSE` | confirmation (or "was not active") |
| `help` | — | command list |
| *anything else* | — | `unknown command: '…' - DM 'help' for the list` |

Replies go through **`notify._send_sync`** → the same `notify_chat_id`
(8877588890) Hermes-bot DM as every relay report.

## Auth model (fail-closed)

The Telethon session is a **dedicated relay account** (confirmed: 8877588890 is
cached in `telethon.session` as a DM peer, not the session owner). A message is
a command only when **ALL** hold:

1. `event.chat_id > 0` — private chat (Telethon marks channels/groups negative),
   so watched-channel messages (all `-100…`) can never be commands;
2. `chat_id == OWNER_ID` — the daemon's own DM chat;
3. `sender_id == OWNER_ID` — the message is FROM the owner.

Every other DM — stranger, bot, or the owner typing in another chat (friends,
the Hermes bot) — is **ignored silently with exactly one log line**
(`[console HH:MM:SS] DM ignored: sender … chat …`) and no reply. A DM is
**never parsed as a signal**, whoever sent it: injected DM "signals"
(`BUY XAUUSD SL …` from a stranger's DM) are structurally impossible to trade.

## Signal path: 100% intact

- `run()` keeps `events.NewMessage(chats=channels)` → `handler` untouched; a
  second `dm_handler` (`events.NewMessage()`) forwards **only positive
  (private) chat ids** into `on_message` and returns after one comparison for
  everything else, so no double-processing.
- `on_message`'s console branch is first: one `isinstance/int < 0` check for
  channel messages (cost: nanoseconds), full handling only for DMs.
- Command MT5 work runs on the event-loop thread (naturally serialized with
  `execute()` — no cross-thread MT5 races); only the reply HTTP call runs in
  `asyncio.to_thread`, so a slow Telegram API can never stall ingestion.
- Console code attaches to MT5 **exactly like `executor.execute()`**
  (`initialize()` only if `terminal_info()` is None, **never `shutdown()`**) —
  deliberately NOT `executor.mt5_session()`, whose shutdown would tear down
  the executor's live in-process connection mid-trade. No second login.

## PAUSE semantics

`paused()` (`os.path.exists(PAUSE)`) is checked in `on_message`'s pre-execute
gate **immediately after `halted()`** — the same way HALT is checked. It
blocks NEW signal entries only (the blocked signal still gets one
`PAUSE active - not executed` notify, mirroring HALT behavior). It is read by
**daemon.py only**: executor.py and manage.py never see the file, so open
positions keep being managed (SL→BE, trailing) and can still be closed via
`close`/`closeall` while paused. `status.py` now also lists PAUSE.

## Files changed

- `daemon.py` — docstring, `OWNER_ID`/`PAUSE_FILE`/`_ENGINE_STARTED` constants,
  console block (`paused`, `parse_command`, `classify_dm`, `_cmd_*`,
  `_dispatch_command`, `_console_reply`, `_console_branch`), console branch at
  top of `on_message`, PAUSE gate, `dm_handler` registration, uptime start,
  ONLINE message mentions the console.
- `status.py` — PAUSE added to kill-switch listing (read-only tool).
- `test_console.py` — NEW, 48 checks.

## Test verdict (all real runs, miniconda 3.13.13)

- `test_console.py`: **48/48 PASS, exit 0** — every command parses (each
  spelling), unknown → "unknown command" reply, non-user sender rejected
  silently (branch wiring: stranger DM consumed, zero replies; channel message
  falls through to the signal path), pause/resume round-trip on a scratch
  PAUSE file (machine state untouched), help/close-usage paths.
- `test_suite.py` (FULL suite): **ALL PASS, exit 0** — 9/9 signal cases plus
  the parallel agent's 6 news-filter cases (N1–N6), i.e. the console changes
  coexist cleanly with the in-flight executor.py news-gate work.
- Live read-only smoke of `status` (real MT5, no orders sent):
  `Account 5057394166 @ MetaQuotes-Demo, balance 99999.92 USD, equity
  100012.49, 4 open positions (XAUUSD/USDCAD/EURUSD/USDJPY) each rendered as
  #ticket SYMBOL DIR lots SL P/L, last 3 ledger rows`. No PAUSE/HALT files
  created; nothing traded.

## How to activate

Restart `daemon.py` (the running pid still executes the pre-console code; a
single-instance lock makes the old process exit cleanly on overlap). On the
next serve attempt the console is live and the ONLINE message says
`console: DM 'help' for commands`. Not restarted here on purpose: the
parallel executor.py edit is still in flight.

## Notes / risks

- `close`/`closeall` were unit-tested only up to the MT5 boundary (arg
  validation, gate, reply shape); live close was NOT exercised (would close
  real positions). The order request mirrors `executor.close_all_positions`
  (TRADE_ACTION_DEAL, position ticket, deviation 50, magic 20261014).
- `_fill_type` prefers `executor._fill_type` with a self-contained bit-logic
  fallback, so a rename in the parallel executor edit cannot break closes.
- Bot-API replies (Hermes chat) never enter the Telethon session; the user's
  own messages to the Hermes bot are "foreign" (different chat id) and ignored.


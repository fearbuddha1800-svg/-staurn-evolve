---
slug: agent-reports.news-filter
type: note
graph: gitnexus
---

# News filter: High-impact USD event gate for new entries

**Date:** 2026-10-16 · **Scope:** executor entry path only — daemon.py and manage.py NOT edited (parallel agent owns daemon.py).

## What shipped

| File | Change |
|---|---|
| `news_fetcher.py` | NEW. Fetches `https://nfs.faireconomy.media/ff_calendar_thisweek.json` (free, no key; 3 retries, 30s timeout each, backoff). Keeps only events with `country == USD` and High impact (title fallback), normalizes to `{dt_utc, title, impact}` (UTC ISO), purges past events, and writes `news_calendar.json` atomically (tmp + `os.replace`). On ANY failure (network, bad JSON, disk) the existing calendar is left untouched. Also exposes `block_reason(cfg, now, events)` (the gate check) and `log_daemon()` (best-effort append to daemon.log). Schema drift tolerated: key aliases (`country`/`currency`, `title`/`event`, `impact`/`importance`, `date`/`datetime`), offset/`Z`/epoch/strptime dates; unusable events are skipped, never crash. |
| `executor.py` | (1) News gate in `execute()` immediately AFTER the `_guards()` HALT/dedupe block: if `news_filter.enabled` and now ∈ [event − pre, event + post] of any calendar event → `result["status"] = "skipped_news_window"`, same ledger skip-row style as other skips (`_record(result, parsed, 0)` → status+detail row, ticket 0 in signals.db), plus a `daemon.log` line; then return. (2) Daily-cap query in `_guards` changed from `status!='skipped'` to `status NOT LIKE 'skipped%'` so news-window skips (a required new status name) cannot consume the 20/day entry budget. Fail-open: any exception inside the filter lets the trade proceed. |
| `config.json` | Added `news_filter` key (see below). Validated with `json.load` — parses. |
| `C:/Users/voidk/.hermes/scripts/signal-relay-watchdog.py` | Added guarded `_refresh_news()` called at the end of `main()`: runs `news_fetcher.py` as a subprocess (timeout 240s). Fully try/except-wrapped — a fetch failure prints one line and NEVER kills the watchdog; the old calendar is kept (that guarantee lives inside news_fetcher too). Verified by importing the watchdog module and calling `_refresh_news()` directly: live fetch OK, caller survived. |
| `test_suite.py` | 6 new cases (N1–N6) after the untouched 9 parser cases; per-case try/except so a case failure never crashes the suite. Temp dir stubs `news_fetcher.CALENDAR/DAEMON_LOG/_urlopen/_sleep` and `executor.CONFIG/DB/HALT_FILE` — the LIVE ledger, config, calendar and daemon.log are never touched; `execute()` always called with `dry_run=True` so no order can be sent. Restores all module attrs in `finally`, removes the temp dir. |
| `news_calendar.json` | Produced by a real fetch (twice, incl. via the watchdog path). Currently `[]` — correct: all High USD events this week (CPI, PPI, Retail Sales, Oct 14–15) have already passed and were purged. |

## How the gate works

`executor.execute()` order: MT5 attach → resolve symbol → channel policy → `_guards()` (HALT, dedupe, daily cap, symbol/margin checks) → **NEWS GATE** → symbol_select → require_sl → stops validation → dry-run/order. The gate reads `news_calendar.json`, and if `now` falls inside `[event − pre_minutes, event + post_minutes]` of any event, the entry is skipped with status `skipped_news_window`, a ledger row (ticket 0, detail names the event and window) and a `daemon.log` line. Positions already open are never touched — no changes to manage.py, no SL/TP modification, no position closing. Fail-open by design: missing/corrupt calendar, disabled filter, or any filter error → trade proceeds.

## Config keys added

```json
"news_filter": {
  "enabled": true,          // master switch; missing key = disabled (fail-open)
  "pre_minutes": 5,         // default 5; block window opens this many minutes before the event
  "post_minutes": 3         // default 3; window closes this many minutes after
}
```

## Test verdict — `PYTHONPATH= C:/Users/voidk/miniconda3/python.exe test_suite.py`

**ALL PASS (15/15), exit 0** — 9 original parser cases unchanged + N1 bad JSON keeps calendar, N2 retries 3x then keeps calendar, N3 High-USD-only filter + past purge + schema-drift keys kept, N4 window math (2 min → block, 2 h → pass, exact pre-edge blocks, past post-edge passes, disabled never blocks), N5 `execute()` → `skipped_news_window` with verified ledger skip-row (status + ticket 0) for an event 2 min out, N6 event 2 h out → full normal flow reached `dry_run_ok` (guards clean, symbol selected, stops validated). N5/N6 attach to the live MT5 terminal read-only; dry_run guarantees zero order_send.

## Operational notes / decisions for the parent

1. **Activation:** the running daemon (pid 179580) imported the old executor before this change, so the gate goes live on the next daemon restart. I deliberately did NOT restart it — the parallel agent may be mid-edit on daemon.py, and restarting now could load a half-finished file. The watchdog restarts the daemon automatically whenever it dies; restart it yourself when the parallel daemon.py work lands.
2. **Algo engine is NOT gated (flag for decision):** `strategy.py` places its own orders (magic 20261015, own `mt5.order_send` at line 281) — it does not go through `executor.execute()`, contrary to the task context blurb. Task scope was explicit ("gate it into executor.execute()"), so XAUUSD algo entries can still open inside a news window. Trivial follow-up if wanted: call `news_fetcher.block_reason(load_algo_cfg())` in `strategy.try_trade()`.
3. **Purge margin:** past events are purged only once their post-window has fully elapsed (post_minutes + 5 min slack, read from config) — so an event released minutes ago still blocks entries for its configured post window; a naive `dt < now` purge would have re-opened the gate mid-spike.
4. **Daily-cap fix:** required because the mandated status name `skipped_news_window` would otherwise count toward the 20/day cap (`status!='skipped'`); now `NOT LIKE 'skipped%'`.
5. **Skip visibility:** daemon.py needs no edit — its status map falls through to `status.upper()`, so the Telegram notification reads "=> SKIPPED_NEWS_WINDOW: High USD news window: '…' at … UTC (…)".
6. **Watchdog cadence:** watchdog runs every 15 min via cron → calendar is at most ~15 min stale; pre-window of 5 min makes that safe for scheduled releases (FF feed timestamps are the release minute).


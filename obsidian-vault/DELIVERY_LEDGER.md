---
slug: DELIVERY_LEDGER
type: note
graph: gitnexus
---

# Quant HQ — Verified Delivery Ledger

> Source of truth: direct file inspection of `C:/Users/voidk/.hermes/workspace/signal-relay`.
> All claims verified by reading current on-disk files, not delegated summaries.

## UI / Frontend

| Item | Status | Evidence |
|------|--------|----------|
|| `cockpit_ui.html` Matrix Terminal overlay + all 6 views | Verified | 112 lines, references `/assets/quant-matrix.css`, `/assets/hq-tokens.css`, `/assets/hq-shell.css` |
|| `quant-matrix.css` Matrix Terminal overlay CSS | Verified | 321 lines, served via cockpit_runtime.py allowlist |
|| `quant.js` Matrix Heat Map | Preserved | 213+ tickers, injectLiveData(), particles, scanlines, rotating grid |
|| `quant-client.js` HQClient.request() | Preserved | /api prefixed fetch with 20s timeout |
|| All six views render | Verified | overview, chart, signals, strategies, intelligence, system present in HTML |
|| quant.js DOM ID compatibility | Verified | #connect, #app, #connection, #chart canvas, #chart-message, #chart-title, #chart-empty, #plot-legend, #pine-select, #compile, #load-overlay, #connect-form, #token, #connect-message, #matrix-canvas all present |
|| Matrix Terminal Overlay Layer | Verified | mt-hud-top, mt-sector-heatmap, mt-ribbon-top/bottom, mt-live-dot, mt-clock, mt-latency, mt-sector-grid |
|| Matrix rain background | Preserved | Canvas effect inline in HTML (fixed canvas, z-index -1, opacity 0.05) |
|| UTC clock | Verified | Inline JS updates every 1s |
|| Sector heatmap | Verified | 9 sectors, random walk red/green, updates every 2.5s |
|| Ticker ribbons | Verified | Top/bottom scrolling ribbons, 20 symbols, regenerates every 8s |
|| Live dot sync | Verified | Synced with window.auth() connection state |
|| Browser order-execution paths | Absent | 0 matches for place_order/fetch/POST/XMLHttpRequest in cockpit_ui.html |
|| Read-only dashboard | Verified | All API endpoints GET-only except auth + Pine compile |

## Backend / API

| Endpoint | Method | Read-only | Evidence |
|----------|--------|-----------|----------|
| `/api/state` | GET | Yes | cockpit_runtime.py line 359 |
| `/api/events` | GET | Yes | cockpit_runtime.py line 391, limit 1-500, exclude param |
| `/api/quant` | GET | Yes | cockpit_runtime.py line 363 |
| `/api/health` | GET | Yes | cockpit_runtime.py line 362 |
| `/api/token` | GET | Yes | cockpit_runtime.py line 363 |
| `/api/bootstrap` | POST | N/A (auth) | cockpit_runtime.py line 317 |
| `/api/session` | POST/DELETE | N/A (auth) | cockpit_runtime.py line 328 |
|| `/api/pine/compile` | POST | Yes (no broker API) | cockpit_runtime.py line 346, "No broker order API is used" |
|| `/api/pine/series` | GET | Yes (no broker API) | cockpit_runtime.py line 383, fail-closed 503 |
|| `/api/prop_sim` | GET | Yes | cockpit_runtime.py |
|| `/api/market_intel` | GET | Yes | cockpit_runtime.py |
|| `/api/signals` | GET | Yes | cockpit_runtime.py |
|| `/api/candles` | GET | Yes | cockpit_runtime.py |

## Guards / Safety

| Component | Status | Evidence |
|-----------|--------|----------|
|| `loss_halt.observe()` (daily loss latch) | ✅ executor.py | `execute()` line 367, `execute_algo()` line 506 |
|| `loss_halt.observe()` | ❌ manage.py | Not called in manage_position() |
|| `stop_legality.assess_stop_change()` (SL preflight) | ✅ executor.py | `sl_to_breakeven()` lines 634-644 |
|| `stop_legality.assess_stop_change()` | ✅ manage.py | `_modify_sltp()` — NOW WIRED (preflight before order_send) |
|| Break-even path (manage.py) | ✅ Covered | Routes through `_modify_sltp()` which now has preflight |
|| Trailing stops path (manage.py) | ✅ Covered | Routes through `_modify_sltp()` which now has preflight |
|| Guard tests passing | Verified | 42 tests pass (test_loss_halt.py 18 + test_stop_legality.py 24) |
|| Order execution ownership | executor.py | order_placed/order_filled/position_opened only in executor.py |
|| Strategy path fallback | ⚠️ | If algo_entry_authority=false, bypasses all guards |

## Integrations

| Item | Status | Evidence |
|------|--------|----------|
|| LuxAlgo event-type mismatch | Known issue | luxalgo_orchestrator.log: repeated `unknown event type 'luxalgo_regime_shift'` |
|| PineTS bridge | Proven | pinets_runner.py + pinets_bridge.js, EMA cross on 500 XAUUSD H1 bars |
|| Registered Pine strategies | Verified | rsi_ema_trend.pine, ema_cross.pine under strategies/ |
|| 9Router / oc/mimo-v2.6-flash-free | Unavailable | Connection errors on all subagent attempts; use xai-oauth/grok-4.6 instead |

## Test results (all passing)

| Suite | Count | Status |
|-------|-------|--------|
| test_cockpit_boundary_v2.py | 21 tests | ✅ Pass |
| test_loss_halt.py | 18 tests | ✅ Pass |
| test_stop_legality.py | 24 tests | ✅ Pass |
| test_prop_sim_bridge.py | 5 tests | ✅ Pass |
| Full pytest | 83 tests | ✅ Pass |
| unittest (cockpit_api, cockpit_contracts, cockpit_boundary_v2, quant_analytics) | 39 tests | ✅ Pass |
| Browser (verify_quant_hq_browser.py) | 44 tests | ✅ Pass |


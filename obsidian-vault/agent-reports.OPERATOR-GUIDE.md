---
slug: agent-reports.OPERATOR-GUIDE
type: note
graph: gitnexus
---

# Quant HQ Cockpit — Operator Guide

**System:** Quant HQ trading command center (VELA Terminal)  
**Location:** `C:/Users/voidk/.hermes/workspace/signal-relay/`  
**Backend:** `cockpit.py` on port 8490  
**Demo account:** MT5 5057394166

---

## Start / Stop / Status

| Action | Command |
|---|---|
| **Start backend** | `hq.bat` (from workspace root) — launches `cockpit.py` on :8490 |
| **Start UI** | Open `http://localhost:8490/` in a browser |
| **Check status** | Browser auto-login → session cookie → all `/api/*` endpoints available |
| **Check raw** | `curl -H "Authorization: Bearer <token>" http://localhost:8490/api/health` |
| **Stop backend** | `Ctrl+C` in the `cockpit.py` window |
| **Force stop** | `taskkill /F /IM python.exe /FI "WINDOWTITLE eq *cockpit*"` |

---

## Authentication

**Auto-login (recommended):**
1. Open `http://localhost:8490/` in Chrome/Edge/Firefox
2. Server injects single-use 180s nonce at `window.__hqBootstrap`
3. Page trades nonce at POST `/api/bootstrap` → receives HttpOnly SameSite=Strict session cookie
4. All `/api/*` calls now authenticated automatically

**Manual token (alternative):**
- Dashboard credential shown in UI System view as "Dashboard credential"
- `POST /api/session` with `Authorization: Bearer <token>` → session cookie
- Token file: `.cockpit-token` in workspace root

**Save token to dashboard file:** Check the box on the connect overlay → token stored in localStorage + synced to `.cockpit-token` for auto-login on reload.

---

## VELA Terminal Panels

| Panel | Key | Endpoint | What you see |
|---|---|---|---|
| Intelligence | top-left | `/api/luxalgo`, `/api/quant`, `/api/market_intel` | LuxAlgo packages, market stats, correlation, risk positions |
| System | top-right | `/api/edge`, `/api/channels` | Edge stats, Wilson CI, signal channels table |
| Signals | bottom-left | `/api/news` | News window, pre/post impact minutes, scheduled events |
| Strategies | bottom-right | `/api/pine_series`, `/api/pine/compile` | PineTS signals from V01D AGI, EMA Cross, RSI+EMA |
| Top ribbon | full width | `/api/candles` | 16 symbols scrolling live prices, 3s poll |
| Bottom ribbon | full width | `/api/pine_series` | PineTS strategy signals, 5s poll |

---

## PineTS Strategies

| File | Description |
|---|---|
| `strategies/v01d_agi.pine` | V01D AGI Pine Script v6 (no request.security, inline EMA HTF trend) |
| `strategies/ema_cross.pine` | EMA Cross strategy |
| `strategies/rsi_ema_trend.pine` | RSI + EMA Trend strategy |

Run via PineTS bridge: `node pinets_bridge.js strategies/<name>.pine <candles.json> XAUUSD 60`

**Verified results (500 XAUUSD H1 bars):**
- ema_cross: 1 open long @ 4145.62, 20 closed trades, netprofit -310.28
- v01d_agi: runs clean, flat position
- rsi_ema_trend: runs clean, flat position

`record_signal` writes `pine_signal` rows (dry-run only, no MT5 orders).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| HTTP 401 on `/api/*` | No auth cookie | Open `http://localhost:8490/` in browser for auto-login, or use `POST /api/session` with Bearer token |
| HTTP 403 on `/api/bootstrap` | Not same-origin | Must be called from browser on `localhost:8490`, not curl from remote |
| `/api/pine_series` empty | count too low | Use `count=220` minimum (verified working) |
| `Math.random` / fake data concerns | None — all live | UI verified zero fake/synthetic markers; all data from `/api/candles` + `/api/pine_series` |
| Subagent delegation fails | OpenCode provider 403 FreeTierError | Billing/credits exhausted at provider — not a code issue; work verified directly |

---

## Test Commands

```
python3 -m pytest test_cockpit_api.py test_cockpit_contracts.py test_quant_analytics.py -v
python3 test_pine_runner.py          (standalone — pytest blocked by sys.exit(0))
```

Expected: 36/36 cockpit + 4/4 pine = **40/40 pass**.


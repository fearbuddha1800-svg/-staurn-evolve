# Quant HQ — Quick Start (5 minutes)

> Install → Start → Dashboard → Verify. All on localhost, no external accounts required.

---

## Step 1 — Install (2 min)

```cmd
cd /c/Users/voidk/.hermes/workspace/signal-relay
install.bat
```

This creates `.venv`, installs dependencies, validates `config.json`, and copies the local config.

---

## Step 2 — Start everything (1 min)

```cmd
start.bat
```

This launches:
- **Cockpit** on http://localhost:8490 (UI + API)
- **Trade-relay** on http://localhost:8484 (MT5 execution proxy)

Then a health check runs automatically. You should see:

```
[OK] Cockpit on port 8490 — HTTP 200
[OK] Trade-relay on port 8484 — HTTP 200
All services running. Dashboard: http://localhost:8490
```

---

## Step 3 — Open the dashboard

Open **http://localhost:8490** in your browser.

It logs you in automatically via a single-use nonce (no password). If you ever see a connect form instead, reload the page locally — the nonce expired.

---

## Step 4 — Verify everything is live

Check these in the dashboard's **System → Process & guard health** view, or via the API:

| What to check | Where | Expected |
|---------------|-------|----------|
| MT5 account connected | Overview / `/api/state` | Account 5057394166, balance $99,888.64 |
| Neural labels ready | Neural / `/api/neural` | 300/300, ready=true |
| Pine strategies | Strategies / `/api/pine` | 3 registered strategies |
| Matrix panels | Matrix grid | 13/16 available |
| Trade-relay | Health / `/api/health` | Port 8484 responding |
| All engines | Health | daemon, manage, strategy, strategy2_live, cockpit, trade-relay |

Or run the one-line verification:

```cmd
python -c "
import urllib.request, json, http.cookiejar, re
cj = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
page = op.open(urllib.request.Request('http://127.0.0.1:8490/')).read().decode()
nonce = re.search(r'window.__hqBootstrap=\"([^\"]+)\"', page).group(1)
op.open(urllib.request.Request('http://127.0.0.1:8490/api/bootstrap',
    data=json.dumps({'nonce': nonce}).encode(),
    headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8490'}, method='POST'))
d = json.loads(op.open(urllib.request.Request('http://127.0.0.1:8490/api/state')).read())
print('MT5:', d.get('account'))
print('Balance:', d.get('balance'))
print('All endpoints live.')
"
```

---

## Step 5 — Stop

```cmd
stop.bat
```

Or stop individual components:

```cmd
python hq.py stop
```

---

## What you should see

After startup, the Matrix Terminal shows **13 panels** with live data:
- **state** — account balance, equity, positions
- **health** — process liveness, port checks
- **neural** — label counts, readiness gate
- **luxalgo** — LuxAlgo package status
- **edge** — edge statistics
- **strategies** — RSI pullback + London breakout engines
- **pine** — PineTS strategies (3 registered)
- **portfolio** — stop risk, concentration
- **latency** — pipeline timing
- **inbox** — signal inbox
- **market-intel** — congress/insider tracking
- **events** — event bus feed
- **candles** — live MT5 OHLCV bars

3 panels are intentionally unavailable by design:
- **prop-sim** — broker-backed simulation disabled (observational HQ)
- **cloudroom** — no verified WSL adapter (local CPU fallback active)
- **pine-live** — browser Pine execution disabled (OS-isolated worker required)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Dashboard won't load | `netstat -ano \| findstr :8490`. If nothing, run `start.bat` |
| Connect form instead of auto-login | Reload `http://localhost:8490` locally (nonce expired) |
| "Session expired" | Sessions last 8 hours. Reload to re-establish |
| MT5 not connected | Ensure MetaTrader 5 terminal is running and logged in to account 5057394166 |
| Trade-relay not responding | Check port 8484: `netstat -ano \| findstr :8484` |
| Everything empty but "Connected" | MT5 isn't attached — check terminal login |

---

## Next steps

- Read [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full system map
- Read [`HQ_USER_GUIDE.md`](HQ_USER_GUIDE.md) for the operator guide
- See [`README.md`](README.md) for the complete API reference
- Configure Telegram channels in `config.json` for signal ingestion
- Enable additional Pine strategies in `config.json` under `pine_strategies`

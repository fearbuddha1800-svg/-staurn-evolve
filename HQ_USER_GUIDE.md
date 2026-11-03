# Quant HQ — Operator Guide

**Dashboard URL:** http://localhost:8490 (served by `cockpit.py`)

**Read-only.** The dashboard never places, modifies or closes orders. It reads MT5, `signals.db`,
`config.json` and the local bridges, and renders them. This guide describes the dashboard as the
code actually behaves today.

---

## Opening it

Open **http://localhost:8490** on this machine. It **logs you in automatically** — there is no
token prompt. (The page is served with a single-use, 180-second, loopback-only nonce that the
client trades for a session cookie.)

If the connect form appears, reload locally first: a nonce can expire after 180 seconds or
have already been consumed. Token fallback is `POST /api/session` via the form. Get it from:

- the dashboard itself: **System → Dashboard credential**
- the file `.cockpit-token` next to `cockpit.py`
- `hq token` on the command line

The session lasts 8 hours. **System → Disconnect** ends it.
The cookie is HttpOnly and SameSite=Strict. This is a loopback-only service: another device's
LAN address is rejected even with the token. Do not expose the credential or paste it in a URL.
The server's `COCKPIT_TOKEN` overrides its file; `hq token` currently prefers the file.

---

## Layout

A left rail with six views, a top bar, and the active view on the right.

**Top bar** (always visible)

| Element | Meaning |
|---|---|
| Connection status | `Connected · local session` / `Degraded · retry available` / `Authentication required` |
| Account badge | `Demo account` / `Live account` / `Contest account` — amber for live |
| Last sync | Time of the last successful refresh |
| **Refresh** | Forces an immediate refresh of the current view |

Core account/activity data refreshes after **15 seconds**; other view data is cached for
60 seconds and refreshed on entry when due, or on **Refresh**. Hidden tabs suspend the timer.

---

## The six views

### 1. Overview
The default view: account, protection, exposure, positions and recent activity.

| Section | What it shows |
|---|---|
| **Measurements** | Balance · Equity · Floating P/L · Free margin. Floating P/L is green when positive, red when negative. |
| **Protection flags** | `Halt:` / `Pause:` / `Stop:` as Active / Clear / Unknown, plus the account login. |
| **Exposure & protection** | Quant risk from `GET /api/quant`: open positions, protected vs. unprotected count, current stop risk in money and as % of balance. Each position is listed with its own stop risk; unprotected tickets are called out explicitly. |
| **Open positions** | Ticket · Symbol/side · Lots · Entry · Current · P/L · SL/TP · R · BE. Click a **ticket** to trace it. |
| **Activity** | The latest events from the event bus: time · source, event type, trace id, payload. A **Ticket** button on an event traces it. |
| **Ticket trace** | Opens under the positions panel when you click a ticket: the ledger rows for that ticket plus the broker-confirmed open/closed status. Evidence only — the ledger alone cannot establish open/closed status. |
| **Daily P/L footer** | Daily realised P/L split into total, signals, and algo, in account currency. |

### 2. Chart Lab
Real broker candles with Pine Script overlays, plus a scratchpad.

- **Symbol** (default `XAUUSD`), **Timeframe** (`M15` `M30` `H1` `H4` `D1`), **Registered Pine**
  (No overlay, or a registered strategy) → **Load chart**.
- **Render registered Pine** runs the selected registered strategy and draws its series over the candles.
- The legend under the chart labels rendered series, including non-price series such as
  RSI and ATR. Hover/value presentation may
  differ by renderer, so use the API series for exact numeric inspection.
- **Pine scratchpad**: edit Pine source and press **Compile & render**, or **Import .pine source**
  to load a file. Compiling the scratchpad does **not** change registered strategies.
- The canvas is a local renderer — no CDN, no synthetic candles. If the broker returns no bars the
  chart says so rather than inventing data.

**Live chart, closed-bar research:** the chart retains the newest forming bar; Pine research
excludes the final received bar. Broker timestamps have no guaranteed timezone, so comparing
them with local wall-clock time is not used to infer closure. `/api/candles` reports
`forming_bar_excluded`, `last_bar_closed` and the broker timestamp basis. Null closure is
unknown, not an assertion that the final displayed candle is closed.
Scratchpad source is owner-trusted, not sandboxed. PineTS v5/v6 support varies; compilation
is research and cannot arm a live order path. Source limits and runtime bounds are in README.

### 3. Signals
Three read-only panels: **Incoming inbox** (`/api/inbox`), **Decision journal** (`/api/journal`),
and **Source channels** (`/api/channels`) with each channel's mode (trading / shadow) and its
SL/TP policy.

### 4. Strategies
- **Strategy engines** — liveness of daemon / manage / strategy / strategy2_live.
- **Strategy identity & attribution** — open-ticket owner, strategy ID/version and broker
  magic, plus the identity registry. Unknown magic stays unknown. Both algo engines share
  legacy magic 20261015, so this panel cannot distinguish their ownership individually.
- **Registered Pine · paper state** — strategies from `config.json` with enabled and paper badges.
- **Neural readiness** — labels collected vs. the 300 required, progress, and the last evaluation.
  The count basis is **completed outcomes**, not all entry snapshots. Its label-pipeline
  health summary shows status, total/complete/pending counts, map consistency, feature
  dimensions and observation time; full details include accumulation rate. Below 300 there
  is no training. Readiness does not activate a model: promotion also requires holdout
  AUC ≥ 0.58 and `model_net > baseline_net > 0`. At the 2026-10-17 read-only probe there were
  2 complete / 3 recorded labels (1 pending), not a trained challenger.
- **Latency measurements** — p50/p95/p99 per pipeline stage.
- **Strategy lineage** — recent intents: signal → intent → order → position.

### 5. Intelligence
- **LuxAlgo ecosystem** — local services (trade-relay :8484, LuxAlgo MCP :3333) and which library
  repos are present and built.
- **Market source** — congress, insider activity, government contracts, lobbying, short volume
  (choose the source, then **Load source**).
- **Edge statistics**, **Prop-firm research simulation**, and the **News risk window** (the pre/post
  entry-blocking window around high-impact USD events).

Monte Carlo pass probabilities are **simulated estimates from observed trade inputs**, not
observed returns or a promise of passing a challenge. Small samples and unavailable sources
must remain labelled as such. News gating is fail-open on source errors; an inactive badge
does not prove that an external calendar is complete. Quant/portfolio stop risk is an
estimate, not maximum possible loss. `/api/portfolio` and `/api/attribution` are additional
read-only API diagnostics; do not assume an endpoint has a dedicated rail panel.

### 6. System
- **Process & guard health** — process liveness, listening ports, database size, and the
  maintenance / halt / pause / stop flags.
- **Dashboard credential** — the token, its file path, and a note.
- **Session → Disconnect** — ends the session.

---

## Emergency controls

These are **not** in the dashboard — they are marker files next to `daemon.py`. The dashboard only
reports their state.

| File | Effect |
|---|---|
| `HALT` | Blocks shared executor new entries; protective management continues. It does not close positions. |
| `PAUSE` | Daemon and strategy2 entry gates; **not universal**: the reviewed RSI strategy/shared executor path does not read it. Management continues. |
| `STOP` | Polling loops exit, including manage and the collector; watchdog launches are suppressed. Automated stop updates cease. |
| `MAINTENANCE` | Suppresses watchdog launch/refresh work, but does not stop existing processes or itself block orders. |
| `ALGO-HALT-YYYYMMDD` | Dated algo daily-loss control, separate from HALT and the new loss-latch library. |

Do not delete a flag just to clear a badge. Establish why it exists, reconcile broker
positions/pending orders and protection, then have the authorised operator decide whether
to resume. **Overview → Protection flags** and **System → Process & guard health** show
flags; `hq status` covers five core components, not the whole watchdog fleet.
New `loss_halt.py` and `stop_legality.py` are library-only until integration is proven;
their presence is not proof of new live enforcement.

For normal lifecycle commands use `hq.py start|stop|status|token|restart` or `hq.bat`;
see README for exact commands. `hq stop` removes only the STOP it created, so the watchdog
can revive components on its next tick unless an operator-maintained STOP/MAINTENANCE holds.
Stopping does not flatten broker exposure. Do not stop manage as a substitute for blocking entries.

---

## Morning checklist

1. **Overview → Measurements:** balance, equity, floating P/L.
2. **Overview → Exposure & protection:** any *unprotected* positions? Stop risk as a % of balance?
3. **Overview → Protection flags:** is Halt / Pause / Stop set, and does that match what you expect?
4. **Overview → Daily P/L footer:** realised P/L split signals vs. algo.
5. **Strategies → Identity/Neural readiness:** expected owners? Completed vs pending labels,
   map/feature health, collector alive, last evaluation? A ready label count is not activation.
6. **System → Process & guard health:** all processes up, expected ports listening?
7. **Overview → Activity:** anything skipped or failed overnight?
8. **Chart Lab/Intelligence:** real broker bars and source timestamps plausible? Research
   is not a fill record. Confirm demo/live account badge and expected news/guard posture
   before authorising any operational changes. Never interpret unavailable as zero risk.

---

## Cloudroom compute-offload status

Cloudroom is installed, but **remote GPU/CPU workload offload is not configured or verified**. An installed desktop application or a ready status does not establish remote execution.

Verified on 2026-11-02:

- `Desktop/Cloudroom.lnk` launches `AppData/Local/Programs/Cloudroom/Cloudroom.exe`.
- `C:/Users/voidk/Projects/cloudroom-windows/README.md` describes an Electron client for Cloudroom Core running **locally under WSL2**, providing agent-terminal sessions, filesystem access, and browser panels. It does not document a hosted GPU job service.
- The saved base URL is `http://127.0.0.1:9840`; the WSL `Ubuntu` distro reports `cloudroom.service` active. Authenticated read-only probes returned HTTP 200 from `/v1/health` (`status: ready`) and `/v1/ready` (`ready: true`). These checks establish local Core readiness only.
- Connector discovery did not identify a Cloudroom connector. The connection-manager invocation returned `Unknown tool: manage_connections` in this execution environment. No hosted or MCP connection was added, and Hermes configuration was not changed.
- `backtest.py`, `pine_runner.py`, and `neural_label_collector.py` remain unchanged. No workload was submitted remotely. The neural label collector collects labels; a separate training entry point still needs identification before a training migration.

**Offload prerequisites:** identify the intended hosted compute service or supported MCP server, its endpoint and authentication method, job submission/status/cancellation interface, CPU/GPU runtimes, and artifact-return contract. Set explicit cost and latency limits with the operator; acceptable limits and measured remote cost/latency are not yet available. Keep MT5 access and order execution on their existing local path; move only bounded compute inputs/results once verified.

**Fallback:** existing local execution remains unchanged. Automatic remote-to-local failover is **not implemented or tested**. A future adapter must enforce bounded timeouts, prevent duplicate side effects after ambiguous submission failures, and verify fallback and artifact integrity before enabling scheduling.

## Troubleshooting

**Dashboard won't load** — confirm something is listening:
`netstat -ano | findstr :8490`. If not, start it with `hq start` (or `python cockpit.py`).

**The connect form appeared instead of auto-login** — the page's nonce expired or was consumed.
Reload locally, or paste the token from
**System → Dashboard credential** / `.cockpit-token`.

**"Session expired"** — sessions last 8 hours. Reload; auto-login re-establishes it. If it
persists, restart `cockpit.py` so it re-reads `.cockpit-token`.

**"Activity: Request failed"** — the event bus or server is unhealthy. Check
**System → Process & guard health**. Previously loaded data stays visible and is marked stale.

**Chart shows "MT5 candle data unavailable"** — the terminal/broker connection is down, or the
symbol name is wrong. The dashboard deliberately does not substitute synthetic candles.

**Market data marked stale** — inspect the source's timestamp/basis and its reason. Closed
markets or disconnection can explain old bars; broker epochs alone are not verified UTC
and must not be compared with local time to establish candle closure.

**Pine compile fails** — PineTS has varying Pine v5/v6 compatibility. The error is reported without
echoing your source. Try a registered strategy first to confirm the runtime itself is healthy.

**Everything looks empty but the connection says "Connected"** — check that MT5 is actually
attached. `Account: —` and "Position data unavailable" mean the broker snapshot could not be read,
not that the account is flat.

**Labels not growing** — `PYTHONPATH= C:/Users/voidk/miniconda3/python.exe neural_label_collector.py`
prints status. Check that the watchdog supervises `neural_label_collector.py watch`, not
status mode; pending labels need actual closes. HALT/PAUSE allow collection, STOP exits it.
Watch mode collects but does not automatically train at each pass.

**AI extraction unavailable** — regex parsing can still work. Provider/key/model/API transport
must agree. OAuth Hermes providers are not automatically usable by the standalone API-key
extractor; authentication, credits, model availability and network failures are separate
from a configured candidate. This refresh did not certify a live provider request.

**New API returns 404 despite source code** — the running cockpit can predate an edit. Ask
the service owner to reload/restart it after safe integration; do not start duplicate engines.

## What changed in this doc refresh

Preserved the six-view guide and added identity/label-health interpretation, closed-bar Pine
semantics, exact flag/lifecycle caveats, local-only auth and observed-vs-simulated data limits.

---

*Not in the left rail: `GET /api/mobile` returns a phone-sized HTML fragment of the same key data,
for embedding elsewhere.*

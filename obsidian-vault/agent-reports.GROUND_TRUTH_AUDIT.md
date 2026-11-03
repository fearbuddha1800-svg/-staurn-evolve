---
slug: agent-reports.GROUND_TRUTH_AUDIT
type: note
graph: gitnexus
---

# HERMES SCALP — Ground Truth Audit & Order-Send Inventory

**Compiled:** 2026-10-17 UTC · **Owner:** integration owner · **Mode:** observation (no trading changes made by this audit)

This is the evidence map the masterbook asks for first (§15 step 1). It records what
actually exists in the live checkout — not what historical transcripts claim.

## 1. Live checkout (verified this session)

Working dir: `C:/Users/voidk/.hermes/workspace/signal-relay/`
Python: `C:/Users/voidk/miniconda3/python.exe` (always prepend `PYTHONPATH=` to defeat the
shadow install env).

**Running processes (verified via lock-file PID + ctypes liveness + port probe):**

| Engine | Lock file | Port | Role |
|---|---|---|---|
| daemon.py | daemon.lock | — | Telegram source capture → parse → executor; console; news gate |
| manage.py | manage.lock | — | Protective BE +1R / 0.5R trail from +1.5R (magic 20261014 + 20261015) |
| strategy.py | strategy.lock | — | RSI-pullback algo, XAUUSD+EURUSD, magic 20261015 |
| strategy2_live.py | strategy2.lock | — | London-open breakout, XAUUSD, 0.5% risk, 1 entry/day, magic 20261015 |
| cockpit.py | (port probe) | :8490 | Read-only dashboard, 18 panels, 12 endpoints |
| trade-relay (node) | (port probe) | :8484 | LuxAlgo order audit rails |
| luxalgo-mcp (node) | (port probe) | :3333 | Local LuxAlgo ecosystem MCP |

**Account:** MT5 demo 5057394166 (MetaQuotes-Demo). Demo gate asserted in the entry path.

## 2. Order-send inventory — the real risk surface

Every site that can move money, classified entry (exposure-increasing) vs exit (exposure-reducing):

| # | File:line | Action | Class | Routes through shared authority? |
|---|---|---|---|---|
| 1 | `executor.py:313` | `TRADE_ACTION_DEAL` | **ENTRY** | ✅ IS the authority |
| 2 | `executor.py:307` | `TRADE_ACTION_PENDING` | **ENTRY** | ✅ IS the authority |
| 3 | `strategy.py:283` | `TRADE_ACTION_DEAL` | **ENTRY** | ❌ **own order_send — bypasses authority** |
| 4 | `strategy2_live.py:414` | `TRADE_ACTION_DEAL` | **ENTRY** | ❌ **own order_send — bypasses authority** |
| 5 | `executor.py:346` | `TRADE_ACTION_DEAL` (close) | exit | ✅ authority helper |
| 6 | `manage.py:150` | `TRADE_ACTION_SLTP` | exit (protective) | ⚠️ own send — protective, acceptable per §6 |
| 7 | `daemon.py:417` | `TRADE_ACTION_DEAL` (close ticket) | exit (owner console) | ⚠️ own send — owner-authorized exit, §12 |

**Verification-only modules** (no order path — `order_send` never called, documented in-file):
`channel_verify.py`, `channel_verify2.py`, `channel_verify3.py`, `channel_verify_mass.py`,
`channel_verify_scout.py`.

## 3. The defect (masterbook §4)

> "Every entry origin—Telegram, algorithm, Pine strategy, manual action, model proposal—must
> call it. Separate engines may propose decisions; they must not independently submit orders."

`strategy.py` and `strategy2_live.py` build their own MT5 requests and call `mt5.order_send`
directly. Consequences:

- **News gate skipped** — `executor.execute()` blocks entries inside High-USD news windows;
  the two algo engines do not consult it.
- **Dedupe / daily-cap skipped** — `_guards()` (duplicate msg_id, `max_trades_per_day`,
  `allowed_symbols`, max-open, free-margin) is not applied.
- **Symbol/volume/fill helpers duplicated** — drift risk between three copies of
  `_fill_type` / `_norm_volume` / stop validation.
- **No shared lineage** — algo fills are not written to the `trades` ledger by the same path
  as signal fills, so trace/edge-stats coverage is partial.

This is a *risk-control* defect, not a P&L claim. It does not mean the engines are unsafe —
they have their own sizing and SL — it means **there is no single account execution authority**,
which the masterbook makes the #1 integration requirement.

## 4. What is already correct

- Entry authority exists and is used by the Telegram path (`daemon.py:688` → `execute()`).
- `executor.execute()` carries: HALT check, dedupe, daily cap, symbol resolution,
  allowed-symbols, max-open, free-margin, news gate, SL requirement, stop validation,
  volume normalization, fill-type selection, ledger write, event-bus publish.
- Protective exits (BE/trail) are preserved and never widen a stop (`manage.py` verified).
- Telegram console is owner-locked (user id allowlist) and its close is by exact ticket.
- Demo-only gate is asserted on the live path.

## 5. Milestones (masterbook §15 order)

| # | Milestone | Status |
|---|---|---|
| 1 | Preserve + hash checkout; inventory order-send paths | ✅ this document |
| 2 | **One execution authority** — route algo entries through it | 🔨 dispatched |
| 3 | Durable source capture in observation mode | partial (daemon live; cursor recovery in scalp360) |
| 4 | Route parser/AI proposals through deterministic gates | partial (ai_extract validator exists) |
| 5 | Demo-only submission/reconciliation/native stops + lineage | partial (submission yes; reconciliation states no) |
| 6 | Truthful dashboard/Telegram read models | ✅ 18 panels, honest empty/stale states |
| 7 | Freeze + prospective economic evaluation | not started (needs labels) |
| 8 | Customer paper pilot | out of scope |

## 6. Known limitations (honest)

- No durable intent/reconciliation state machine (PROPOSED→RESERVED→SUBMITTING→ACK→FILLED→CLOSED);
  the ledger records outcomes, not the full broker state path.
- Reconciliation of ambiguous broker outcomes (10012/timeout) is not implemented.
- `trades` ledger `magic` column is used for per-engine attribution but lineage is not yet
  ticket→deal→position complete.
- Neural evaluation has 0 labels; the ≥300 gate correctly refuses to promote.
- Pine/PineTS parity is proven for one EMA strategy only — not universal Pine compatibility.


---
slug: agent-reports.guard-audit-current
type: note
graph: gitnexus
---

# Guard Wiring Audit — Current State

**Date:** 2026-10-18  
**Scope:** Read-only source audit of executor.py, manage.py, strategy.py, loss_halt.py, stop_legality.py

---

## Summary

| Guard | Entry Path (executor.py) | Trailing/BE Path (manage.py) | Status |
|-------|--------------------------|------------------------------|--------|
| `loss_halt.observe()` (daily loss latch) | ✅ `execute()` line 367, `execute_algo()` line 506 | ❌ Not called | **PARTIAL** |
| `stop_legality.assess_stop_change()` (SL preflight) | ✅ `sl_to_breakeven()` lines 634-644 | ❌ Not called in `_modify_sltp()` | **PARTIAL** |

---

## Verified Wiring (executor.py)

### 1. `loss_halt.observe()` — Daily Loss Latch

**File:** `executor.py`  
**Function:** `execute()` (Telegram/webhook signal path)  
**Lines:** 364-376

```python
try:
    lh = _loss_halt_instance(cfg)
    if lh is not None:
        lh_state = lh.observe(datetime.now(timezone.utc))
        if lh_state.get("halted"):
            result["detail"] = f"daily loss limit breached ({lh_state.get('loss')}/{lh_state.get('limit')}) - HALT latched"
            _record(result, parsed, 0)
            return result
except SafetyError as e:
    result["detail"] = f"loss guard unavailable: {e}"
    _record(result, parsed, 0)
    return result
```

**Function:** `execute_algo()` (Pine/algo strategy path)  
**Lines:** 503-515

```python
try:
    lh = _loss_halt_instance(cfg)
    if lh is not None:
        lh_state = lh.observe(datetime.now(timezone.utc))
        if lh_state.get("halted"):
            result["detail"] = f"daily loss limit breached ({lh_state.get('loss')}/{lh_state.get('limit')}) - HALT latched"
            _record(result, parsed, 0)
            return result
except SafetyError as e:
    result["detail"] = f"loss guard unavailable: {e}"
    _record(result, parsed, 0)
    return result
```

✅ **Both entry paths apply the daily loss latch before any order is sent.**

### 2. `stop_legality.assess_stop_change()` — SL Legality Preflight

**File:** `executor.py`  
**Function:** `sl_to_breakeven()` (used by daemon.handle_channel_update on TP hits)  
**Lines:** 631-644

```python
try:
    sd = assess_stop_change(
        mt5, position.symbol, "BUY" if is_buy else "SELL",
        cur_sl, new_sl, now=datetime.now(timezone.utc),
        ticket=position.ticket,
    )
    if not sd.allowed:
        return f"stop legality rejected: {sd.reason}"
    if sd.requires_widen_opt_in:
        return f"stop legality: WIDEN requires explicit opt-in ({sd.reason})"
except Exception as e:
    return f"stop guard unavailable: {type(e).__name__}: {e}"
```

✅ **Break-even moves from channel TP hits are preflighted.**

---

## Missing Wiring (manage.py)

### 1. `_modify_sltp()` — Core SL/TP Modification

**File:** `manage.py`  
**Function:** `_modify_sltp()`  
**Lines:** 147-151

```python
def _modify_sltp(position, new_sl, new_tp):
    req = {"action": mt5.TRADE_ACTION_SLTP, "symbol": position.symbol,
           "position": position.ticket, "sl": new_sl, "tp": new_tp}
    res = mt5.order_send(req)
    ...
```

❌ **NO `stop_legality.assess_stop_change()` call.** Direct `mt5.order_send()`.

### 2. Break-Even Logic (manage.py)

**File:** `manage.py`  
**Function:** `manage_position()` → `be_triggered` block  
**Lines:** 212-224

```python
if be_triggered:
    new_sl = round(entry_price + (buffer_points * point) if is_buy else entry_price - (buffer_points * point), digits)
    if (is_buy and cur_sl < new_sl) or (not is_buy and cur_sl > new_sl):
        _modify_sltp(pos, new_sl, pos.tp)
        ...
```

❌ **Break-even in manage.py bypasses `stop_legality`.** Calls `_modify_sltp()` directly.

### 3. Trailing Stop Logic (manage.py)

**File:** `manage.py`  
**Function:** `manage_position()` → trailing block  
**Lines:** 226-231

```python
if trail_points and trail_points > 0:
    new_sl = round(tick.bid - trail_points * point if is_buy else tick.ask + trail_points * point, digits)
    if (is_buy and cur_sl < new_sl) or (not is_buy and cur_sl > new_sl):
        _modify_sltp(pos, new_sl, pos.tp)
        ...
```

❌ **Trailing stops bypass `stop_legality`.** Calls `_modify_sltp()` directly.

---

## Strategy Path (strategy.py)

**File:** `strategy.py`  
**Function:** `run_strategy()` → entry logic  
**Lines:** 284-296

```python
if cfg.get("algo_entry_authority", True):
    exec_result = executor.execute_algo(...)
```

✅ **Algo entries route through `executor.execute_algo()`** which applies both guards.
⚠️ **Fallback:** If `algo_entry_authority=false`, direct `mt5.order_send()` (no guards).

---

## Guard Library Test Coverage

| Module | Tests | Status |
|--------|-------|--------|
| `test_loss_halt.py` | 18 tests | ✅ All pass |
| `test_stop_legality.py` | 24 tests | ✅ All pass |

Libraries are functionally correct and tested.

---

## Remaining High-Risk Issues

1. **`manage.py` break-even** — No `stop_legality` preflight (lines 212-224)
2. **`manage.py` trailing stops** — No `stop_legality` preflight (lines 226-231)
3. **`manage.py` `_modify_sltp()`** — No guard wrapper at all (lines 147-151)
4. **`strategy.py` fallback** — If `algo_entry_authority=false`, bypasses all guards

---

## Recommendation

Wire `stop_legality.assess_stop_change()` into `manage.py._modify_sltp()` as a preflight wrapper, and add `loss_halt.observe()` to `manage_position()` before any SL modification. This ensures **all** SL/TP modifications (whether from channel TP hits, break-even, or trailing) pass the legality check.


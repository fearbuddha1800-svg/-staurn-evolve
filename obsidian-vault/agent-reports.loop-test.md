---
slug: agent-reports.loop-test
type: note
graph: gitnexus
---

# End-to-end loop test: signal -> MT5 -> manage -> close -> ledger

- **When (local):** 2026-10-16 22:33:20
- **Account:** login=5057394166 server=MetaQuotes-Demo trade_mode=0 (0=demo) margin_mode=2 (0=netting, 1=exchange, 2=hedging) balance=99999.92 equity=100011.13
- **Channel policy:** channel_id -1002369502254 (sl_mode=atr, tp_mode=none, atr_mult=2.0)
- **Signal text:** '🟡 XAUUSD SIGNAL 🟡\nBUY NOW\nSL: 2650\nTP1: 2700\nTP2: 2750'
- **msg_id:** `looptest-1792204400`  |  **requested lot:** 0.01

## Stage results

| # | Stage | Status | Detail |
|---|-------|--------|--------|
| 0 | environment+demo gate | **PASS** | demo account, XAUUSD live, guards clear |
| 1 | parse_signal | **PASS** | {"is_signal": true, "parse_ok": true, "action": "buy", "order_type": "market", "symbol": "XAUUSD", "entry": "market", "sl": 2650.0, "tps": [2700.0, 2750.0]} |
| 2 | executor.execute REAL order | **FAIL** | status=broker_rejected ticket=0 fill=None lot=None sl=4154.25 detail=retcode 10018: Market closed |
| 6 | ledger row | **PASS** | row=(5, '2026-10-16 22:33:20', 'XAUUSD', 'buy', None, 'market', 4154.25, '[]', 'market', 0, 'broker_rejected', 'retcode 10018: Market closed') |

## Raw log

```
pre-flight: trade_allowed=True halt_file=False
pre-flight: account=login=5057394166 server=MetaQuotes-Demo trade_mode=0 (0=demo) margin_mode=2 (0=netting, 1=exchange, 2=hedging) balance=99999.92 equity=100011.13
pre-flight: symbol=XAUUSD bid=4168.77 ask=4169.24 point=0.01 digits=2 vol_min=0.01 stops_level=0
pre-flight: open positions total=4 (magic 20261014: 1, XAUUSD specifically: 1)
pre-flight: ledger non-skipped today=2 (cap 20)
[PASS] stage 0 environment+demo gate :: demo account, XAUUSD live, guards clear
parse result: {"is_signal": true, "parse_ok": true, "action": "buy", "order_type": "market", "symbol": "XAUUSD", "entry": "market", "sl": 2650.0, "tps": [2700.0, 2750.0]}
[PASS] stage 1 parse_signal :: {"is_signal": true, "parse_ok": true, "action": "buy", "order_type": "market", "symbol": "XAUUSD", "entry": "market", "sl": 2650.0, "tps": [2700.0, 2750.0]}
execute(): msg_id=looptest-1792204400 lot=0.01 channel_id=-1002369502254 policy={'sl_mode': 'atr', 'atr_mult': 2.0, 'tp_mode': 'none', 'note': 'Best Signal Forex - V2-B: +0.267R after costs'} (sl_mode=atr will REPLACE the parsed SL; tp_mode=none strips TPs)
execute() result: {"msg_id": "looptest-1792204400", "symbol": "XAUUSD", "resolved": "XAUUSD", "side": "buy", "entry": "market", "sl": 4154.25, "tp": [], "status": "broker_rejected", "ticket": 0, "detail": "retcode 10018: Market closed"}
[FAIL] stage 2 executor.execute REAL order :: status=broker_rejected ticket=0 fill=None lot=None sl=4154.25 detail=retcode 10018: Market closed
ledger rows for msg_id=looptest-1792204400: [(5, '2026-10-16 22:33:20', 'XAUUSD', 'buy', None, 'market', 4154.25, '[]', 'market', 0, 'broker_rejected', 'retcode 10018: Market closed')]
[PASS] stage 6 ledger row :: row=(5, '2026-10-16 22:33:20', 'XAUUSD', 'buy', None, 'market', 4154.25, '[]', 'market', 0, 'broker_rejected', 'retcode 10018: Market closed')
cleanup: nothing to close (no position was opened)
```

## Diagnosis

- Stage 2 failed: `retcode 10018: Market closed`. Channel policy={'sl_mode': 'atr', 'atr_mult': 2.0, 'tp_mode': 'none', 'note': 'Best Signal Forex - V2-B: +0.267R after costs'}. Retcode hint: market closed - XAUUSD session hours. Module to fix: whichever guard rejected it - executor.py (guards) or the MT5 terminal state itself.

## Cleanup: OK


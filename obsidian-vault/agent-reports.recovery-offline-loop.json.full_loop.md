---
slug: agent-reports.recovery-offline-loop.json.full_loop
type: note
graph: gitnexus
---

{
  "release": "0.2",
  "mode": "OFFLINE PAPER INTEGRATION",
  "data_origin": "SYNTHETIC TEST FIXTURES",
  "network_calls": 0,
  "broker_orders": 0,
  "passed": 12,
  "stages": [
    {
      "stage": "Paginated durable capture",
      "status": "PASS",
      "detail": "Original times preserved; fake source adapter."
    },
    {
      "stage": "Reject stale recovered entry",
      "status": "PASS",
      "detail": "signal timestamp outside freshness window"
    },
    {
      "stage": "Reject recap as entry",
      "status": "PASS",
      "detail": "historical outcome or result language"
    },
    {
      "stage": "Risk-gated simulated entry",
      "status": "PASS",
      "detail": "One simulated position opened."
    },
    {
      "stage": "Recover persistent position",
      "status": "PASS",
      "detail": "Entry, stop, fees and original risk persist."
    },
    {
      "stage": "Suppress replayed order",
      "status": "PASS",
      "detail": "No second position."
    },
    {
      "stage": "Defer illegal break-even",
      "status": "PASS",
      "detail": "Stop unchanged until geometry is legal."
    },
    {
      "stage": "Tighten legal stop",
      "status": "PASS",
      "detail": "Paper geometry verified; MT5 broker rules require preflight."
    },
    {
      "stage": "Telegram pause blocks entry",
      "status": "PASS",
      "detail": "Mocked transport; persistent shared halt is real."
    },
    {
      "stage": "Exit while entries paused",
      "status": "PASS",
      "detail": "Sell exit uses ask plus adverse slippage and fee."
    },
    {
      "stage": "Reconcile modeled net P&L",
      "status": "PASS",
      "detail": "Arithmetic check; synthetic outcome is not performance evidence."
    },
    {
      "stage": "Journal and outbox survive restart",
      "status": "PASS",
      "detail": "Acknowledgment cannot retrade. No Telegram delivery implied."
    }
  ],
  "snapshot": {
    "mode": "PAPER",
    "quote_source": "caller supplied; not a connected market feed",
    "utc_day": "2026-10-16",
    "open_positions": 0,
    "aggregate_open_risk": 0,
    "net_unrealized": 0,
    "net_realized": 19.799199999999274,
    "daily_cash_pnl": 19.799199999999274,
    "halts": [
      "operator pause via Telegram console"
    ]
  },
  "limitations": [
    "No live Telegram capture or delivery tested",
    "No Windows or MT5 connection tested",
    "No profitability or model edge tested"
  ]
}


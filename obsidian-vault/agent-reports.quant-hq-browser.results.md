---
slug: agent-reports.quant-hq-browser.results
type: note
graph: gitnexus
---

{
  "observed_at": "2026-10-18T08:04:11.022352+00:00",
  "checks": [
    {
      "name": "demo account scope",
      "passed": true,
      "detail": null
    },
    {
      "name": "real equity rendered",
      "passed": true,
      "detail": null
    },
    {
      "name": "real position count",
      "passed": true,
      "detail": null
    },
    {
      "name": "currency rendered",
      "passed": true,
      "detail": null
    },
    {
      "name": "chart rendered accessible description",
      "passed": true,
      "detail": null
    },
    {
      "name": "keyboard focus visible",
      "passed": true,
      "detail": null
    },
    {
      "name": "position table numeric sort",
      "passed": true,
      "detail": null
    },
    {
      "name": "real ticket evidence drawer",
      "passed": true,
      "detail": null
    },
    {
      "name": "drawer keyboard focus",
      "passed": true,
      "detail": null
    },
    {
      "name": "drawer escape closes and restores focus",
      "passed": true,
      "detail": null
    },
    {
      "name": "risk methodology expanded",
      "passed": true,
      "detail": null
    },
    {
      "name": "desktop no page-wide overflow",
      "passed": true,
      "detail": {
        "width": 1440,
        "scroll": 1440
      }
    },
    {
      "name": "desktop chart has usable size",
      "passed": true,
      "detail": null
    },
    {
      "name": "tablet no page-wide overflow",
      "passed": true,
      "detail": {
        "width": 820,
        "scroll": 820
      }
    },
    {
      "name": "tablet chart has usable size",
      "passed": true,
      "detail": null
    },
    {
      "name": "phone no page-wide overflow",
      "passed": true,
      "detail": {
        "width": 390,
        "scroll": 390
      }
    },
    {
      "name": "phone chart has usable size",
      "passed": true,
      "detail": null
    },
    {
      "name": "phone position summaries",
      "passed": true,
      "detail": null
    },
    {
      "name": "phone detail sheet",
      "passed": true,
      "detail": null
    },
    {
      "name": "Pine simulation disabled with explanation",
      "passed": true,
      "detail": null
    },
    {
      "name": "local source import works",
      "passed": true,
      "detail": null
    },
    {
      "name": "chart symbol selection uses real broker data",
      "passed": true,
      "detail": null
    },
    {
      "name": "Signals reachable",
      "passed": true,
      "detail": null
    },
    {
      "name": "System real contract rendered",
      "passed": true,
      "detail": null
    },
    {
      "name": "deployed source hq-tokens.css",
      "passed": true,
      "detail": null
    },
    {
      "name": "deployed source hq-shell.css",
      "passed": true,
      "detail": null
    },
    {
      "name": "deployed source quant-matrix.css",
      "passed": true,
      "detail": null
    },
    {
      "name": "deployed source quant-client.js",
      "passed": true,
      "detail": null
    },
    {
      "name": "deployed source quant.js",
      "passed": true,
      "detail": null
    },
    {
      "name": "deployed HTML equals reviewed template",
      "passed": true,
      "detail": null
    },
    {
      "name": "live read-only state",
      "passed": true,
      "detail": null
    },
    {
      "name": "live read-only events?limit=30&exclude=pnl_update",
      "passed": true,
      "detail": null
    },
    {
      "name": "live read-only quant",
      "passed": true,
      "detail": null
    },
    {
      "name": "live read-only health",
      "passed": true,
      "detail": null
    },
    {
      "name": "authenticated unknown API is 404",
      "passed": true,
      "detail": null
    },
    {
      "name": "live Pine fail-closed 503",
      "passed": true,
      "detail": null
    },
    {
      "name": "failure visible and not healthy",
      "passed": true,
      "detail": null
    },
    {
      "name": "stale observation visible",
      "passed": true,
      "detail": null
    },
    {
      "name": "confirmed empty differs from unavailable",
      "passed": true,
      "detail": null
    },
    {
      "name": "broker unavailability not zero",
      "passed": true,
      "detail": null
    },
    {
      "name": "logout revokes authenticated requests",
      "passed": true,
      "detail": null
    },
    {
      "name": "local reload auto-login recovers",
      "passed": true,
      "detail": null
    },
    {
      "name": "no JS page errors",
      "passed": true,
      "detail": []
    },
    {
      "name": "no unexpected console errors",
      "passed": true,
      "detail": []
    }
  ],
  "screenshots": [
    "C:\\Users\\voidk\\.hermes\\workspace\\signal-relay\\agent-reports\\quant-hq-browser\\desktop.png",
    "C:\\Users\\voidk\\.hermes\\workspace\\signal-relay\\agent-reports\\quant-hq-browser\\tablet.png",
    "C:\\Users\\voidk\\.hermes\\workspace\\signal-relay\\agent-reports\\quant-hq-browser\\phone.png"
  ],
  "console_errors": [],
  "page_errors": [],
  "fault_injection": "Browser routes only. Not production feeds.",
  "account_scope": {
    "login": 5057394166,
    "server": "MetaQuotes-Demo",
    "trade_mode": 0
  },
  "snapshot": {
    "observed_at": "2026-10-18T04:04:21.461905-04:00",
    "account": {
      "login": 5057394166,
      "server": "MetaQuotes-Demo",
      "trade_mode": 0,
      "currency": "USD",
      "type": "demo",
      "balance": 99999.92,
      "equity": 100011.13,
      "margin": 135.3,
      "free": 99875.83,
      "profit": 11.21
    },
    "mt5": {
      "available": true,
      "account_available": true,
      "positions_available": true
    },
    "day_pl": {
      "total": 0.0,
      "signals": 0.0,
      "algo": 0.0,
      "available": true,
      "units": "account_currency",
      "basis": "MT5 deals profit + commission + swap + fee; local calendar day"
    }
  },
  "passed": 44,
  "total": 44
}


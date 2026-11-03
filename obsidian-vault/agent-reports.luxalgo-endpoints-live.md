---
slug: agent-reports.luxalgo-endpoints-live
type: note
graph: gitnexus
---

[
  {
    "endpoint": "/api/luxalgo",
    "http": 200,
    "available": null,
    "preview": "{'services': {'trade-relay': {'port': 8484, 'up': True, 'desc': 'Order audit rails + risk limits (dashboard + API)'}, 'luxalgo-mcp': {'port': 3333, 'up': True, 'desc': 'Full local LuxAlgo MCP (library, edge-stats, trackers, prop-firm-sim, journal, brokers)'}}, 'library_repos': [{'name': 'PineTS', 'p"
  },
  {
    "endpoint": "/api/edge",
    "http": 200,
    "available": null,
    "preview": "{'channels': [], 'engines': [{'engine': 'algo', 'magic': 20261015, 'n': 0, 'wins': 0, 'losses': 0, 'win_rate': {'estimate': 0, 'lo': 0, 'hi': 0}, 'expectancy_r': 0.0, 'guards': {'low_sample': True, 'refused': True, 'warn_floor': 30, 'refuse_floor': 10}, 'stability': {'first_half': {'n': 0, 'k': 0, '"
  },
  {
    "endpoint": "/api/journal",
    "http": 200,
    "available": true,
    "preview": "{'available': True, 'events': [{'time': '2026-11-02T20:32:33.042425Z', 'event': 'engine_status', 'detail': '{\"observed_at\": \"2026-11-02T20:32:32.949085+00:00\", \"transport\": \"streamable-http\", \"provenance\": \"http://localhost:3333/mcp\", \"trackers\": {\"available\": false, \"reason\": \"explicit dataset miss"
  },
  {
    "endpoint": "/api/prop_sim",
    "http": 200,
    "available": false,
    "preview": "{'available': False, 'reason': 'Broker-backed simulation disabled in observational HQ; use an offline research artifact', 'broker': {'maintenance': False, 'halt': False, 'stop': False, 'pause': False, 'read_allowed': True, 'blocked_reason': 'not_attached: dashboard never initializes MT5', 'lifecycle"
  },
  {
    "endpoint": "/api/whale",
    "http": 200,
    "available": false,
    "preview": "{'package': 'whale-options', 'available': False, 'rows': [], 'source_url': 'http://127.0.0.1:8787', 'observed_at': '2026-11-02T20:33:21.657065+00:00', 'broker_orders_enabled': False, 'reason': 'Whale Options service unavailable (URLError); configure a market-data feed at localhost:8787'}"
  },
  {
    "endpoint": "/api/market_intel",
    "http": 200,
    "available": true,
    "preview": "{'rows': [{'id': 'senate:257795ae-e1b2-411d-b562-8fe4c2a4f2a1:0', 'chamber': 'senate', 'docId': '257795ae-e1b2-411d-b562-8fe4c2a4f2a1', 'rowIndex': 0, 'member': {'name': 'David H McCormick', 'bioguideId': 'M001243', 'party': 'Republican', 'state': 'PA'}, 'filedAt': '2026-08-27', 'transactedAt': '202"
  }
]


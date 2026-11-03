# Architecture diagrams

Editable local Excalidraw sources (open with Excalidraw File -> Open; do not upload sensitive workspace data):
* [System overview](system-overview.excalidraw)
* [Data flow](data-flow.excalidraw)
* [Deployment topology](deployment-topology.excalidraw)

Mermaid sequence sources (render in a Mermaid-capable editor):
* [Signal to trade](signal-to-trade.mmd)
* [Neural loop](neural-loop.mmd)
* [Guard evaluation](guard-evaluation.mmd)

These are logical, source-grounded views, not claims that every component is running. Render previews locally if needed; no service credentials, account identifiers or real message payloads are embedded. Entry guard and stop legality are separate responsibilities. External service manager configuration is authoritative for Node ports; only cockpit port 8490 is fixed here. Neural live promotion and HTTP Pine execution are explicitly unavailable.

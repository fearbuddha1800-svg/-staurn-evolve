---
slug: agent-reports.evolve-run
type: note
graph: gitnexus
---

# Evolution Run Summary

## Modules Built

- **mt5_comm** – MT5 communication layer
- **telegram_bot** – Telegram bot interface
- **signal_parser** – Signal parsing and tag extraction
- **manage_patch** – Patch management utility
- **test_manage_adoption** – Adoption testing suite
- **pine_bridge** – Pine Script data bridge
- **portfolio_selector** – Portfolio selection logic
- **executor** – Trade execution engine
- **cockpit UI** – User interface cockpit
- **integration test** – End‑to‑end integration test suite

## Risk Policy

- **Stop**: 2×ATR mandatory, no fixed take‑profit
- **Exit**: Trailing exits only; dynamic trail applied per signal

## Demo Account

- Pin: **123456** (demo placeholder)

## Live Broker Calls

- No live broker calls are made; all modules operate on demo / simulated data.

## Verification Checklist

- [ ] mt5_comm integration test passes
- [ ] telegram_bot responds with correct commands
- [ ] signal_parser extracts tags without errors
- [ ] manage_patch applies patches in dry‑run mode
- [ ] test_manage_adoption runs end‑to‑end
- [ ] pine_bridge bridges Pine Script data correctly
- [ ] portfolio_selector respects risk limits
- [ ] executor respects 2×ATR stop
- [ ] cockpit UI displays risk state accurately
- [ ] integration test completes without live broker calls


# Local Pine strategy registry

## Delivered

- `strategy_registry.py`: discovers direct `strategies/*.pine` files; exposes name, semantic version, Pine version, symbols, timeframe, parameters, canonical source SHA256, validation status and last-known-good revision. `start()` runs a stoppable content-hash watcher with real PineTS syntax compilation. Bad edits retain the last-known-good source; deletion unregisters the strategy.
- `tv_pine_import.py`: conservative TradingView text importer. Accepts Pine v5/v6, BOM/CRLF, a single Markdown Pine fence and tab-indented blocks (expanded to four spaces). Reads balanced multiline declarations/inputs, named/positional defaults and quoted commas. Does not silently rewrite unsupported TV libraries, multi-timeframe semantics or legacy Pine. Unknown constructs remain intact for PineTS validation. Non-four-space block source may need manual correction; arbitrary reindentation would corrupt Pine continuation semantics.
- Immutable local revision snapshots under `.cache/strategy-registry/<id>/<sha256>.pine`; validated SHA rollback. Explicit git semver tags use `strategy/<id>/v<version>`, only for already committed clean strategy files. No repository-wide staging, commits or tags were created during implementation; tag behavior was exercised in an isolated temporary git repository.
- Trusted local backtest chain: `StrategyRegistry.backtest()` → `pine_runner.backtest_strategy()` → `pinets_runner.run_pine_strategy()` → existing real Node/PineTS bridge. No order or signal-recording call. Results are atomically published for read-only dashboards with revision and observation timestamp.
- Authenticated read-only `/api/strategy_registry` endpoint. Metadata requests do not compile or attach MT5. Published results are marked stale after source changes.
- `cockpit_assets/strategy-registry.js`, included by the cockpit HTML and allowed by the asset boundary: strategy selector, explicit refresh, simulated equity/drawdown, observed timestamp, returned closed-trade tail and CLI backtest command. Uses DOM textContent, not source-derived HTML. Missing, failed or stale results never become invented performance.

## Safety blocker / not delivered

The current `cockpit_runtime.py` deliberately rejects `/api/pine_series` and `/api/pine/compile` with **503: credential-free OS-isolated worker not configured**. That boundary predates this change and remains intact. PineTS subprocess limits are not a hostile-script sandbox. Consequently:

- **No hot-reloaded `/api/pine_series` HTTP execution**: the local watcher and `source()` hot-reload are tested, but they do not bypass the HTTP execution gate.
- **No one-click HTTP backtest**: trusted local CLI integration works; the dashboard supplies the command rather than exposing an unsafe execution endpoint.
- **No live account equity or bar-by-bar equity curve**: the panel labels engine output as simulated, and the existing bridge returns at most the most recent 20 closed trades. It does not establish a complete trade tape or a live account feed.
- No service restart/deploy, live broker attachment or live-market performance verification was done. Existing running processes need the owner's normal redeploy procedure to load the new read-only route and assets.

Parent handoff flags should treat `hot_reload_working=false` for the full requested HTTP behavior, even though the filesystem watcher itself is verified. Registry/parser and trusted-local backtest integration are delivered. Dashboard panel is implemented; browser-rendered visual validation remains pending.

## Commands

Run from `C:/Users/voidk` (paths are module-relative thereafter):

```text
python .hermes/workspace/signal-relay/strategy_registry.py list
python .hermes/workspace/signal-relay/strategy_registry.py watch
python .hermes/workspace/signal-relay/strategy_registry.py import --id my_strategy --file C:/path/to/export.pine
python .hermes/workspace/signal-relay/strategy_registry.py backtest --id ema_cross --symbol XAUUSD --timeframe H1 --count 500
python .hermes/workspace/signal-relay/strategy_registry.py rollback --id my_strategy --revision FULL_SHA256
python .hermes/workspace/signal-relay/strategy_registry.py tag --id my_strategy
```

Import never overwrites an existing strategy unless `--overwrite` is explicitly supplied. Version annotations are independent of Pine language version:

```text
//@version=5
// @version 1.2.3
// @symbols XAUUSD, EURUSD
// @timeframe H1
```

Absent strategy-version annotations default to `0.1.0`; absent symbols/timeframe are unspecified rather than guessed.

## Verification

`python3 -m pytest C:/Users/voidk/.hermes/workspace/signal-relay/test_strategy_registry.py C:/Users/voidk/.hermes/workspace/signal-relay/test_cockpit_boundary_v2.py -q`

- 33 tests passed in the first combined run (12 new registry tests plus 21 existing boundary tests).
- New tests exercise actual local PineTS valid/invalid syntax, background watcher activation/error retention/recovery/deletion, transport/parser behavior, immutable rollback, explicit git tags, traversal rejection, authenticated metadata/staleness, canonical source hashing, and the registry→Python runner→real Node/PineTS chain.
- Runtime fixture uses explicitly synthetic candles and patched MT5 attachment/signal paths that fail if invoked. It is not historical market-performance evidence.
- `node --check .../cockpit_assets/strategy-registry.js` passed. Full browser rendering and one-click HTTP execution remain unverified/not enabled respectively.
- Existing `test_pine_runner.py` is an import-time script, not a unittest suite; its printed checks passed when imported but unittest reported zero discovered tests. Do not count those as an additional unittest total.

## Files changed

Created `strategy_registry.py`, `tv_pine_import.py`, `pine_compile_bridge.js`, `test_strategy_registry.py`, `cockpit_assets/strategy-registry.js`, and this document. Patched `pine_runner.py`, `cockpit_runtime.py` and `cockpit_ui.html` surgically. Other agents were editing cockpit files concurrently; their existing changes were not replaced.

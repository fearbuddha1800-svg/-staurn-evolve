# Documentation validation

Executed against the current workspace without starting trading components or changing operational flags:

* `python3 docs/validate_docs.py`: PASS — 31 API routes, 32 operations, 18 Markdown links, 3 Excalidraw drawings and 3 Mermaid sequences structurally checked.
* `uv run --no-project --with openapi-spec-validator python -c ...`: PASS — OpenAPI 3.1 document validated with openapi_spec_validator.validate. Validator dependencies were isolated in uv, not installed into the trading environment.
* `python3 -m unittest test_cockpit_boundary_v2`: PASS — 21 tests, 1.781 seconds, isolated real-HTTP fixtures with fake backend. No broker order calls or production startup.

Limitations: diagrams are editable sources with geometry/reference checks, not visually rendered/reviewed exports. Mermaid validation is structural, not an external renderer parse. Runbooks were checked against source; disruptive procedures (restart, re-auth, rotation, DB restore) were deliberately not exercised against production. Provider snapshots have extensible schemas rather than invented exhaustive external contracts. Runtime code changed concurrently during documentation work; route coverage was rechecked after adding the newly present strategy_registry route. Re-run the validator after future dispatch edits.

Notable contract corrections: neural.health and pine/series are not implemented aliases; use neural and pine_series. Pine HTTP execution remains fail-closed. Prop simulation is unavailable from observational HTTP. SSE is finite replay. Candles has a distinct unavailable response snapshot. Count-ready neural labels do not activate a live model.

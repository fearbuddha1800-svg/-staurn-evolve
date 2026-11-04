# Cloud desktop and engineering tools

Verified 2026-11-04 in this Cloudroom environment. These installations are in the
cloud, not on the user's computer, and are not automatically installed in new
Cloudroom sandboxes. No project dependency declaration was changed.

## Available

- Virtual desktop: `room-cli computer-use start`, display `:99`.
- Chromium and `browser-harness`: a browser button was clicked through CDP and
  its changed text verified. A native window screenshot was also returned.
  The test tab was closed.
- RTK 0.30.0: built locally from its tagged MIT source because prebuilt ARM64
  binaries require GLIBC 2.39; this environment has GLIBC 2.36.
- GitNexus 1.6.12: installed with a dedicated Node 22.23.4 runtime.
- `python`: Python 3.11.2 in an isolated environment with pip, pytest, PyYAML,
  Telethon, Pillow, and NumPy. This is not the user's configured Windows Python.
- Ruff 0.17.3. Hermes Agent 0.21.6 was already installed; version/help inspected
  only. Its model, gateway, credentials, and provider configuration were not changed.

Commands live in `~/.local/bin`. Stable tool files and the Python environment live
under `~/.local/share/quant-toolchain`. Rust was installed under `~/.cargo` to build
RTK, without changing shell startup files. Node 24 remains the system default;
the GitNexus wrapper invokes Node 22 explicitly.

The GitNexus wrapper defaults to two parsing workers, one parse chunk, and a
768 MiB database buffer. The default 256 MiB buffer failed on this checkout.
Overrides can be supplied with GitNexus's corresponding environment variables.

## Verification

```sh
rtk --version
rtk proxy gitnexus status
rtk proxy python -m pip check
rtk proxy python -m pytest tools/test_ea_readiness.py mql5-training/offline_tests -q
rtk proxy ruff check tools/ea_readiness.py tools/test_ea_readiness.py mql5-training/offline_pipeline.py mql5-training/offline_tests
```

The dependency check succeeded; all 12 tests and Ruff passed. GitNexus indexed
6,512 nodes, 13,190 edges, 268 clusters and 515 flows. Its content/status check
reported current. The registered repository alias is `staurn-evolve`, located at
`/code/Personal`; the old instructions advertise `signal-relay`.

Graph completeness is limited: analysis reported capped process traversal and
unresolved cross-language fields. `impact OnTick` returned UNKNOWN/target missing;
this does not establish safety for MQL5 edits. A file-qualified impact query for
`mql5-training/offline_pipeline.py:validate` returned LOW with `build`, `main`,
and the containing file upstream. No absence of graph results should be treated
as proof that a symbol is unused.

## Still requires the user's computer

Cloudroom reports computer access is turned off. Enable it in Cloudroom to reach
the existing local MT5 terminal and Hermes installation. A cloud desktop does not
grant access to the user's desktop or existing browser logins.

`pip install --dry-run MetaTrader5` returned no matching distribution on Linux
ARM64. The native MT5 Python bridge and MetaEditor were not installed or tested.
No brokerage login, model training, Telegram message, or trade was performed.

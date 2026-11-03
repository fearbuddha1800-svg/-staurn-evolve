---
slug: agent-reports.recovery-baseline.results
type: note
graph: gitnexus
---

{
  "at": "2026-10-17T15:00:42.588130+00:00",
  "phase": "baseline",
  "scope": "explicit isolated tests; live test_loop.py excluded",
  "suites": [
    {
      "file": "test_suite.py",
      "mode": "acceptance-script",
      "exit_code": 1,
      "elapsed_s": 0.679,
      "log": "C:\\Users\\voidk\\.hermes\\workspace\\signal-relay\\agent-reports\\recovery-baseline\\test_suite.py.log",
      "tail": [
        "FAIL N5 execute() -> skipped_news_window for event 2min out: AttributeError: 'EventBus' object has no attribute 'intelligence_history'",
        "FAIL N6 execute() normal flow for event 2h out: AttributeError: 'EventBus' object has no attribute 'intelligence_history'",
        "",
        "2 FAILURE(S)",
        ""
      ]
    },
    {
      "file": "test_console.py",
      "mode": "acceptance-script",
      "exit_code": 0,
      "elapsed_s": 0.512,
      "log": "C:\\Users\\voidk\\.hermes\\workspace\\signal-relay\\agent-reports\\recovery-baseline\\test_console.py.log",
      "tail": [
        "PASS stranger DM got no reply",
        "PASS channel message not consumed",
        "",
        "ALL PASS",
        ""
      ]
    },
    {
      "file": "test_entry_authority.py",
      "mode": "acceptance-script",
      "exit_code": 0,
      "elapsed_s": 0.47,
      "log": "C:\\Users\\voidk\\.hermes\\workspace\\signal-relay\\agent-reports\\recovery-baseline\\test_entry_authority.py.log",
      "tail": [
        "",
        "----------------------------------------------------------------------",
        "Ran 8 tests in 0.014s",
        "",
        "OK"
      ]
    },
    {
      "file": "test_strategy2_live.py",
      "mode": "acceptance-script",
      "exit_code": 0,
      "elapsed_s": 0.297,
      "log": "C:\\Users\\voidk\\.hermes\\workspace\\signal-relay\\agent-reports\\recovery-baseline\\test_strategy2_live.py.log",
      "tail": [
        "PASS SL geometry: opposite edge vs 1.5*ATR cap",
        "PASS config.json strategy2 block matches spec",
        "",
        "ALL PASS",
        ""
      ]
    },
    {
      "file": "test_pine_runner.py",
      "mode": "acceptance-script",
      "exit_code": 0,
      "elapsed_s": 0.148,
      "log": "C:\\Users\\voidk\\.hermes\\workspace\\signal-relay\\agent-reports\\recovery-baseline\\test_pine_runner.py.log",
      "tail": [
        "PASS msg_id format pine_<name>_<ts> msg_id='pine_ema_cross_20261017T150041Z'",
        "PASS dry run: no MT5 order path (executor never imported) pine_runner imports only pinets_runner + stdlib; record_signal is a pure INSERT",
        "",
        "All 4 tests passed \u2014 dry run, no MT5 order.",
        ""
      ]
    },
    {
      "file": "test_neural_collector.py",
      "mode": "acceptance-script",
      "exit_code": 0,
      "elapsed_s": 0.682,
      "log": "C:\\Users\\voidk\\.hermes\\workspace\\signal-relay\\agent-reports\\recovery-baseline\\test_neural_collector.py.log",
      "tail": [
        "  DECISION: REJECT: insufficient labels (3 < 300)",
        "PASS evaluation refuses to promote on <300 labels - decision=None",
        "",
        "13 passed, 0 failed",
        ""
      ]
    },
    {
      "file": "test_edge_stats_bridge.py",
      "mode": "acceptance-script",
      "exit_code": 0,
      "elapsed_s": 0.307,
      "log": "C:\\Users\\voidk\\.hermes\\workspace\\signal-relay\\agent-reports\\recovery-baseline\\test_edge_stats_bridge.py.log",
      "tail": [
        "PASS test_channel_stats_structure",
        "PASS test_engine_stats_structure",
        "",
        "ALL TESTS PASSED",
        ""
      ]
    },
    {
      "file": "test_prop_sim_bridge.py",
      "mode": "acceptance-script",
      "exit_code": 0,
      "elapsed_s": 0.332,
      "log": "C:\\Users\\voidk\\.hermes\\workspace\\signal-relay\\agent-reports\\recovery-baseline\\test_prop_sim_bridge.py.log",
      "tail": [
        "All tests passed!",
        "",
        "Warning: Failed to compute optimal risk: Seed 42 not found in script",
        "Warning: Failed to compute optimal risk: Seed 42 not found in script"
      ]
    },
    {
      "file": "test_market_intel_bridge.py",
      "mode": "acceptance-script",
      "exit_code": 0,
      "elapsed_s": 0.279,
      "log": "C:\\Users\\voidk\\.hermes\\workspace\\signal-relay\\agent-reports\\recovery-baseline\\test_market_intel_bridge.py.log",
      "tail": [
        ".......",
        "----------------------------------------------------------------------",
        "Ran 7 tests in 0.030s",
        "",
        "OK"
      ]
    }
  ],
  "suite_total": 9,
  "suite_passed": 8,
  "syntax_errors": [
    {
      "file": "cockpit.py",
      "error": "invalid decimal literal (cockpit.py, line 790)"
    }
  ]
}


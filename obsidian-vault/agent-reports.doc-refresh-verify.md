---
slug: agent-reports.doc-refresh-verify
type: note
graph: gitnexus
---

"""Explicit safe documentation verification; never discover test_loop.py."""
import os
from pathlib import Path
import subprocess
import json
import sys

BASE = Path(__file__).resolve().parents[1]
PYTEST = ['test_cockpit_api.py', 'test_cockpit_contracts.py', 'test_cockpit_new_features.py',
          'test_quant_analytics.py', 'test_research_contracts.py', 'test_intelligence_integration.py',
          'test_reconciliation.py', 'test_strategy_identity.py', 'test_bar_parity.py',
          'test_model_router.py', 'test_label_health.py', 'test_ai_router_integration.py',
          'test_watchdog_recovery.py', 'test_ai_provider_selection.py',
          'test_loss_halt.py', 'test_portfolio_risk.py', 'test_stop_legality.py',
          'test_prop_sim_real_data.py', 'test_real_data_views.py']
RUNNERS = ['test_suite.py', 'test_neural_collector.py', 'test_pine_runner.py',
           'test_strategy2_live.py', 'test_edge_stats_bridge.py', 'test_prop_sim_bridge.py',
           'test_market_intel_bridge.py', 'test_entry_authority.py', 'test_console.py']
env = dict(os.environ, PYTHONPATH='', PYTHONIOENCODING='utf-8')
results = []
for name, args in [('pytest', ['-m', 'pytest', *PYTEST, '-q', '-rA'])] + [(n, [n]) for n in RUNNERS]:
    result = subprocess.run([sys.executable, *args], cwd=BASE, env=env,
                            capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
    output = result.stdout + result.stderr
    (BASE / 'agent-reports' / ('doc-refresh-' + name + '.log')).write_text(output, encoding='utf-8')
    results.append({'suite': name, 'exit_code': result.returncode, 'output': output})
    print(name, 'exit', result.returncode, '\n', output[-3000:], flush=True)
(BASE / 'agent-reports' / 'doc-refresh-tests.json').write_text(json.dumps(results, indent=2), encoding='utf-8')


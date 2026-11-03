---
slug: verify_recovery
type: note
graph: gitnexus
---

"""Explicit, isolated regression runner. Never discovers test_loop.py (live orders).

Run with the project's Python: python verify_recovery.py --phase baseline|final.
Existing acceptance scripts run separately because some install module-wide stubs.
New pytest suites are likewise isolated. Logs and machine-readable counts are saved.
"""
from __future__ import annotations

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
SCRIPTS = [
    'test_suite.py', 'test_console.py', 'test_entry_authority.py',
    'test_strategy2_live.py', 'test_pine_runner.py', 'test_neural_collector.py',
    'test_edge_stats_bridge.py', 'test_prop_sim_bridge.py', 'test_market_intel_bridge.py',
]
PYTESTS = [
    'test_cockpit_api.py', 'test_luxalgo_orchestrator.py',
    'test_intelligence_integration.py', 'test_research_contracts.py',
    'test_watchdog_recovery.py',
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=['baseline', 'final'], default='final')
    args = parser.parse_args()
    out = ROOT / 'agent-reports' / ('recovery-' + args.phase)
    out.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.pop('PYTHONPATH', None)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    jobs = [(name, False) for name in SCRIPTS]
    jobs += [(name, True) for name in PYTESTS if (ROOT / name).is_file()]

    def run(job):
        name, pytest = job
        argv = [sys.executable]
        if pytest:
            argv += ['-m', 'pytest', name, '-q', '--tb=short',
                     '--junitxml=' + str(out / (name + '.xml'))]
        else:
            argv += [name]
        start = time.monotonic()
        try:
            result = subprocess.run(argv, cwd=ROOT, env=env, capture_output=True,
                                    encoding='utf-8', errors='replace', timeout=180)
            code, text = result.returncode, result.stdout + '\n' + result.stderr
        except subprocess.TimeoutExpired as exc:
            code, text = 124, 'TIMEOUT\n' + str(exc)
        (out / (name + '.log')).write_text(text, encoding='utf-8')
        return {'file': name, 'mode': 'pytest' if pytest else 'acceptance-script',
                'exit_code': code, 'elapsed_s': round(time.monotonic()-start, 3),
                'log': str(out / (name + '.log')), 'tail': text.splitlines()[-5:]}

    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(run, jobs))
    syntax = []
    for file in sorted(ROOT.glob('*.py')):
        try:
            ast.parse(file.read_text(encoding='utf-8-sig'), filename=str(file))
        except (SyntaxError, UnicodeError) as exc:
            syntax.append({'file': file.name, 'error': str(exc)})
    report = {'at': datetime.now(timezone.utc).isoformat(), 'phase': args.phase,
              'scope': 'explicit isolated tests; live test_loop.py excluded',
              'suites': results, 'suite_total': len(results),
              'suite_passed': sum(r['exit_code'] == 0 for r in results),
              'syntax_errors': syntax}
    target = out / 'results.json'
    target.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    print('REPORT:', target)
    return 0 if not syntax and all(r['exit_code'] == 0 for r in results) else 1


if __name__ == '__main__':
    sys.exit(main())


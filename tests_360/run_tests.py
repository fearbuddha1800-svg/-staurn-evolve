#!/usr/bin/env python3
"""Zero-dependency test runner. Usage: python tests/run_tests_360.py [-v]"""
import sys, pathlib, traceback
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import importlib

SUITES = ["tests_360.test_gold_parser", "tests_360.test_risk", "tests_360.test_cursor",
          "tests_360.test_lineage", "tests_360.test_executor", "tests_360.test_console",
          "tests_360.test_ai_neural", "tests_360.test_event_bus"]

def main() -> int:
    verbose = "-v" in sys.argv
    total = failed = 0
    for name in SUITES:
        mod = importlib.import_module(name)
        for attr in sorted(dir(mod)):
            if not attr.startswith("test_"):
                continue
            total += 1
            try:
                getattr(mod, attr)()
                if verbose: print(f"  PASS {name}.{attr}")
            except Exception:
                failed += 1
                print(f"  FAIL {name}.{attr}")
                traceback.print_exc()
    print(f"\n{total-failed}/{total} tests passed")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())

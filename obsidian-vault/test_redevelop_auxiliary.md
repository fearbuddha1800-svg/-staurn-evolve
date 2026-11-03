---
slug: test_redevelop_auxiliary
type: note
graph: gitnexus
---

"""Offline structural and injected-adapter regressions; never import MT5."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

BASE = Path(__file__).resolve().parent
EXPLICIT = ('backtest.py', 'channel_verify.py', 'channel_verify2.py',
            'channel_verify3.py', 'channel_verify_mass.py',
            'channel_verify_scout.py', 'pinets_runner.py', 'report.py', 'status.py')
OBSERVERS = ('mobile_view.py', 'prop_sim_bridge.py', 'quant_analytics.py')


def load_functions(name, names, namespace):
    tree = ast.parse((BASE / name).read_text(encoding='utf-8-sig'))
    functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names]
    assert len(functions) == len(names)
    exec(compile(ast.Module(body=functions, type_ignores=[]), name, 'exec'), namespace)
    return namespace


class AuxiliaryTests(unittest.TestCase):
    def test_no_direct_initialize_in_covered_utilities(self):
        for name in EXPLICIT + OBSERVERS:
            with self.subTest(file=name):
                tree = ast.parse((BASE / name).read_text(encoding='utf-8-sig'))
                self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Call)
                    and isinstance(n.func, ast.Attribute) and n.func.attr == 'initialize'])
                if name in EXPLICIT:
                    self.assertTrue(any(isinstance(n, ast.ImportFrom)
                        and n.module == 'broker_lifecycle'
                        and any(a.name == 'initialize_existing' for a in n.names)
                        for n in tree.body))

    def test_mobile_disconnected_is_unknown_without_reconnect(self):
        forbidden = Mock(side_effect=AssertionError('no connection or broker query'))
        broker = SimpleNamespace(terminal_info=lambda: None, initialize=forbidden,
                                 account_info=forbidden, positions_get=forbidden)
        namespace = load_functions('mobile_view.py', {'_account', '_positions'},
                                   {'_mt5': lambda: broker})
        self.assertIsNone(namespace['_account']())
        self.assertIsNone(namespace['_positions']())
        forbidden.assert_not_called()

    def test_prop_snapshot_never_attaches(self):
        tree = ast.parse((BASE / 'prop_sim_bridge.py').read_text())
        func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_broker')
        self.assertFalse(any(isinstance(n, ast.Attribute) and n.attr == 'initialize'
                             for n in ast.walk(func)))

    def test_quant_disconnected_does_not_initialize(self):
        # Pure analytics module imports no execution/broker modules.
        from quant_analytics import quant_snapshot
        forbidden = Mock(side_effect=AssertionError('no initialization'))
        backend = SimpleNamespace(candles_data=lambda *a: {'error': 'unavailable'},
            mt5=SimpleNamespace(terminal_info=lambda: None, initialize=forbidden))
        result = quant_snapshot(backend)
        self.assertFalse(result['available'])
        self.assertFalse(result['broker_orders_enabled'])
        forbidden.assert_not_called()


if __name__ == '__main__':
    unittest.main()


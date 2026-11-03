---
slug: test_evolve_entry_contract
type: note
graph: gitnexus
---

"""AST-only regressions: never import daemon/executor or attach to broker."""
import ast
import inspect
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).parent

def tree(name):
    return ast.parse((ROOT / name).read_text(encoding='utf-8-sig'))

def function(name):
    return next(n for n in tree('executor.py').body if isinstance(n, ast.FunctionDef) and n.name == name)

def test_daemon_execute_keywords_match_signature_and_trace_is_preserved():
    node = function('execute')
    args = node.args.args
    signature = inspect.Signature([inspect.Parameter(a.arg, inspect.Parameter.POSITIONAL_OR_KEYWORD,
        default=inspect.Parameter.empty if i < len(args)-len(node.args.defaults) else None)
        for i,a in enumerate(args)])
    calls = [n for n in ast.walk(tree('daemon.py')) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == 'execute']
    assert calls
    for call in calls:
        keywords = {k.arg: None for k in call.keywords}
        signature.bind(*([None]*len(call.args)), **keywords)
        assert 'trace_id' not in keywords
    assignments = [n for n in ast.walk(node) if isinstance(n, ast.Assign)
                   and any(isinstance(t, ast.Name) and t.id == 'trace_id' for t in n.targets)]
    assert any('str(msg_id)' in ast.unparse(n.value) for n in assignments)


def run_be(config, allowed=False, widen=False, buy=True):
    sent, observed = [], []
    def guard(*args, **kwargs):
        observed.append(kwargs)
        return SimpleNamespace(allowed=allowed, reason='stub guard', requires_widen_opt_in=widen)
    mt5 = SimpleNamespace(POSITION_TYPE_BUY=0, TRADE_ACTION_SLTP=6, TRADE_RETCODE_DONE=10009,
        symbol_info=lambda s: SimpleNamespace(point=0.00001,digits=5,trade_stops_level=0),
        symbol_info_tick=lambda s: SimpleNamespace(bid=1.2,ask=1.2001),
        order_send=lambda req: sent.append(req) or SimpleNamespace(retcode=10009),
        last_error=lambda: (0,'stub'))
    ns = dict(mt5=mt5, load_config=lambda: config, assess_stop_change=guard,
              datetime=datetime, timezone=timezone)
    mod = ast.fix_missing_locations(ast.Module(body=[function('sl_to_breakeven')],type_ignores=[]))
    exec(compile(mod,'<isolated BE>','exec'),ns)
    p = SimpleNamespace(type=0 if buy else 1,price_open=1.1 if buy else 1.3,sl=0,
                        symbol='OFFLINE-FIXTURE',ticket=123,tp=0)
    result = ns['sl_to_breakeven'](p)
    return result, observed, sent

@pytest.mark.parametrize('offset',[10800,-10800,0,True,123])
@pytest.mark.parametrize('buy',[True,False])
def test_explicit_offset_reaches_guard_unchanged_and_denial_never_sends(offset,buy):
    result, observed, sent = run_be({'manage':{'broker_utc_offset_s':offset}},buy=buy)
    assert observed[0]['broker_utc_offset_s'] == offset
    assert type(observed[0]['broker_utc_offset_s']) is type(offset)
    assert observed[0]['ticket'] == 123
    assert result.startswith('stop legality rejected:')
    assert sent == []

@pytest.mark.parametrize('config',[{}, {'manage':{} }])
def test_default_offset_is_zero(config):
    _, observed, sent = run_be(config)
    assert observed[0]['broker_utc_offset_s'] == 0
    assert sent == []

@pytest.mark.parametrize('config',[None, {'manage':None}, {'manage':[]}])
def test_malformed_config_fails_closed(config):
    result, observed, sent = run_be(config)
    assert result.startswith('stop guard unavailable:')
    assert not observed and not sent

def test_widen_opt_in_remains_fail_closed():
    result, observed, sent = run_be({'manage':{'broker_utc_offset_s':10800}},allowed=True,widen=True)
    assert 'WIDEN requires explicit opt-in' in result
    assert observed and not sent


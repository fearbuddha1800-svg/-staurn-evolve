"""Observed-input-only bridge to LuxAlgo's model-derived Monte Carlo engine."""
from __future__ import annotations
import json
import math
from pathlib import Path
from contextlib import closing
import sqlite3
import subprocess
import sys
import urllib.request

BASE = Path(__file__).resolve().parent
DB = BASE / 'signals.db'
CORE = BASE.parent / 'luxalgo/prop-firm-sim/packages/core/dist'
DIRECTORY_URL = 'https://app.luxalgo.com/api/propfirms/list'
DEFAULT_SEED = 42
MIN_TRADES_FOR_STATS = 10


def _finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{name} unavailable: finite numeric value required')
    return float(value)


def _fetch_prop_firm_list():
    try:
        with urllib.request.urlopen(DIRECTORY_URL, timeout=30) as response:
            data = json.loads(response.read().decode())['data']
        # Public endpoint currently wraps rows in data.propfirms; older responses used data directly.
        if isinstance(data, dict):
            data = data.get('propfirms')
        if not isinstance(data, list) or not all(isinstance(f, dict) for f in data):
            raise ValueError('invalid directory payload')
        return data
    except Exception as exc:
        raise ValueError(f'Prop-firm directory unavailable ({type(exc).__name__})') from exc


def _find_firm(firm_id, challenge_id):
    for firm in _fetch_prop_firm_list():
        if firm.get('propfirmId') == firm_id and any(c.get('challengeId') == challenge_id for c in firm.get('challenges', [])):
            return firm
    return None


def _find_challenge_spec(firm_id, challenge_id):
    firm = _find_firm(firm_id, challenge_id)
    return next((c for c in firm['challenges'] if c.get('challengeId') == challenge_id), None) if firm else None


def _broker():
    try:
        import MetaTrader5 as mt5
        if mt5.terminal_info() is None:
            # Observation must never create or retry a broker connection.
            raise ValueError('broker attachment unavailable; explicit connection required')
        return mt5
    except Exception as exc:
        raise ValueError(f'Broker history unavailable ({type(exc).__name__})') from exc


def _observed_trades(db_path=None, broker=None):
    """Validate complete single-entry positions against immutable ledger SL.

    Gross price R avoids misusing today's currency tick value as historical
    original risk. Costs are excluded explicitly, never fabricated. No DB write.
    """
    path = Path(db_path) if db_path is not None else DB
    try:
        with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=2)) as con:
            rows = con.execute("SELECT ticket,symbol,side,sl FROM trades WHERE status IN ('executed','closed') AND ticket IS NOT NULL").fetchall()
    except Exception as exc:
        raise ValueError(f'Observed trade database unavailable ({type(exc).__name__})') from exc
    m = broker if broker is not None else _broker()
    try:
        positions = m.positions_get()
    except Exception as exc:
        raise ValueError('Broker open-position state unavailable') from exc
    if positions is None:
        raise ValueError('Broker open-position state unavailable')
    active = {int(p.identifier) for p in positions}
    accepted, rejected, seen = [], [], set()
    for ticket, symbol, side, sl in rows:
        try:
            if ticket in seen:
                continue
            seen.add(ticket)
            stop = _finite(sl, 'original stop')
            if stop <= 0 or side not in ('buy','sell'):
                raise ValueError('original stop/side invalid')
            orders = m.history_orders_get(ticket=int(ticket))
            if orders is None or len(orders) != 1:
                raise ValueError('initial order unavailable')
            order = orders[0]
            if order.symbol != symbol or not math.isclose(_finite(order.sl, 'order stop'),stop,rel_tol=1e-9):
                raise ValueError('original stop provenance mismatch')
            pid = int(order.position_id)
            if pid <= 0 or pid in active:
                raise ValueError('position not confirmed closed')
            deals = m.history_deals_get(position=pid)
            if not deals or any(d.symbol != symbol or int(d.position_id) != pid for d in deals):
                raise ValueError('history unavailable/mismatched')
            ins = [d for d in deals if d.entry == m.DEAL_ENTRY_IN]
            outs = [d for d in deals if d.entry in (m.DEAL_ENTRY_OUT,m.DEAL_ENTRY_OUT_BY)]
            if len(ins) != 1 or not outs or len(ins)+len(outs) != len(deals):
                raise ValueError('complex/incomplete round trip')
            entry = ins[0]
            expected = m.DEAL_TYPE_BUY if side == 'buy' else m.DEAL_TYPE_SELL
            if entry.order != int(ticket) or entry.type != expected:
                raise ValueError('entry order/side mismatch')
            price, volume = _finite(entry.price,'fill price'), _finite(entry.volume,'entry volume')
            if price <= 0 or volume <= 0 or (price-stop)*(1 if side=='buy' else -1) <= 0:
                raise ValueError('invalid original risk geometry')
            out_volume = sum(_finite(d.volume,'exit volume') for d in outs)
            if any(d.volume <= 0 or d.type == expected for d in outs) or not math.isclose(out_volume,volume,rel_tol=1e-8):
                raise ValueError('position not completely closed')
            exit_price = sum(_finite(d.price,'exit price')*d.volume for d in outs)/volume
            opened = _finite(entry.time,'entry timestamp')
            closed = max(_finite(d.time,'close timestamp') for d in outs)
            if opened <= 0 or closed < opened or any(d.time < opened or d.price <= 0 for d in outs):
                raise ValueError('invalid timestamps/prices')
            r = (exit_price-price)*(1 if side=='buy' else -1)/abs(price-stop)
            accepted.append({'r':_finite(r,'R'),'opened_at':opened,'closed_at':closed,
                             'ticket':int(ticket),'position_id':pid,
                             'source':'signals.db executed SL + MT5 initial order and closed deals',
                             'risk_basis':'original stop distance; gross price R excluding monetary costs'})
        except (ValueError,TypeError,AttributeError,OverflowError) as exc:
            rejected.append({'ticket':ticket,'reason':str(exc)})
    return {'trades':sorted(accepted,key=lambda t:(t['opened_at'],t['ticket'])),
            'rejected':rejected,'ledger_rows':len(rows),'data_source':'signals.db+MT5'}


def _get_r_multiples_from_db():
    return [t['r'] for t in _observed_trades()['trades']]


def _compute_trader_stats(values):
    values = [_finite(r,'R') for r in values]
    wins, losses = [r for r in values if r>0], [r for r in values if r<0]
    if not wins or not losses:
        raise ValueError('Trader statistics unavailable: both wins and losses required')
    return len(wins)/len(values),sum(wins)/len(wins),-sum(losses)/len(losses)


def _cadence(trades):
    starts = [_finite(t['opened_at'],'entry timestamp') for t in trades]
    ends = [_finite(t['closed_at'],'close timestamp') for t in trades]
    if not starts or min(starts)<=0 or any(b<a for a,b in zip(starts,ends)):
        raise ValueError('Trade cadence unavailable')
    first,last = min(starts),max(ends)
    days = int(last//86400-first//86400)+1
    return {'trades_per_day':len(trades)/days,'denominator_days':days,
            'window_start_epoch':first,'window_end_epoch':last,'numerator_closed_positions':len(trades),
            'definition':'inclusive broker-epoch calendar days from first accepted entry to last accepted close, including zero-entry days',
            'limitation':'validated closed subset only; epoch timezone not inferred; calendar-day rate used as simulated trading-day proxy'}


def _run_node_script(script):
    try:
        result = subprocess.run(['node','--input-type=module','-'],input=script,capture_output=True,text=True,check=True,timeout=180)
        data = json.loads(result.stdout)
    except Exception as exc:
        raise ValueError(f'Local Monte Carlo engine unavailable ({type(exc).__name__})') from exc
    if not isinstance(data,dict):
        raise ValueError('Simulation output unavailable')
    return data


def _build_node_script(spec,profile,options):
    return (f'import {{simulate}} from {json.dumps((CORE/"index.js").as_uri())};\n'
            f'console.log(JSON.stringify(simulate({json.dumps(spec,allow_nan=False)},'
            f'{json.dumps(profile,allow_nan=False)},{json.dumps(options,allow_nan=False)})));\n')


def _get_optimal_risk(spec,profile):
    script = (f'import {{optimalRisk}} from {json.dumps((CORE/"index.js").as_uri())};\n'
              f'console.log(JSON.stringify(optimalRisk({json.dumps(spec,allow_nan=False)},'
              f'{json.dumps(profile,allow_nan=False)},{{paths:1000,seed:42}})));\n')
    result = _run_node_script(script)
    try:
        return _finite(result['bestByEv']['risk'],'optimal risk')
    except (KeyError,TypeError) as exc:
        raise ValueError('Optimal risk unavailable: missing bestByEv.risk') from exc


def _adapt_directory(firm,challenge_id):
    row = next(c for c in firm['challenges'] if c['challengeId']==challenge_id)
    # Refuse upstream adapter's missing financial/rule field defaults.
    for key in ('accountSize','steps','price','activationFee','profitSplitPercent','minTradingDays','firstPayoutMinDays'):
        if _finite(row.get(key),'directory '+key)<0:
            raise ValueError('Invalid directory '+key)
    for key in ('profitTargetIsPercent','lossIsPercent','isFeeRefundable'):
        if not isinstance(row.get(key),bool):
            raise ValueError('Directory '+key+' unavailable')
    for key in ('profitTarget','payoutFrequency','interval'):
        if not row.get(key):
            raise ValueError('Directory '+key+' unavailable')
    if not firm.get('name') or not firm.get('currency') or not firm.get('productTypes'):
        raise ValueError('Directory firm name/currency/product types unavailable')
    targets = row['profitTarget']
    if (not isinstance(row['steps'], int) or row['steps'] < 1 or
            not isinstance(targets, list) or len(targets) != row['steps'] or
            any(_finite(v, 'profit target') <= 0 for v in targets)):
        raise ValueError('Directory step targets unavailable/incomplete')
    # These rule fields would otherwise silently become false/zero/defaults.
    expected_mode = row.get('maxLossMode')
    if expected_mode not in ('static-initial','trailing-realized-eod','trailing-intraday-unrealized','trailing-locks-at-initial'):
        raise ValueError('Directory structured max-loss mode unavailable')
    if expected_mode != 'static-initial':
        for key in ('maxLossLocksAtInitial', 'maxLossLockOffset'):
            if row.get(key) is None:
                raise ValueError('Directory trailing-loss semantics unavailable: '+key)
    if row.get('dailyLoss') is not None:
        for key in ('dailyLossBasis','dailyLossLimitBasis','dailyLossIncludesOpenPnl','dailyLossEvaluation'):
            if row.get(key) is None:
                raise ValueError('Directory daily-loss semantics unavailable: '+key)
    payout_fields = ('payoutMinWinningDays','payoutWinningDayMinProfit','payoutBufferAmount')
    if any(row.get(k) is not None for k in (*payout_fields,'payoutMaxPct','payoutMaxAmount','fundedConsistencyPct')):
        for key in payout_fields:
            _finite(row.get(key),'directory '+key)
    script = (f'import {{adaptFirm,inferPayoutFrequency}} from {json.dumps((CORE/"directory/index.js").as_uri())};\n'
              f'if(!inferPayoutFrequency({json.dumps(row["payoutFrequency"])})) throw new Error("Payout cadence unavailable");\n'
              f'const a=adaptFirm({json.dumps(firm,allow_nan=False)}).find(c=>c.challengeId==={json.dumps(challenge_id)});\n'
              "if(!a) throw new Error('Challenge rules unavailable/ambiguous');\nconsole.log(JSON.stringify(a));\n")
    result = _run_node_script(script)
    if not isinstance(result.get('spec'),dict):
        raise ValueError('Adapted spec unavailable')
    return result


def _extract_result(result):
    try:
        p = _finite(result['perAttempt']['passProbability'],'pass probability')
        ci = result['perAttempt']['passProbabilityCi']
        low,high = _finite(ci['low'],'CI low'),_finite(ci['high'],'CI high')
        attempts = _finite(result['journey']['attempts']['mean'],'expected attempts')
        cost = _finite(result['journey']['cost']['mean'],'expected cost')
        ev = _finite(result['ev']['evTotal'],'funded EV')
        assumptions = result['assumptions']
        if not isinstance(assumptions,dict) or not all(k in assumptions for k in ('spec','profile','options','flags','disclaimer')):
            raise ValueError('Simulation assumptions unavailable')
        if not 0<=low<=p<=high<=1 or attempts<1 or cost<0:
            raise ValueError('Invalid simulation result ranges')
        return dict(pass_probability=p,ci={'low':low,'high':high},expected_attempts=attempts,
                    expected_cost=cost,ev_funded=ev,assumptions=assumptions)
    except (KeyError,TypeError) as exc:
        raise ValueError('Simulation result unavailable: missing required fields') from exc


def get_prop_sim(firm=None,risk_pct=None,n_paths=10000):
    observed = _observed_trades()
    trades = observed['trades']
    if len(trades)<MIN_TRADES_FOR_STATS:
        raise ValueError(f'Insufficient real trade data: {len(trades)} validated closed trades; need {MIN_TRADES_FOR_STATS}')
    values = [_finite(t['r'],'R') for t in trades]
    if risk_pct is None or not 0<_finite(risk_pct,'scenario risk_pct')<=100:
        raise ValueError('Explicit scenario risk_pct in (0,100] required')
    if isinstance(n_paths,bool) or not isinstance(n_paths,int) or not 1<=n_paths<=100000:
        raise ValueError('n_paths must be integer in [1,100000]')
    if not firm or '/' not in firm:
        raise ValueError('Explicit firm/challenge directory IDs required')
    firm_id,challenge_id = firm.split('/',1)
    raw_firm = _find_firm(firm_id,challenge_id)
    if raw_firm is None:
        raise ValueError('Requested directory firm/challenge unavailable')
    adapted = _adapt_directory(raw_firm,challenge_id)
    cadence = _cadence(trades)
    profile = {'kind':'bootstrap','rSeries':values,'blockMeanLength':5,
               'tradesPerDay':cadence['trades_per_day'],'tradesPerDayModel':'poisson',
               'risk':{'mode':'percent-of-balance','value':risk_pct}}
    options = {'paths':n_paths,'seed':DEFAULT_SEED,'simulateFunded':True,'fundedHorizonDays':90,
               'unlimitedStepDayCap':365,'includeHistograms':False,'tracePaths':0}
    result = _extract_result(_run_node_script(_build_node_script(adapted['spec'],profile,options)))
    try:
        optimal,error = _get_optimal_risk(adapted['spec'],profile),None
    except Exception as exc:
        optimal,error = None,f'Optimal risk unavailable ({type(exc).__name__})'
    result.update(status='available',result_kind='model-derived Monte Carlo; not observed performance',
                  data_source=observed['data_source'],optimal_risk=optimal,optimal_risk_unavailable_reason=error,
                  provenance={'trades':observed,'cadence':cadence,'directory_url':DIRECTORY_URL,
                              'raw_firm':raw_firm,'adaptation':adapted},
                  model_assumptions={'costs':'gross price R excludes commission, fees and swap; optimistic versus net',
                                     'bootstrap':'stationary blocks; assumed mean length 5',
                                     'cadence':'Poisson calendar-day proxy; see provenance.cadence',
                                     'risk_pct':'explicit hypothetical sizing, percentage units, not observed sizing',
                                     'optimizer':'best EV on core default 0.1%-3% grid; 1000 seeded paths; not a recommendation'})
    return result


if __name__=='__main__':
    try:
        print(json.dumps(get_prop_sim(),indent=2,allow_nan=False))
    except Exception as exc:
        print(f'Unavailable: {exc}',file=sys.stderr)
        sys.exit(1)

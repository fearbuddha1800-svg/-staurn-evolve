---
slug: test_prop_sim_real_data
type: note
graph: gitnexus
---

"""Offline fixtures only. Never contacts a broker, directory, or paid API."""
import copy
import json
import sqlite3
from types import SimpleNamespace as NS
from unittest.mock import Mock
import pytest
import prop_sim_bridge as p


@pytest.fixture
def history(tmp_path):
    db = tmp_path/'observed.db'
    with sqlite3.connect(db) as con:
        con.execute('CREATE TABLE trades(ticket INTEGER,symbol TEXT,side TEXT,sl REAL,status TEXT)')
        con.execute("INSERT INTO trades VALUES(11,'XAUUSD','buy',90,'executed')")
    entry = NS(entry=0,type=0,order=11,position_id=22,symbol='XAUUSD',price=100.,volume=1.,time=86400.)
    close = NS(entry=1,type=1,order=12,position_id=22,symbol='XAUUSD',price=120.,volume=1.,time=259200.)
    broker = NS(DEAL_ENTRY_IN=0,DEAL_ENTRY_OUT=1,DEAL_ENTRY_OUT_BY=3,DEAL_TYPE_BUY=0,DEAL_TYPE_SELL=1,
                positions_get=Mock(return_value=[]),
                history_orders_get=Mock(return_value=[NS(symbol='XAUUSD',sl=90.,position_id=22)]),
                history_deals_get=Mock(return_value=[entry,close]))
    return db,broker,entry,close


def test_missing_db_does_not_create(tmp_path):
    path = tmp_path/'missing.db'
    with pytest.raises(ValueError,match='database unavailable'):
        p._observed_trades(path,NS())
    assert not path.exists()


def test_absent_broker(history,monkeypatch):
    db,_,_,_ = history
    monkeypatch.setattr(p,'_broker',Mock(side_effect=ValueError('Broker unavailable')))
    with pytest.raises(ValueError,match='Broker unavailable'):
        p._observed_trades(db)


def test_unknown_positions_not_empty(history):
    db,b,_,_ = history
    b.positions_get.return_value = None
    with pytest.raises(ValueError,match='state unavailable'):
        p._observed_trades(db,b)


def test_observed_provenance_and_cadence(history):
    db,b,_,_ = history
    observed = p._observed_trades(db,b)
    assert observed['trades'][0]['r'] == 2
    assert 'original stop' in observed['trades'][0]['risk_basis']
    assert observed['trades'][0]['position_id'] == 22
    b.history_deals_get.assert_called_once_with(position=22)
    cadence = p._cadence(observed['trades'])
    assert cadence['denominator_days'] == 3
    assert cadence['trades_per_day'] == pytest.approx(1/3)
    assert 'including zero-entry days' in cadence['definition']


@pytest.mark.parametrize('field,value',[('price',float('nan')),('price',None),('volume',float('inf')),('time',None)])
def test_invalid_deals_not_zero(history,field,value):
    db,b,_,close = history
    setattr(close,field,value)
    result = p._observed_trades(db,b)
    assert result['trades'] == []
    assert len(result['rejected']) == 1


def test_missing_original_sl(history):
    db,b,_,_ = history
    b.history_orders_get.return_value[0].sl = None
    assert not p._observed_trades(db,b)['trades']


def test_partial_or_open_refused(history):
    db,b,_,close = history
    close.volume = .5
    assert not p._observed_trades(db,b)['trades']
    close.volume = 1
    b.positions_get.return_value = [NS(identifier=22)]
    assert not p._observed_trades(db,b)['trades']


@pytest.mark.parametrize('values',[[],[1]*10,[float('nan'),-1],[None,1],['1',-1]])
def test_stats_unknown_not_zero(values):
    with pytest.raises(ValueError):
        p._compute_trader_stats(values)


def test_insufficient_never_fetches(monkeypatch):
    monkeypatch.setattr(p,'_observed_trades',lambda:{'trades':[]})
    fetch = Mock(side_effect=AssertionError('must not fetch'))
    monkeypatch.setattr(p,'_fetch_prop_firm_list',fetch)
    with pytest.raises(ValueError,match='Insufficient real trade data'):
        p.get_prop_sim('firm/challenge',1,10)
    fetch.assert_not_called()


def result_fixture():
    return {'perAttempt':{'passProbability':.5,'passProbabilityCi':{'low':.4,'high':.6}},
            'journey':{'attempts':{'mean':2},'cost':{'mean':100}},'ev':{'evTotal':-100},
            'assumptions':{'spec':{},'profile':{},'options':{},'flags':[],'disclaimer':'fixture'}}


@pytest.mark.parametrize('section,key',[('perAttempt','passProbabilityCi'),('perAttempt','passProbability'),('journey','cost'),('ev','evTotal'),('assumptions','flags')])
def test_no_missing_output_zero_defaults(section,key):
    result = result_fixture()
    del result[section][key]
    with pytest.raises(ValueError):
        p._extract_result(result)


def test_optimizer_correct_contract(monkeypatch):
    monkeypatch.setattr(p,'_run_node_script',lambda script:{'bestByEv':{'risk':.5}})
    assert p._get_optimal_risk({}, {}) == .5
    monkeypatch.setattr(p,'_run_node_script',lambda script:{})
    with pytest.raises(ValueError):
        p._get_optimal_risk({}, {})


def test_model_labels_raw_metadata_and_risk_units(monkeypatch):
    observed = {'trades':[{'r':(-1 if i%2 else 2),'opened_at':86400*(i+1),'closed_at':86400*(i+1)+1} for i in range(10)],'data_source':'signals.db+MT5'}
    firm = {'propfirmId':'actual-id','name':'Fetched name','website':'https://real-firm.invalid','extra':'preserve','challenges':[{'challengeId':'c'}]}
    monkeypatch.setattr(p,'_observed_trades',lambda:observed)
    monkeypatch.setattr(p,'_find_firm',lambda *args:firm)
    monkeypatch.setattr(p,'_adapt_directory',lambda *args:{'spec':{},'inferredFields':[]})
    scripts = []
    def run(script):
        scripts.append(script)
        return result_fixture()
    monkeypatch.setattr(p,'_run_node_script',run)
    monkeypatch.setattr(p,'_get_optimal_risk',Mock(side_effect=ValueError('unavailable')))
    result = p.get_prop_sim('actual-id/c',.5,10)
    assert result['provenance']['raw_firm'] == firm
    assert result['optimal_risk'] is None
    assert 'model-derived Monte Carlo' in result['result_kind']
    assert 'not observed performance' in result['result_kind']
    assert '"kind": "bootstrap"' in scripts[0]
    assert '"value": 0.5' in scripts[0]
    assert '"rSeries": [2.0, -1.0' in scripts[0]
    assert 'file:///' in scripts[0]


def test_missing_directory_fields_refused():
    with pytest.raises(ValueError,match='directory accountSize'):
        p._adapt_directory({'challenges':[{'challengeId':'c'}]},'c')


def test_public_fetch_nested_response(monkeypatch):
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = b'{"data":{"propfirms":[{"propfirmId":"observed-name"}]}}'
    monkeypatch.setattr(p.urllib.request,'urlopen',Mock(return_value=response))
    assert p._fetch_prop_firm_list() == [{'propfirmId':'observed-name'}]


def test_production_invalid_r_refused(monkeypatch):
    monkeypatch.setattr(p,'_observed_trades',lambda:{'trades':[{'r':float('nan')}] * 10})
    with pytest.raises(ValueError,match='finite numeric'):
        p.get_prop_sim('f/c',1,10)


def test_directory_financial_missing_never_zero(monkeypatch):
    firm = {'name':'Fixture only','currency':'USD','productTypes':['cfd'],'challenges':[
        {'challengeId':'c','accountSize':10000,'steps':1,'price':100,'activationFee':0,
         'profitSplitPercent':80,'minTradingDays':0,'firstPayoutMinDays':0,
         'profitTargetIsPercent':True,'lossIsPercent':True,'isFeeRefundable':False,
         'profitTarget':[10],'payoutFrequency':'biweekly','interval':'one time','maxLossMode':'static-initial'}]}
    for key in ('price','activationFee','minTradingDays','firstPayoutMinDays'):
        candidate = copy.deepcopy(firm)
        del candidate['challenges'][0][key]
        with pytest.raises(ValueError,match='directory '+key):
            p._adapt_directory(candidate,'c')


def test_public_fetch_failure_explicit(monkeypatch):
    monkeypatch.setattr(p.urllib.request,'urlopen',Mock(side_effect=OSError()))
    with pytest.raises(ValueError,match='directory unavailable'):
        p._fetch_prop_firm_list()


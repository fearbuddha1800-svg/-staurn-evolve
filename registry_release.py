"""Fail-closed registry release gate and atomic per-engine bindings.

Bindings select research-approved entry signals only. They do not arm executor,
change magic numbers, or replace the existing 2 ATR / no-TP live exit policy.
Only the trusted CLI can approve a release; HTTP can select an approved release.
"""
from __future__ import annotations
import hashlib
import json
import math
import time

TARGETS = {'strategy.py': 20261015, 'strategy2_live.py': 20261015}


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def release_gate(result, *, revision, risk_unit_cash=None):
    reasons = []
    stats = result.get('stats') or {}
    if result.get('ok') is not True:
        reasons.append('Backtest did not succeed')
    if result.get('revision') != revision:
        reasons.append('Backtest revision is stale')
    if not finite(result.get('bars')) or result['bars'] < 500:
        reasons.append('At least 500 actual closed MT5 bars required')
    trades = stats.get('closed_trade_count')
    if not finite(trades) or trades < 100:
        reasons.append('At least 100 closed trades required (full count, not trade tail)')
    pf = stats.get('profit_factor')
    if not finite(pf) or pf < 1.10:
        reasons.append('Measured profit factor >= 1.10 required')
    commission = stats.get('commission_paid')
    if not finite(commission) or commission <= 0:
        reasons.append('Positive runtime-reported commissions required; unknown costs cannot pass')
    dd = stats.get('max_drawdown')
    dd_r = dd / risk_unit_cash if finite(dd) and finite(risk_unit_cash) and risk_unit_cash > 0 else None
    if dd_r is None or dd_r < 0 or dd_r > 30:
        reasons.append('Measured max drawdown <= 30R requires an explicit positive cash R unit')
    return {'passed': not reasons, 'reasons': reasons, 'max_drawdown_r': dd_r,
            'risk_unit_cash': risk_unit_cash}


def approve(registry, strategy_id, *, risk_unit_cash, acknowledge_live_policy=False):
    """Explicit owner review, never called by discovery/HTTP."""
    if not acknowledge_live_policy:
        raise ValueError('Acknowledge that Pine exits differ from live 2 ATR / no-TP policy')
    source = registry.source(strategy_id)
    revision = hashlib.sha256(source.encode()).hexdigest()
    entry = next(e for e in registry.list() if e['id'] == strategy_id)
    if entry.get('revision') != revision or entry.get('status') not in ('ready', 'research-ready') or entry.get('kind') != 'strategy':
        raise ValueError('Current source must be a validated strategy')
    if entry.get('warnings'):
        raise ValueError('Resolve Pine data-provider/library warnings before release')
    result = json.loads((registry.cache / strategy_id / 'backtest.json').read_text(encoding='utf-8'))
    gate = release_gate(result, revision=revision, risk_unit_cash=risk_unit_cash)
    if not gate['passed']:
        raise ValueError('; '.join(gate['reasons']))
    release = {'strategy_id': strategy_id, 'revision': revision, 'gate': gate,
               'symbol': result['symbol'], 'timeframe': result['timeframe'],
               'approved_at': time.time(), 'live_policy': '2 ATR stop / no fixed TP',
               'execution_armed': False}
    registry._write(registry.cache / strategy_id / 'approved.json', json.dumps(release, allow_nan=False))
    return release


def deploy(registry, strategy_id, revision, target):
    if target not in TARGETS:
        raise ValueError('Unknown deployment target')
    registry._id(strategy_id)
    entry = next((e for e in registry.list() if e['id'] == strategy_id), None)
    if not entry or entry.get('revision') != revision or entry.get('status') == 'error':
        raise ValueError('Deployment revision must match current discovered source')
    approved = json.loads((registry.cache / strategy_id / 'approved.json').read_text(encoding='utf-8'))
    if approved.get('revision') != revision or approved.get('strategy_id') != strategy_id:
        raise ValueError('Trusted owner approval required for this exact revision')
    snapshot = registry.cache / strategy_id / (revision + '.pine')
    if hashlib.sha256(snapshot.read_bytes()).hexdigest() != revision:
        raise ValueError('Approved snapshot hash mismatch')
    binding = {**approved, 'target': target, 'magic': TARGETS[target], 'deployed_at': time.time()}
    path = registry.cache / 'deployments' / (target + '.json')
    registry._write(path, json.dumps(binding, allow_nan=False))
    if json.loads(path.read_text(encoding='utf-8')) != binding:
        raise RuntimeError('Deployment readback mismatch')
    return binding


def read_binding(registry, target):
    if target not in TARGETS:
        raise ValueError('Unknown deployment target')
    path = registry.cache / 'deployments' / (target + '.json')
    if not path.exists():
        return None
    binding = json.loads(path.read_text(encoding='utf-8'))
    strategy_id = registry._id(binding.get('strategy_id'))
    approved = json.loads((registry.cache / strategy_id / 'approved.json').read_text(encoding='utf-8'))
    if (binding.get('target') != target or binding.get('magic') != TARGETS[target] or
            binding.get('revision') != approved.get('revision') or not approved.get('gate', {}).get('passed')):
        raise ValueError('Invalid or revoked registry deployment')
    revision = binding['revision']
    if not isinstance(revision, str) or len(revision) != 64 or any(c not in '0123456789abcdef' for c in revision):
        raise ValueError('Invalid bound revision')
    snapshot = registry.cache / strategy_id / (revision + '.pine')
    if hashlib.sha256(snapshot.read_bytes()).hexdigest() != revision:
        raise ValueError('Deployed source hash mismatch')
    return {**binding, 'snapshot': str(snapshot)}

"""Pure offline shadow evidence engine. No execution, database, network or ML.

CLI: python signal_evidence.py --input evidence.jsonl --as-of <aware ISO time>
JSON input is an array; JSONL is one envelope per line. Envelopes are exactly
{"kind":"signal"|"outcome", "data":{...}}. --demo emits TEST FIXTURES only.
All cash/price values are decimal strings, all timestamps include UTC offsets.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, fields, asdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
import math
from pathlib import Path
import re
from statistics import mean, stdev
from typing import Literal


class EvidenceError(ValueError):
    """Unusable evidence; callers must abstain, never repair it implicitly."""


def text(value: object, name: str) -> None:
    if type(value) is not str or not value.strip() or value != value.strip():
        raise EvidenceError(f'{name}: nonempty, unpadded text required')


def aware(value: object, name: str) -> datetime:
    if not isinstance(value, datetime) or value.utcoffset() is None:
        raise EvidenceError(f'{name}: timezone-aware datetime required')
    return value


def stamp(value: object) -> datetime:
    if type(value) is not str:
        raise EvidenceError('timestamp must be ISO text')
    try:
        return aware(datetime.fromisoformat(value.replace('Z', '+00:00')), 'timestamp')
    except (ValueError, TypeError) as exc:
        raise EvidenceError(str(exc)) from exc


def number(value: object, name: str, positive: bool = False) -> Decimal:
    if type(value) is not Decimal or not value.is_finite() or (positive and value <= 0):
        raise EvidenceError(f'{name}: finite Decimal' + (' > 0 required' if positive else ' required'))
    if len(value.as_tuple().digits) > 38 or not -18 <= value.as_tuple().exponent <= 18:
        raise EvidenceError(f'{name}: decimal precision/exponent outside evidence bounds')
    return value


@dataclass(frozen=True)
class SignalEvidence:
    source: str
    message_id: str
    source_version: str
    version: int
    original_at: datetime
    version_at: datetime
    received_at: datetime
    feature_at: datetime
    quote_at: datetime
    provenance: str
    parser_version: str
    content_hash: str
    category: Literal['entry', 'recap', 'management', 'ambiguous']
    symbol: str
    side: Literal['buy', 'sell']
    entry: Decimal
    stop: Decimal
    target: Decimal
    bid: Decimal
    ask: Decimal
    correlation_id: str

    def __post_init__(self) -> None:
        for key in ('source', 'message_id', 'source_version', 'provenance', 'parser_version',
                    'content_hash', 'symbol', 'correlation_id'):
            text(getattr(self, key), key)
        if len(self.content_hash) != 64 or any(c not in '0123456789abcdef' for c in self.content_hash):
            raise EvidenceError('content_hash must be lowercase SHA256 hex')
        if type(self.version) is not int or self.version < 1:
            raise EvidenceError('version must be a positive integer')
        for key in TIME_SIGNAL:
            aware(getattr(self, key), key)
        if not self.original_at <= self.version_at <= self.received_at:
            raise EvidenceError('original <= version <= receipt required')
        if self.version == 1 and self.original_at != self.version_at:
            raise EvidenceError('original version timestamp mismatch')
        if self.category not in ('entry', 'recap', 'management', 'ambiguous'):
            raise EvidenceError('invalid category')
        if self.side not in ('buy', 'sell'):
            raise EvidenceError('explicit side required')
        for key in PRICE_SIGNAL:
            number(getattr(self, key), key, True)
        if self.ask < self.bid:
            raise EvidenceError('crossed quote')
        if not (self.stop < self.entry < self.target if self.side == 'buy'
                else self.target < self.entry < self.stop):
            raise EvidenceError('invalid stop/entry/target geometry')

    @property
    def identity(self) -> tuple[str, str, str, int]:
        return self.source, self.source_version, self.message_id, self.version


TIME_SIGNAL = ('original_at', 'version_at', 'received_at', 'feature_at', 'quote_at')
PRICE_SIGNAL = ('entry', 'stop', 'target', 'bid', 'ask')


@dataclass(frozen=True)
class OutcomeEvidence:
    outcome_id: str
    decision_id: str
    mode: Literal['paper', 'broker']
    status: Literal['completed', 'open', 'censored']
    opened_at: datetime
    closed_at: datetime | None
    observed_at: datetime
    gross_pnl: Decimal | None
    costs: Decimal | None
    initial_risk: Decimal | None
    currency: str
    evidence_ref: str
    costs_complete: bool

    def __post_init__(self) -> None:
        for key in ('outcome_id', 'decision_id', 'currency', 'evidence_ref'):
            text(getattr(self, key), key)
        if self.mode not in ('paper', 'broker') or self.status not in ('completed', 'open', 'censored'):
            raise EvidenceError('invalid outcome mode/status')
        if type(self.costs_complete) is not bool:
            raise EvidenceError('costs_complete must be boolean')
        aware(self.opened_at, 'opened_at')
        aware(self.observed_at, 'observed_at')
        if self.opened_at > self.observed_at:
            raise EvidenceError('outcome observed before open')
        if self.closed_at is not None:
            aware(self.closed_at, 'closed_at')
            if not self.opened_at <= self.closed_at <= self.observed_at:
                raise EvidenceError('invalid outcome chronology')
        for key in ('gross_pnl', 'costs', 'initial_risk'):
            value = getattr(self, key)
            if value is not None:
                number(value, key, key == 'initial_risk')
        if self.costs is not None and self.costs < 0:
            raise EvidenceError('costs must be nonnegative all-in cash deduction')
        if self.status == 'completed' and (self.closed_at is None or not self.costs_complete
                or any(getattr(self, k) is None for k in ('gross_pnl', 'costs', 'initial_risk'))):
            raise EvidenceError('completed outcome requires final close and complete cash costs/risk')
        if self.status == 'open' and self.closed_at is not None:
            raise EvidenceError('open outcome cannot have close timestamp')

    @property
    def realized_r(self) -> Decimal | None:
        if self.status != 'completed':
            return None
        with localcontext() as context:
            context.prec = 128
            return (self.gross_pnl - self.costs) / self.initial_risk


@dataclass(frozen=True)
class Policy:
    max_latency_s: int = 60
    max_age_s: int = 120
    max_quote_age_s: int = 10
    correlation_window_s: int = 600
    min_clusters: int = 30
    min_split_clusters: int = 10

    def __post_init__(self) -> None:
        for field in fields(self):
            value = getattr(self, field.name)
            if type(value) is not int or value <= 0:
                raise EvidenceError('policy bounds must be positive integers')
        if self.min_clusters < 2 or self.min_split_clusters < 2:
            raise EvidenceError('uncertainty needs at least two clusters')


@dataclass(frozen=True)
class ShadowDecision:
    decision_id: str | None
    identity: tuple[str, str, str, int] | None
    decided_at: datetime
    disposition: Literal['shadow_candidate', 'abstain']
    reason: str
    cluster_id: str | None = None
    approved_for_live: Literal[False] = False


def decode(model: type, data: object):
    """Exact schemas; reject unknown/missing keys, coercions and naive times."""
    if type(data) is not dict or set(data) != {f.name for f in fields(model)}:
        raise EvidenceError('exact model fields required (no unknown or missing keys)')
    values = dict(data)
    times = TIME_SIGNAL if model is SignalEvidence else ('opened_at', 'closed_at', 'observed_at')
    decimals = PRICE_SIGNAL if model is SignalEvidence else ('gross_pnl', 'costs', 'initial_risk')
    try:
        for key in times:
            if values[key] is not None:
                values[key] = stamp(values[key])
        for key in decimals:
            if values[key] is not None:
                if (type(values[key]) is not str or len(values[key]) > 128
                        or re.fullmatch(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?',
                                        values[key]) is None):
                    raise EvidenceError(f'{key}: canonical decimal string required')
                values[key] = Decimal(values[key])
        return model(**values)
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise EvidenceError(str(exc)) from exc


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class ShadowEngine:
    """In-memory replay ledger. Replay full input to rebuild; never imports a broker."""

    def __init__(self, policy: Policy | None = None):
        self.policy = policy or Policy()
        self.signals: dict[tuple, SignalEvidence] = {}
        self.decisions: dict[str, ShadowDecision] = {}
        self.outcomes: dict[tuple[str, str], OutcomeEvidence] = {}
        self.outcome_history: list[OutcomeEvidence] = []
        self.outcome_ids: set[str] = set()
        self.outcome_refs: dict[tuple[str, str], str] = {}
        self.last_received: datetime | None = None
        self.clusters: list[tuple[SignalEvidence, str]] = []
        self.cluster_parent: dict[str, str] = {}

    def _root(self, cluster: str) -> str:
        while self.cluster_parent.get(cluster, cluster) != cluster:
            cluster = self.cluster_parent[cluster]
        return cluster

    def decide(self, signal: SignalEvidence, *, now: datetime) -> ShadowDecision:
        aware(now, 'now')
        if type(signal) is not SignalEvidence:
            raise EvidenceError('SignalEvidence required')
        identity = signal.identity
        did = digest(identity)
        def result(reason: str, cluster: str | None = None) -> ShadowDecision:
            return ShadowDecision(did, identity, now,
                                  'shadow_candidate' if reason == 'eligible' else 'abstain', reason, cluster)
        if identity in self.signals:
            return result('replay' if self.signals[identity] == signal else 'identity_conflict')
        if signal.received_at > now:
            return result('future_receipt')
        if self.last_received is not None and signal.received_at < self.last_received:
            return result('out_of_order_receipt')
        self.last_received = signal.received_at
        self.signals[identity] = signal
        reason = 'eligible'
        if signal.version != 1:
            reason = 'edit_not_new_entry'
        elif signal.category != 'entry':
            reason = 'not_entry'
        elif (signal.received_at - signal.original_at).total_seconds() > self.policy.max_latency_s:
            reason = 'publication_latency'
        elif (now - signal.original_at).total_seconds() > self.policy.max_age_s:
            reason = 'stale_signal'
        elif signal.feature_at > signal.received_at or signal.quote_at > signal.received_at:
            reason = 'future_features_or_quote'
        elif any((now - t).total_seconds() > self.policy.max_quote_age_s
                 for t in (signal.quote_at, signal.feature_at)):
            reason = 'stale_features_or_quote'
        cluster = digest(('cluster', identity))
        geometry = lambda s: (s.symbol, s.side, s.entry, s.stop, s.target)
        # Includes abstentions; repeated echoes cannot reset stale/correlated evidence.
        # Union every match: later bridge evidence can correlate earlier clusters.
        # Such multi-candidate clusters are quarantined from source scoring below.
        matches = set()
        for previous, cid in self.clusters:
            same_message = previous.source == signal.source and previous.message_id == signal.message_id
            explicit = previous.correlation_id == signal.correlation_id
            echo = (geometry(previous) == geometry(signal) and
                    (signal.received_at - previous.received_at).total_seconds() <= self.policy.correlation_window_s)
            if same_message or explicit or echo:
                matches.add(self._root(cid))
        if matches:
            cluster = sorted(matches)[0]
            for cid in matches:
                self.cluster_parent[cid] = cluster
            if reason == 'eligible':
                reason = 'correlated_duplicate'
        self.cluster_parent.setdefault(cluster, cluster)
        self.clusters.append((signal, cluster))
        decision = result(reason, cluster)
        self.decisions[did] = decision
        return decision

    def record_outcome(self, outcome: OutcomeEvidence, *, now: datetime) -> str:
        aware(now, 'now')
        if type(outcome) is not OutcomeEvidence:
            raise EvidenceError('OutcomeEvidence required')
        decision = self.decisions.get(outcome.decision_id)
        if decision is None or decision.disposition != 'shadow_candidate':
            return 'unattributed_or_abstained_decision'
        if outcome.observed_at > now or outcome.opened_at < decision.decided_at:
            return 'future_or_predecision_outcome'
        key = (outcome.decision_id, outcome.mode)
        if outcome.outcome_id in self.outcome_ids:
            return 'outcome_replay_or_conflict'
        ref_key = (outcome.mode, outcome.evidence_ref)
        if self.outcome_refs.get(ref_key, outcome.decision_id) != outcome.decision_id:
            return 'outcome_evidence_already_attributed'
        previous = self.outcomes.get(key)
        if previous is not None and (previous.status == 'completed'
                or outcome.observed_at <= previous.observed_at
                or outcome.opened_at != previous.opened_at
                or outcome.currency != previous.currency
                or outcome.evidence_ref != previous.evidence_ref
                or (previous.initial_risk is not None and outcome.initial_risk != previous.initial_risk)):
            return 'outcome_revision_conflict'
        self.outcome_refs[ref_key] = outcome.decision_id
        self.outcome_ids.add(outcome.outcome_id)
        self.outcomes[key] = outcome
        self.outcome_history.append(outcome)
        return 'recorded'

    def source_report(self, *, as_of: datetime, split_at: datetime) -> dict:
        aware(as_of, 'as_of')
        aware(split_at, 'split_at')
        if split_at >= as_of:
            raise EvidenceError('split must precede as_of')
        # Rebuild correlation only from information available by the report cutoff.
        snapshot = ShadowEngine(self.policy)
        for signal in self.signals.values():
            if signal.received_at <= as_of:
                snapshot.decide(signal, now=signal.received_at)
        cluster_counts: dict[str, int] = {}
        for decision in self.decisions.values():
            if decision.decided_at <= as_of and decision.disposition == 'shadow_candidate':
                root = snapshot._root(decision.cluster_id)
                cluster_counts[root] = cluster_counts.get(root, 0) + 1
        known_outcomes = {(o.decision_id, o.mode): o for o in self.outcome_history
                          if o.observed_at <= as_of}
        groups: dict[tuple, list] = {}
        counts: dict[tuple, dict] = {}
        for identity, signal in self.signals.items():
            if signal.received_at > as_of:
                continue
            source = (signal.source, signal.source_version)
            counts.setdefault(source, {'received_versions': 0, 'shadow_candidates': 0})
            counts[source]['received_versions'] += 1
            decision = self.decisions[digest(identity)]
            if decision.decided_at > as_of or decision.disposition != 'shadow_candidate':
                continue
            counts[source]['shadow_candidates'] += 1
            for mode in ('paper', 'broker'):
                outcome = known_outcomes.get((decision.decision_id, mode))
                if outcome is not None and outcome.observed_at <= as_of:
                    groups.setdefault((*source, mode), []).append((signal, decision, outcome))
        reports = []
        for source in sorted(counts):
            for mode in ('paper', 'broker'):
                rows = groups.get((*source, mode), [])
                completed = [r for r in rows if r[2].status == 'completed']
                usable = [r for r in completed
                          if cluster_counts[snapshot._root(r[1].cluster_id)] == 1]
                correlation_excluded = len(completed) - len(usable)
                train = [r for r in usable if r[1].decided_at < split_at and r[2].observed_at < split_at]
                holdout = [r for r in usable if r[0].original_at >= split_at and r[1].decided_at >= split_at]
                leaked = len(usable) - len(train) - len(holdout)
                # One candidate per cluster engine-wide; defensive uniqueness before scoring.
                clusters = {r[1].cluster_id for r in usable}
                values = [float(r[2].realized_r) for r in usable]
                if any(not math.isfinite(v) for v in values):
                    raise EvidenceError('realized R outside report numeric range')
                n = len(values)
                avg = mean(values) if n else None
                half = 1.96 * stdev(values) / math.sqrt(n) if n >= 2 else None
                enough = (len(clusters) >= self.policy.min_clusters and
                          len(train) >= self.policy.min_split_clusters and
                          len(holdout) >= self.policy.min_split_clusters and leaked == 0
                          and correlation_excluded == 0 and len(usable) == counts[source]['shadow_candidates'])
                reports.append({'source': source[0], 'source_version': source[1], 'mode': mode,
                    **counts[source], 'completed': len(completed), 'scored_completed': n,
                    'correlation_excluded': correlation_excluded,
                    'open_or_censored': len(rows) - len(completed),
                    'missing_outcomes': counts[source]['shadow_candidates'] - len(rows),
                    'independent_clusters': len(clusters), 'train_completed': len(train),
                    'holdout_completed': len(holdout), 'boundary_leakage_excluded': leaked,
                    'mean_realized_r': avg, 'mean_r_interval_approx95':
                        [avg - half, avg + half] if half is not None else None,
                    'train_mean_r': mean([float(r[2].realized_r) for r in train]) if train else None,
                    'holdout_mean_r': mean([float(r[2].realized_r) for r in holdout]) if holdout else None,
                    'evidence_state': 'descriptive_only' if enough else 'insufficient_evidence',
                    'approved_for_live': False})
        return {'mode': 'offline_shadow_only', 'as_of': as_of, 'split_at': split_at,
                'approved_for_live': False, 'sources': reports,
                'limitations': ['No profitability, predictive edge, ML or promotion inference.',
                    'Intervals are descriptive normal approximations, unreliable for small/heavy-tailed samples.',
                    'Correlation uses declared IDs and exact geometry, not inferred economic independence.',
                    'Missing/censored outcomes can bias completed-only summaries; no imputation.',
                    'Cash values/cost completeness/provenance are assertions, not broker-verified facts.',
                    'No multiple-testing correction, regime coverage or deployment authorization.',
                    'Ledger is in memory; replay all records to restore duplicate protection.']}


def json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(type(value).__name__)


def fixture_records() -> list[dict]:
    """Clearly synthetic examples, never live observations."""
    data = dict(source='TEST_FIXTURE_SOURCE', message_id='TEST-1', source_version='TEST-v1',
                version=1, original_at='2026-01-01T12:00:00+00:00',
                version_at='2026-01-01T12:00:00+00:00', received_at='2026-01-01T12:00:02+00:00',
                feature_at='2026-01-01T12:00:01+00:00', quote_at='2026-01-01T12:00:01+00:00',
                provenance='TEST FIXTURE NOT LIVE', parser_version='TEST-parser',
                content_hash=hashlib.sha256(b'TEST FIXTURE NOT LIVE').hexdigest(),
                category='entry', symbol='TEST_EURUSD', side='buy', entry='1.10001',
                stop='1.09901', target='1.10201', bid='1.10000', ask='1.10002',
                correlation_id='TEST-cluster-1')
    return [{'kind': 'signal', 'data': data}]


def replay(records: list, *, as_of: datetime, split_at: datetime) -> dict:
    engine = ShadowEngine()
    decisions, outcomes, rejected = [], [], []
    for index, envelope in enumerate(records):
        try:
            if type(envelope) is not dict or set(envelope) != {'kind', 'data'}:
                raise EvidenceError('exact envelope required')
            kind = envelope['kind']
            if kind == 'signal':
                signal = decode(SignalEvidence, envelope['data'])
                # The historical receipt is the decision clock; report as_of is a read cutoff.
                if signal.received_at > as_of:
                    raise EvidenceError('future receipt relative to as_of')
                decisions.append(asdict(engine.decide(signal, now=signal.received_at)))
            elif kind == 'outcome':
                outcome = decode(OutcomeEvidence, envelope['data'])
                outcomes.append({'index': index, 'result': engine.record_outcome(outcome, now=as_of)})
            else:
                raise EvidenceError('unknown envelope kind')
        except (EvidenceError, OverflowError) as exc:
            rejected.append({'index': index, 'disposition': 'abstain', 'reason': str(exc),
                             'approved_for_live': False})
    return {'decisions': decisions, 'outcomes': outcomes, 'rejected': rejected,
            'report': engine.source_report(as_of=as_of, split_at=split_at)}


def strict_json(raw: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise EvidenceError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    def invalid_constant(value):
        raise EvidenceError('nonfinite JSON constant: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--input', type=Path)
    group.add_argument('--demo', action='store_true')
    parser.add_argument('--as-of', required=True, type=stamp)
    parser.add_argument('--split-at', required=True, type=stamp)
    args = parser.parse_args()
    try:
        if args.demo:
            records = fixture_records()
            fixture = decode(SignalEvidence, records[0]['data'])
            records.append({'kind': 'outcome', 'data': {
                'outcome_id': 'TEST-FIXTURE-OUTCOME', 'decision_id': digest(fixture.identity),
                'mode': 'paper', 'status': 'completed',
                'opened_at': '2026-01-01T12:00:02+00:00',
                'closed_at': '2026-01-01T12:00:32+00:00',
                'observed_at': '2026-01-01T12:00:33+00:00',
                'gross_pnl': '25', 'costs': '5', 'initial_risk': '10',
                'currency': 'TEST_USD', 'evidence_ref': 'TEST FIXTURE NOT LIVE OUTCOME',
                'costs_complete': True}})
        else:
            raw = args.input.read_text(encoding='utf-8')
            records = strict_json(raw) if args.input.suffix.lower() == '.json' else [
                strict_json(line) for line in raw.splitlines() if line.strip()]
            if type(records) is not list:
                raise EvidenceError('JSON input must be an array')
        result = replay(records, as_of=args.as_of, split_at=args.split_at)
        result['test_fixture_only'] = args.demo
        print(json.dumps(result, default=json_default, allow_nan=False, indent=2))
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    main()

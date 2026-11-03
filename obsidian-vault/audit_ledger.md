---
slug: audit_ledger
type: note
graph: gitnexus
---

"""Append-only, SHA-256 chained observation/revert ledger (stdlib only).

This is a LIBRARY, not a broker executor or a runtime collector. Reverts create
compensating *ledger* snapshots; they do not undo fills, cashflows, config or
broker state. An authenticated integration must authorize actor identities.
FinancialState preserves the caller's position_size/netprofit/equity/max_drawdown
values, including null for unknown. Use one scope and consistent units per DB;
position_size is signed, max_drawdown is a nonnegative magnitude (not a ratio
unless all callers explicitly use that basis in metadata). No values are inferred.

Events remain in the existing bus. For low-noise UI reads use
/api/events?limit=100&exclude=pnl_update (or bus.history(exclude='pnl_update')).
Never filter audit storage or suppress published pnl_update observations.

Hash format: SHA256 of UTF-8 json.dumps(entry without hash, sort_keys=True,
separators=(',', ':'), ensure_ascii=True, allow_nan=False). Genesis prev_hash is
64 zeroes. Locally tamper-evident, NOT authenticated: a privileged attacker can
rewrite a whole DB or truncate its tail. Persist a trusted (seq, hash) checkpoint
outside the DB; verify(expected_head=...) detects divergence from that anchor.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from typing import Mapping

GENESIS = '0' * 64
STATE_KEYS = frozenset(('position_size', 'netprofit', 'equity', 'max_drawdown'))
EVENTS_URL = '/api/events?limit=100&exclude=pnl_update'


class LedgerError(ValueError):
    """Invalid input or workflow transition."""


class IntegrityError(LedgerError):
    """Persisted ledger fails verification; all writes fail closed."""


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False)


def entry_hash(entry):
    return hashlib.sha256(_json({k: v for k, v in entry.items() if k != 'hash'})
                          .encode('utf-8')).hexdigest()


def _text(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 4096:
        raise LedgerError(f'{field} must be a nonblank string of at most 4096 characters')
    return value


def _seq(value):
    if type(value) is not int or value < 1:
        raise LedgerError('sequence must be a positive integer')
    return value


def financial_state(value: Mapping):
    if not isinstance(value, Mapping) or set(value) != STATE_KEYS:
        raise LedgerError('state requires exactly ' + ', '.join(sorted(STATE_KEYS)))
    result = dict(value)
    for key, number in result.items():
        if number is not None and (type(number) not in (int, float)
                                   or (type(number) is float and not math.isfinite(number))):
            raise LedgerError(f'{key} must be finite numeric or null')
    if result['max_drawdown'] is not None and result['max_drawdown'] < 0:
        raise LedgerError('max_drawdown must be nonnegative or null')
    return result


class AuditLedger:
    """One scope per file. SQLite BEGIN IMMEDIATE serializes cross-process writes.

    Callers must supply a separate audit DB, never a live broker/session DB.
    No DB or default global ledger is created at import time.
    """
    def __init__(self, path, *, scope):
        self.path = str(Path(path).resolve())
        self.scope = _text(scope, 'scope')
        with self._connection() as con:
            con.execute('PRAGMA journal_mode=WAL')
            con.executescript('''
                CREATE TABLE IF NOT EXISTS audit_entries (
                    seq INTEGER PRIMARY KEY, document TEXT NOT NULL);
                CREATE TRIGGER IF NOT EXISTS audit_no_update
                  BEFORE UPDATE ON audit_entries BEGIN
                  SELECT RAISE(ABORT, 'audit entries are immutable'); END;
                CREATE TRIGGER IF NOT EXISTS audit_no_delete
                  BEFORE DELETE ON audit_entries BEGIN
                  SELECT RAISE(ABORT, 'audit entries are immutable'); END;
            ''')
        self.verify()

    @contextmanager
    def _connection(self):
        con = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        con.execute('PRAGMA busy_timeout=10000')
        try:
            yield con
        finally:
            con.close()

    @contextmanager
    def _transaction(self):
        with self._connection() as con:
            con.execute('BEGIN IMMEDIATE')
            try:
                rows = self._read(con)
                self._verify(rows)
                yield con, rows
                con.commit()
            except BaseException:
                con.rollback()
                raise

    @staticmethod
    def _read(con):
        try:
            rows = []
            for seq, document in con.execute('SELECT seq, document FROM audit_entries ORDER BY seq'):
                row = json.loads(document)
                if not isinstance(row, dict) or row.get('seq') != seq:
                    raise IntegrityError('SQL sequence/document mismatch')
                rows.append(row)
            return rows
        except (TypeError, ValueError) as exc:
            raise IntegrityError('Malformed audit document') from exc

    def _verify(self, rows):
        previous = GENESIS
        current = None
        proposals, decisions = {}, {}
        for seq, entry in enumerate(rows, 1):
            try:
                if set(entry) != {'version', 'seq', 'timestamp', 'scope', 'kind',
                                  'actor', 'reason', 'state', 'payload', 'prev_hash', 'hash'}:
                    raise IntegrityError('Invalid entry fields')
                if (type(entry['version']) is not int or entry['version'] != 1
                        or type(entry['seq']) is not int or entry['seq'] != seq
                        or entry['prev_hash'] != previous or entry['scope'] != self.scope
                        or entry['hash'] != entry_hash(entry)):
                    raise IntegrityError('Hash, scope or sequence mismatch')
                stamp = datetime.fromisoformat(entry['timestamp'])
                if not entry['timestamp'].endswith('Z') or stamp.utcoffset().total_seconds() != 0:
                    raise IntegrityError('Timestamp must be UTC')
                _text(entry['actor'], 'actor')
                _text(entry['reason'], 'reason')
                financial_state(entry['state'])
                kind, payload = entry['kind'], entry['payload']
                if not isinstance(payload, dict):
                    raise IntegrityError('Payload must be an object')
                if kind == 'snapshot':
                    if set(payload) != {'metadata'} or not isinstance(payload['metadata'], dict):
                        raise IntegrityError('Invalid snapshot payload')
                    current = entry
                elif kind == 'revert_proposed':
                    if set(payload) != {'target_seq', 'target_hash', 'base_seq', 'base_hash'}:
                        raise IntegrityError('Invalid proposal payload')
                    target_seq = _seq(payload['target_seq'])
                    base_seq = _seq(payload['base_seq'])
                    if not (target_seq < base_seq < seq):
                        raise IntegrityError('Revert must target an earlier state')
                    target = rows[target_seq - 1]
                    if (current is None or current['seq'] != base_seq
                            or current['hash'] != payload['base_hash']
                            or target['kind'] not in ('snapshot', 'revert_committed')
                            or target['hash'] != payload['target_hash']
                            or entry['state'] != current['state']):
                        raise IntegrityError('Invalid revert target/base')
                    proposals[seq] = entry
                elif kind in ('revert_approved', 'revert_rejected'):
                    if set(payload) != {'proposal_seq'}:
                        raise IntegrityError('Invalid decision payload')
                    prop_seq = _seq(payload['proposal_seq'])
                    prop = proposals.get(prop_seq)
                    if (prop is None or prop_seq in decisions or current is None
                            or entry['state'] != current['state']):
                        raise IntegrityError('Missing proposal or duplicate decision')
                    if kind == 'revert_approved' and (
                            entry['actor'] == prop['actor']
                            or current['hash'] != prop['payload']['base_hash']):
                        raise IntegrityError('Self approval or stale proposal')
                    decisions[prop_seq] = entry
                elif kind == 'revert_committed':
                    if set(payload) != {'proposal_seq', 'approval_seq', 'target_seq', 'target_hash'}:
                        raise IntegrityError('Invalid commit payload')
                    prop_seq = _seq(payload['proposal_seq'])
                    prop, approval = proposals.get(prop_seq), decisions.get(prop_seq)
                    if (prop is None or approval is None or approval['kind'] != 'revert_approved'
                            or payload['approval_seq'] != approval['seq']
                            or current is None or current['hash'] != prop['payload']['base_hash']
                            or payload['target_seq'] != prop['payload']['target_seq']
                            or payload['target_hash'] != prop['payload']['target_hash']
                            or entry['state'] != rows[payload['target_seq'] - 1]['state']):
                        raise IntegrityError('Unapproved, stale or repeated commit')
                    current = entry
                else:
                    raise IntegrityError('Unknown entry kind')
                previous = entry['hash']
            except (KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
                raise IntegrityError(f'Invalid audit entry {seq}: {exc}') from exc
        return {'ok': True, 'count': len(rows), 'head_hash': previous,
                'head_seq': len(rows), 'scope': self.scope}

    def verify(self, *, expected_head=None):
        with self._connection() as con:
            result = self._verify(self._read(con))
        if expected_head is not None and expected_head != (result['head_seq'], result['head_hash']):
            raise IntegrityError('Trusted head checkpoint mismatch')
        return result

    def entries(self):
        with self._connection() as con:
            rows = self._read(con)
            self._verify(rows)
            return rows

    @staticmethod
    def _current(rows):
        return next((r for r in reversed(rows)
                     if r['kind'] in ('snapshot', 'revert_committed')), None)

    def _append(self, con, rows, kind, state, payload, actor, reason):
        entry = {'version': 1, 'seq': len(rows) + 1,
                 'timestamp': datetime.now(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z'),
                 'scope': self.scope, 'kind': kind, 'actor': _text(actor, 'actor'),
                 'reason': _text(reason, 'reason'), 'state': financial_state(state),
                 'payload': payload, 'prev_hash': rows[-1]['hash'] if rows else GENESIS}
        entry['hash'] = entry_hash(entry)
        # Round-trip freezes caller-owned metadata before persistence/return.
        entry = json.loads(_json(entry))
        self._verify(rows + [entry])
        con.execute('INSERT INTO audit_entries(seq, document) VALUES (?,?)',
                    (entry['seq'], _json(entry)))
        return entry

    def record_snapshot(self, state, *, actor, reason, metadata=None):
        metadata = {} if metadata is None else metadata
        if not isinstance(metadata, dict):
            raise LedgerError('metadata must be an object')
        with self._transaction() as (con, rows):
            return self._append(con, rows, 'snapshot', state, {'metadata': metadata}, actor, reason)

    def propose_revert(self, target_seq, *, actor, reason):
        _seq(target_seq)
        with self._transaction() as (con, rows):
            current = self._current(rows)
            if current is None or not 1 <= target_seq < current['seq']:
                raise LedgerError('Target must be an earlier state entry')
            target = rows[target_seq - 1]
            if target['kind'] not in ('snapshot', 'revert_committed'):
                raise LedgerError('Target is not a state entry')
            return self._append(con, rows, 'revert_proposed', current['state'],
                                {'target_seq': target_seq, 'target_hash': target['hash'],
                                 'base_seq': current['seq'], 'base_hash': current['hash']}, actor, reason)

    def decide_revert(self, proposal_seq, *, approve, actor, reason):
        _seq(proposal_seq)
        if type(approve) is not bool:
            raise LedgerError('approve must be boolean')
        with self._transaction() as (con, rows):
            current = self._current(rows)
            kind = 'revert_approved' if approve else 'revert_rejected'
            return self._append(con, rows, kind, current['state'] if current else {},
                                {'proposal_seq': proposal_seq}, actor, reason)

    def commit_revert(self, proposal_seq, *, actor, reason):
        """Append a compensating record only; never call an external executor."""
        _seq(proposal_seq)
        with self._transaction() as (con, rows):
            if proposal_seq > len(rows) or rows[proposal_seq - 1]['kind'] != 'revert_proposed':
                raise LedgerError('Unknown proposal')
            prop = rows[proposal_seq - 1]
            approval = next((r for r in rows if r['kind'] == 'revert_approved'
                             and r['payload']['proposal_seq'] == proposal_seq), None)
            if approval is None:
                raise LedgerError('Proposal has not been approved')
            target = rows[prop['payload']['target_seq'] - 1]
            return self._append(con, rows, 'revert_committed', target['state'],
                                {'proposal_seq': proposal_seq, 'approval_seq': approval['seq'],
                                 'target_seq': target['seq'], 'target_hash': target['hash']}, actor, reason)

## Links from
- [[test_audit_ledger]]

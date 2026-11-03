---
slug: test_real_data_views
type: note
graph: gitnexus
---

"""Offline source-integrity contracts; fakes here never enter production."""
import importlib
import json
import sqlite3
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import mobile_view as mobile
import event_journal as journal


def test_mobile_does_not_claim_fresh_market_quotes_or_invent_values():
    with patch.object(mobile, '_account', return_value=None), \
         patch.object(mobile, '_positions', return_value=None), \
         patch.object(mobile, '_flags', return_value={}), \
         patch.object(mobile, '_recent_events', return_value=None):
        rendered = mobile.get_mobile_html()
    assert 'Unavailable' in rendered
    assert 'live ·' not in rendered
    assert 'freshness' in rendered.lower()
    assert 'UTC' in rendered
    for text in ('FX Flow', '10:42', 'Paper Mode', '+0.4%', 'EUR/USD Momentum'):
        assert text not in rendered
    assert '<button' not in rendered


def test_mobile_escapes_real_broker_fields_and_labels_currency():
    acct = dict(login=1, server='<script>bad</script>', balance=123.45,
                equity=124.56, profit=1.11, free=100, type='demo', currency='EUR')
    with patch.object(mobile, '_account', return_value=acct), \
         patch.object(mobile, '_positions', return_value=[]), \
         patch.object(mobile, '_flags', return_value={}), \
         patch.object(mobile, '_recent_events', return_value=[]):
        rendered = mobile.get_mobile_html()
    assert '123.45' in rendered and 'EUR' in rendered
    assert '<script>' not in rendered
    assert '&lt;script&gt;' in rendered


def test_journal_uses_persisted_event_ids_not_log_inference(tmp_path, monkeypatch):
    path = tmp_path / 'events.db'
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE events (event_id TEXT, ts TEXT, type TEXT, source TEXT, payload TEXT, trace_id TEXT)')
        con.execute('INSERT INTO events VALUES(?,?,?,?,?,?)', (
            'e1', '2026-10-17T10:00:00Z', 'order_placed', 'executor',
            json.dumps({'ticket': 123, 'symbol': 'EURUSD', 'detail': 'submitted, not filled'}), 'trace1'))
        con.execute('INSERT INTO events VALUES(?,?,?,?,?,?)', (
            'e2', '2026-10-17T10:00:01Z', 'pnl_update', 'manage', '{}', 'trace1'))
    monkeypatch.setattr(journal, 'DB_PATH', str(path))
    snapshot = journal.journal()
    assert snapshot["available"] is True
    rows = snapshot["events"]
    assert len(rows) == 1
    assert rows[0]['event_id'] == 'e1' and rows[0]['trace_id'] == 'trace1'
    assert rows[0]['source'] == 'executor'
    assert rows[0]['data_source'] == 'signals.db:events'
    assert 'submitted, not filled' in rows[0]['detail']


def test_journal_empty_or_missing_is_not_fabricated(tmp_path, monkeypatch):
    path = tmp_path / 'not-created.db'
    monkeypatch.setattr(journal, 'DB_PATH', str(path))
    assert journal.get_events() == []
    assert journal.journal()["available"] is False
    assert not path.exists(), 'read-only queries must not create a missing DB'


def test_journal_preserves_ledger_status_and_does_not_guess_timezone(tmp_path, monkeypatch):
    path = tmp_path / 'ledger.db'
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE trades (id INTEGER, ts TEXT, symbol TEXT, side TEXT, status TEXT, detail TEXT)')
        con.execute('INSERT INTO trades VALUES(?,?,?,?,?,?)', (
            1, '2026-10-17T09:00:00', 'XAUUSD', 'buy', 'skipped_risk', 'not an execution'))
    monkeypatch.setattr(journal, 'DB_PATH', str(path))
    rows = journal.get_events()
    assert len(rows) == 1 and rows[0]['event'] == 'trade skipped_risk'
    assert rows[0]['time'] == '2026-10-17T09:00:00'
    assert rows[0]['timestamp_basis'] == 'source as recorded; timezone unspecified'
    assert rows[0]['data_source'] == 'signals.db:trades'


def test_journal_bad_json_does_not_hide_other_records(tmp_path, monkeypatch):
    path = tmp_path / 'events.db'
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE events (event_id TEXT, ts TEXT, type TEXT, source TEXT, payload TEXT, trace_id TEXT)')
        for index, payload in enumerate(('not json', '{"detail":"observed"}')):
            con.execute('INSERT INTO events VALUES(?,?,?,?,?,?)', (
                str(index), f'2026-10-17T10:00:0{index}Z', 'alert', 'test', payload, 'trace'))
    monkeypatch.setattr(journal, 'DB_PATH', str(path))
    rows = journal.get_events()
    assert len(rows) == 2 and rows[0]['detail'] == 'observed'
    assert rows[1]['payload_available'] is False


def test_bridge_default_uses_shared_extractor_and_abstains_on_failure(monkeypatch):
    from scalp360_bridge import make_bridge
    import ai_filter
    b = make_bridge(':memory:')
    try:
        monkeypatch.setattr(ai_filter, 'llm_extract', lambda text: (None, 'no LLM key in .env'))
        result = b.ai_extract('actual source text')
        assert result.kind == 'UNKNOWN'
        assert 'no LLM key' in result.abstained_reason
        assert result.symbol is None
    finally:
        b.db.close()


def test_bridge_only_reports_extraction_with_real_adapter_result(monkeypatch):
    from scalp360_bridge import make_bridge
    import ai_filter
    b = make_bridge(':memory:')
    text = 'BUY EURUSD at market'
    try:
        monkeypatch.setattr(ai_filter, 'llm_extract', lambda raw: (
            {'is_signal': True, 'action': 'buy', 'symbol': 'EURUSD', 'confidence': .9},
            'injected offline test transport'))
        result = b.ai_extract(text)
        assert result.kind == 'NEW_ENTRY' and result.symbol == 'EURUSD'
        assert result.evidence['raw'] == text
        assert result.side == 'BUY'
    finally:
        b.db.close()


@pytest.mark.parametrize('confidence', [0.1, float('nan'), float('inf')])
def test_bridge_refuses_uncertain_or_nonfinite_confidence(monkeypatch, confidence):
    from scalp360_bridge import make_bridge
    import ai_filter
    b = make_bridge(':memory:')
    try:
        monkeypatch.setattr(ai_filter, 'llm_extract', lambda raw: (
            {'is_signal': True, 'action': 'buy', 'symbol': 'EURUSD', 'confidence': confidence}, 'test'))
        assert b.ai_extract('BUY EURUSD').kind == 'UNKNOWN'
    finally:
        b.db.close()


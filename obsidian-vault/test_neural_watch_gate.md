---
slug: test_neural_watch_gate
type: note
graph: gitnexus
---

"""Offline watch/gate regressions; no broker or live database attachment."""
import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.modules['MetaTrader5'] = types.ModuleType('MetaTrader5')
events = types.ModuleType('event_bus')
events.bus = types.SimpleNamespace(publish=lambda *a, **k: None)
sys.modules['event_bus'] = events
import neural_label_collector as nlc
from scalp360.neural import EvalReport

class WatchGateTests(unittest.TestCase):
    def test_unverified_labels_cannot_promote(self):
        scratch = Path.home() / '.hermes/cache/scratch'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as tmp:
            db = str(Path(tmp) / 'signals.db')
            con = nlc._conn(db)
            con.execute('CREATE TABLE IF NOT EXISTS trades(ticket INTEGER, status TEXT)')
            con.commit()
            con.close()
            promoted = EvalReport(240, 48, 60, .9, .6, .9, 12, 20, 'PROMOTE')
            with patch.object(nlc, 'run_evaluation', return_value=promoted):
                report = nlc.evaluate_collection_gate(db)
            self.assertEqual(report['decision'], 'CONTINUE')
            self.assertFalse(report['shadow_model_activated'])
            self.assertEqual(json.loads(Path(db + '.neural_eval.json').read_text())['decision'], 'CONTINUE')

    def test_watch_evaluates_threshold_once_per_count(self):
        with patch.object(nlc.os.path, 'exists', side_effect=[False, False, False, False, True]), \
             patch.object(nlc, 'backfill_once', return_value=dict(entries=0, closes=0, errors=0)), \
             patch.object(nlc, 'label_counts', return_value=dict(total=300, complete=300, pending=0)), \
             patch.object(nlc, 'evaluate_collection_gate') as gate, \
             patch.object(nlc.time, 'sleep'):
            nlc.watch(0)
            self.assertEqual(gate.call_count, 1)

    def test_stop_exits_before_collection(self):
        with patch.object(nlc.os.path, 'exists', return_value=True), \
             patch.object(nlc, 'backfill_once') as backfill:
            nlc.watch(0)
            backfill.assert_not_called()

    def test_no_order_api_in_collector(self):
        source = Path(nlc.__file__).read_text()
        self.assertNotIn('.order_send(', source)
        self.assertNotIn('.order_check(', source)

if __name__ == '__main__':
    unittest.main()


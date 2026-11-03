"""Offline regression fixtures only; no production DB/broker/orders."""
import json
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

import neural_pipeline as p


class PipelineTests(unittest.TestCase):
    def setUp(self):
        scratch = Path.home()/'.hermes/cache/scratch'
        scratch.mkdir(parents=True,exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.db = str(Path(self.tmp.name)/'test.db')
        with p.connect(self.db) as c:
            c.executescript('''CREATE TABLE neural_labels(id INTEGER PRIMARY KEY, ts REAL,
              symbol TEXT,side TEXT,entry REAL,sl REAL,tp REAL,outcome INTEGER,features TEXT);
              CREATE TABLE neural_label_map(ticket INTEGER PRIMARY KEY,label_id INTEGER);
              CREATE TABLE trades(ticket INTEGER,status TEXT,symbol TEXT,side TEXT,lot REAL);''')
        self.now = time.time()-1000
        self.deals = [NS(ticket=1,order=10,position_id=20,symbol='EURUSD',entry=0,
                         type=0,magic=20261014,volume=.1,time=self.now,price=1.1,
                         profit=0,commission=-1,swap=0,fee=-.1),
                      NS(ticket=2,order=11,position_id=20,symbol='EURUSD',entry=1,
                         type=1,magic=20261014,volume=.1,time=self.now+100,price=1.2,
                         profit=10,commission=-1,swap=-.2,fee=-.1)]
        self.broker = NS(positions_get=lambda:[], history_orders_get=lambda **k:[NS(position_id=20)],
                         history_deals_get=lambda **k:self.deals)
        with p.connect(self.db) as c:
            c.execute('INSERT INTO neural_labels VALUES(1,?,?,?,?,?,?,?,?)',
                      (self.now,'EURUSD','buy',1.1,1.,1.2,1,json.dumps({'entry':1.1,'rsi14':60})))
            c.execute('INSERT INTO neural_label_map VALUES(10,1)')
            c.execute("INSERT INTO trades VALUES(10,'executed','EURUSD','buy',.1)")

    def tearDown(self):
        self.tmp.cleanup()

    def test_verified_cash_includes_fees_and_trade_fingerprint(self):
        self.assertEqual(p.reconcile(self.db,self.broker),{'verified':1,'quarantined':0})
        with p.connect(self.db) as c:
            rows = p.verified_rows(c)
            self.assertEqual(len(rows),1)
            self.assertAlmostEqual(rows[0]['evidence']['net_cash'],7.6)
            self.assertAlmostEqual(rows[0]['evidence']['cost_cash'],2.4)
            c.execute("UPDATE trades SET status='rejected'")
            self.assertEqual(p.verified_rows(c),[])

    def test_orphan_outcome_mismatch_partial_and_missing_history(self):
        for change in ('orphan','outcome','partial','unavailable','wrongmagic'):
            with self.subTest(change=change):
                self.setUp_case = None
                with p.connect(self.db) as c:
                    c.execute('UPDATE neural_labels SET outcome=?',(0 if change=='outcome' else 1,))
                    c.execute('UPDATE neural_label_map SET ticket=?',(999 if change=='orphan' else 10,))
                self.deals[1].volume = .05 if change=='partial' else .1
                self.deals[0].magic = 1 if change=='wrongmagic' else 20261014
                self.broker.history_deals_get = lambda **k: None if change=='unavailable' else self.deals
                self.assertEqual(p.reconcile(self.db,self.broker)['verified'],0)

    def test_mutated_label_and_stale_audit_excluded(self):
        p.reconcile(self.db,self.broker)
        with p.connect(self.db) as c:
            c.execute('UPDATE neural_outcome_audit SET checked_at=0')
            self.assertEqual(p.verified_rows(c),[])
        p.reconcile(self.db,self.broker)
        with p.connect(self.db) as c:
            c.execute("UPDATE neural_labels SET features='{}'")
            self.assertEqual(p.verified_rows(c),[])

    def test_health_read_only_and_no_promotion_without_rows(self):
        p.reconcile(self.db,self.broker)
        result = p.health(self.db)
        self.assertEqual(result['verified_labels'],1)
        self.assertFalse(result['live_execution_enabled'])
        self.assertIsNone(p.train_if_due(self.db))
        self.assertEqual(p.promote_if_ready(self.db),[])
        missing = str(Path(self.tmp.name)/'missing.db')
        self.assertEqual(p.health(missing)['status'],'unavailable')
        self.assertFalse(Path(missing).exists())

    def test_health_http_route_is_authenticated_and_read_only(self):
        import http.client
        import threading
        from http.server import ThreadingHTTPServer
        from cockpit_runtime import CockpitHandler
        p.reconcile(self.db,self.broker)
        handler = type('NeuralHealthHandler',(CockpitHandler,),{'backend':NS(DB=self.db)})
        server = ThreadingHTTPServer(('127.0.0.1',0),handler)
        server.cockpit_token = 'offline-fixture'
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            for suffix,authorized,expected in [('',False,401),('',True,200),('?bad=1',True,400)]:
                conn = http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=3)
                conn.request('GET','/api/neural.health'+suffix,
                             headers={'Authorization':'Bearer offline-fixture'} if authorized else {})
                response = conn.getresponse()
                body = response.read()
                self.assertEqual(response.status,expected,body)
                if expected == 200:
                    self.assertEqual(json.loads(body)['verified_labels'],1)
                conn.close()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(3)

    def test_training_cadence_and_artifact_are_durable(self):
        rows = [dict(id=i,ticket=i,ts=i*10,x=(float(i%2),),y=i%2,
                     evidence=dict(position_id=i,closed_at=i*10+1,
                                   net_cash=2 if i%2 else -1,cost_cash=.1)) for i in range(400)]
        with patch.object(p,'verified_rows',return_value=rows[:300]):
            first = p.train_if_due(self.db)
            self.assertEqual(first['version'],1)
            self.assertGreaterEqual(first['holdout_auc'],.58)
            self.assertIsNone(p.train_if_due(self.db))
        with patch.object(p,'verified_rows',return_value=rows[:399]):
            self.assertIsNone(p.train_if_due(self.db))
        with patch.object(p,'verified_rows',return_value=rows):
            self.assertEqual(p.train_if_due(self.db)['version'],2)
        with p.connect(self.db) as c:
            versions = c.execute('SELECT * FROM neural_model_versions').fetchall()
            self.assertEqual(len(versions),2)
            self.assertEqual(versions[0]['state'],'shadow')
            artifact = json.loads(versions[0]['artifact'])
            self.assertIn('threshold',artifact)
            self.assertEqual(p.promote_if_ready(self.db),[])

    def test_promote_requires_100_future_verified_shadow_outcomes(self):
        import hashlib
        now = time.time()
        rows = [dict(id=i,x=(float(i),),y=int(i<75),evidence=dict(
                    closed_at=now+10,net_cash=2 if i<75 else -1)) for i in range(100)]
        with p.connect(self.db) as c:
            c.execute('''INSERT INTO neural_model_versions(created_at,n_labels,dataset_hash,state,
              artifact,metrics,mlflow_run_id) VALUES(?,300,'promote-fixture','shadow','{}',?,?)''',
                      (now-100,json.dumps({'holdout_pass':True}),'offline-fixture-run'))
            for r in rows[:99]:
                c.execute('INSERT INTO neural_shadow_predictions VALUES(?,?,?,?,?,?)',
                          (1,r['id'],now,.9 if r['y'] else .1,r['y'],
                           hashlib.sha256(json.dumps(list(r['x'])).encode()).hexdigest()))
        with patch.object(p,'verified_rows',return_value=rows):
            self.assertEqual(p.promote_if_ready(self.db),[])
            r = rows[-1]
            with p.connect(self.db) as c:
                c.execute('INSERT INTO neural_shadow_predictions VALUES(?,?,?,?,?,?)',
                          (1,r['id'],now,.1,0,hashlib.sha256(json.dumps(list(r['x'])).encode()).hexdigest()))
            self.assertEqual(p.promote_if_ready(self.db),[1])
        with p.connect(self.db) as c:
            self.assertEqual(c.execute('SELECT state FROM neural_model_versions').fetchone()[0],'promoted')

    def test_shadow_requires_fresh_unclosed_label(self):
        artifact = dict(w=[1],b=0,mean=[0],scale=[1],threshold=.5)
        with p.connect(self.db) as c:
            c.execute('''INSERT INTO neural_model_versions(created_at,n_labels,dataset_hash,state,
              artifact,metrics) VALUES(?,300,'fixture','shadow',?,'{}')''',
                      (time.time()-50,json.dumps(artifact)))
            c.execute('UPDATE neural_labels SET ts=?,outcome=NULL',(time.time(),))
        self.assertEqual(p.shadow_observe(self.db,1,(1.,)),1)
        self.assertEqual(p.shadow_observe(self.db,1,(1.,)),0)
        with p.connect(self.db) as c:
            c.execute('UPDATE neural_labels SET outcome=1')
        self.assertEqual(p.shadow_observe(self.db,1,(1.,)),0)

if __name__ == '__main__':
    unittest.main()

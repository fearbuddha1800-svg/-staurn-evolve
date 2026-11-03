"""Isolated offline adapter tests; no broker, live labels or cloud provisioning."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError
import cloudroom_offload as c


class OffloadTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(os.environ.get("TMPDIR", Path.home() / ".hermes/cache/scratch"))
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch, prefix="cloudroom-test-")
        self.root = Path(self.temp.name)
        self.state = self.root / "state"
        (self.root / "work.py").write_text("import os,json; print(json.dumps({'value':sum(range(100)), 'device':os.getenv('PROJECT_COMPUTE_DEVICE'), 'secret':os.getenv('CLOUDROOM_TOKEN')}))", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def job(self, **kwargs):
        return c.Job(target="data_processing", entrypoint="work.py", **kwargs)

    def test_real_queue_fallback_and_costs(self):
        with patch.dict(os.environ, {"CLOUDROOM_TOKEN": "test-secret", "CLOUDROOM_LOCAL_CPU_USD_PER_HOUR": "0.36"}):
            ids = [c.submit(self.job(), self.state, self.root) for _ in range(5)]
            outcome = c.drain(self.state, self.root, max_workers=2, jobs_per_worker=2)
        self.assertEqual(outcome["completed"], 5)
        self.assertEqual(outcome["worker_targets"][0], 2)
        self.assertEqual(outcome["worker_targets"][-1], 0)
        report = c.report(self.state)
        self.assertEqual(len(report["jobs"]), 5)
        self.assertGreater(report["local_estimated_cost_usd"], 0)
        self.assertEqual(report["remote_cost_usd"], 0)
        for job in report["jobs"]:
            self.assertEqual(job["status"], "succeeded")
            self.assertFalse(job["result"]["remote_submitted"])
            self.assertIn("No verified", job["result"]["fallback_reason"])
        for job_id in ids:
            output = json.loads((self.state / f"{job_id}.stdout.log").read_text())
            self.assertEqual(output, {"value": 4950, "device": "cpu", "secret": None})

    def test_explicit_remote_no_fallback_is_blocked(self):
        for backend in ["cloudroom", "auto"]:
            with self.assertRaises(ValueError):
                c.submit(self.job(backend=backend, allow_local_fallback=False), self.state, self.root)
        self.assertFalse(self.state.exists())

    def test_strict_manifest(self):
        for invalid in [{"timeout_seconds": "3"}, {"target": "live_trade"}, {"unexpected": True}]:
            with self.assertRaises(ValidationError):
                c.Job.model_validate({"target": "data_processing", "entrypoint": "work.py", **invalid})

    def test_paths_and_shell_are_not_interpreted(self):
        with self.assertRaises(ValueError):
            c.submit(c.Job(target="data_processing", entrypoint="../escape.py"), self.state, self.root)
        job_id = c.submit(self.job(backend="local", args=["; echo no-shell"]), self.state, self.root)
        c.drain(self.state, self.root)
        self.assertEqual(json.loads((self.state / f"{job_id}.stdout.log").read_text())["value"], 4950)

    def test_timeout_and_failure_are_persisted(self):
        (self.root / "slow.py").write_text("import time; time.sleep(30)")
        (self.root / "fail.py").write_text("raise SystemExit(7)")
        c.submit(c.Job(target="data_processing", entrypoint="slow.py", timeout_seconds=1), self.state, self.root)
        c.submit(c.Job(target="data_processing", entrypoint="fail.py"), self.state, self.root)
        c.drain(self.state, self.root)
        self.assertEqual({j["status"] for j in c.report(self.state)["jobs"]}, {"timed_out", "failed"})

    def test_no_rate_is_unknown_not_free(self):
        with patch.object(c, "settings", return_value={}):
            c.submit(self.job(), self.state, self.root)
            c.drain(self.state, self.root)
        self.assertIsNone(c.report(self.state)["local_estimated_cost_usd"])

    def test_worker_lock_and_interrupted_job(self):
        job_id = c.submit(self.job(), self.state, self.root)
        with c.db_open(self.state) as db:
            db.execute("UPDATE jobs SET status='running' WHERE id=?", (job_id,))
        with self.assertRaises(RuntimeError):
            c.drain(self.state, self.root)
        self.assertFalse((self.state / "worker.lock").exists())
        (self.state / "worker.lock").touch()
        with self.assertRaises(FileExistsError):
            c.drain(self.state, self.root)

    def test_scaling_bounds(self):
        self.assertEqual([c.desired_workers(d, 3, 2) for d in (0, 1, 2, 3, 6, 99)], [0, 1, 1, 2, 3, 3])
        for args in [(-1, 2, 2), (1, 0, 2), (1, 33, 2), (1, 2, 0)]:
            with self.assertRaises(ValueError):
                c.desired_workers(*args)

    def test_pine_manifest(self):
        for file in ("pinets_bridge.js", "strategy.pine", "candles.json"):
            (self.root / file).touch()
        cmd = c.command(c.Job(target="backtest_batch", args=["strategy.pine", "candles.json", "TEST", "60"]), self.root)
        self.assertEqual(cmd[0], "node")
        self.assertEqual(cmd[-2:], ["TEST", "60"])

    def test_probe_rejects_external_token_destination(self):
        with patch.object(c, "settings", return_value={"CLOUDROOM_BASE_URL": "https://example.com", "CLOUDROOM_TOKEN": "secret"}):
            self.assertFalse(c.probe()["compute_ready"])
            self.assertIn("loopback", c.probe()["blocker"])

    def test_empty_report_does_not_write(self):
        self.assertEqual(c.report(self.state)["jobs"], [])
        self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main()

"""Offline research queue and Cloudroom readiness adapter; never imported by trading.

Cloudroom here is a local WSL agent service, NOT a verified compute provider.
Remote submission is deliberately blocked. CLI manifests are trusted local code.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import json
import math
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
from typing import Literal
import urllib.error
import urllib.parse
import urllib.request
import uuid

from pydantic import BaseModel, ConfigDict, Field

ROOT = Path(__file__).resolve().parent
BLOCKER = "No verified Cloudroom compute job/provisioning API, remote runtime or pricing contract"
TARGETS = {
    "neural_training": {"runtime": "Python/PyTorch (operator-supplied offline script)", "preferred": "gpu", "fallback": "local_cpu", "input": "approved immutable training export; no live database", "promotion": "never automatic; preserve existing evaluation/provenance gates"},
    "backtest_batch": {"runtime": "Node/PineTS pinets_bridge.js", "preferred": "cpu", "fallback": "local_cpu", "input": "strategy file and exported closed-candle JSON; no MT5 attachment"},
    "data_processing": {"runtime": "Python (operator-supplied offline script)", "preferred": "cpu", "fallback": "local_cpu", "input": "explicit offline export files"},
}


class Job(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    target: Literal["neural_training", "backtest_batch", "data_processing"]
    entrypoint: str | None = None
    args: list[str] = Field(default_factory=list, max_length=100)
    timeout_seconds: int = Field(default=300, ge=1, le=86400)
    backend: Literal["auto", "local", "cloudroom"] = "auto"
    allow_local_fallback: bool = True


def settings(env_file: Path = ROOT / ".env.cloudroom") -> dict[str, str]:
    """Read only this adapter's settings; never export secrets into job children."""
    values = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            key, sep, value = line.partition("=")
            if sep and key.strip().startswith("CLOUDROOM_"):
                values[key.strip()] = value.strip().strip('"').strip("'")
    values.update({k: v for k, v in os.environ.items() if k.startswith("CLOUDROOM_")})
    return values


def probe() -> dict:
    cfg = settings()
    base = cfg.get("CLOUDROOM_BASE_URL", "http://127.0.0.1:9840")
    parsed = urllib.parse.urlsplit(base)
    # A local token must never be sent to a configurable external host or redirect.
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        return {"service": "local_wsl", "ready": False, "compute_ready": False, "blocker": "Readiness URL must be a plain HTTP loopback origin"}
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    checks = {}
    for path in ("/v1/health", "/v1/ready"):
        request = urllib.request.Request(base.rstrip("/") + path, headers={"Authorization": "Bearer " + cfg.get("CLOUDROOM_TOKEN", "")})
        try:
            with opener.open(request, timeout=2) as response:
                checks[path] = {"http_status": response.status}
        except urllib.error.HTTPError as error:
            checks[path] = {"http_status": error.code}
        except (OSError, ValueError):
            checks[path] = {"error": "unreachable"}
    return {"service": "local_wsl", "ready": all(c.get("http_status") == 200 for c in checks.values()), "checks": checks, "compute_ready": False, "remote_provisioning_enabled": False, "blocker": BLOCKER}


def confined(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("Entrypoint/input must be an existing file inside the research workspace")
    return path


def command(job: Job, root: Path) -> list[str]:
    if job.target == "backtest_batch":
        if job.entrypoint is not None or len(job.args) not in (2, 3, 4):
            raise ValueError("PineTS needs args [strategy, candles, optional symbol, optional timeframe], no entrypoint")
        inputs = [str(confined(root, arg)) for arg in job.args[:2]]
        return ["node", str(confined(root, "pinets_bridge.js")), *inputs, *job.args[2:]]
    if not job.entrypoint:
        raise ValueError("Python research targets require an explicit reviewed offline entrypoint")
    script = confined(root, job.entrypoint)
    if script.suffix != ".py":
        raise ValueError("Python entrypoint must be a .py file")
    return [sys.executable, str(script), *job.args]


@contextmanager
def db_open(state: Path):
    state.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(state / "queue.sqlite3", timeout=10)
    try:
        db.row_factory = sqlite3.Row
        db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, spec TEXT NOT NULL, status TEXT NOT NULL, created REAL NOT NULL, result TEXT)")
        db.commit()
        with db:
            yield db
    finally:
        db.close()


def submit(job: Job, state: Path, root: Path = ROOT) -> str:
    command(job, root)  # validate before enqueuing
    if job.backend != "local" and not job.allow_local_fallback:
        raise ValueError(BLOCKER)
    job_id = uuid.uuid4().hex
    with db_open(state) as db:
        db.execute("INSERT INTO jobs VALUES (?, ?, 'queued', ?, NULL)", (job_id, job.model_dump_json(), time.time()))
    return job_id


def desired_workers(depth: int, max_workers: int = 2, jobs_per_worker: int = 2) -> int:
    if depth < 0 or not 1 <= max_workers <= 32 or jobs_per_worker < 1:
        raise ValueError("Invalid scaling bounds")
    return min(max_workers, math.ceil(depth / jobs_per_worker))


def child_environment() -> dict[str, str]:
    # Do not pass Cloudroom, broker, exchange, Telegram or arbitrary parent secrets.
    names = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "USERPROFILE", "HOME", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "TMPDIR", "VIRTUAL_ENV", "PYTHONHOME", "NODE_PATH"}
    env = {k: v for k, v in os.environ.items() if k.upper() in names}
    env.update(CUDA_VISIBLE_DEVICES="", PROJECT_COMPUTE_DEVICE="cpu", OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", PYTHONUNBUFFERED="1")
    return env


def execute(job_id: str, job: Job, state: Path, root: Path = ROOT) -> dict:
    started = time.monotonic()
    fallback = BLOCKER if job.backend != "local" else None
    result = {"backend": "local_cpu", "fallback_reason": fallback, "remote_submitted": False, "remote_cost_usd": 0, "local_estimated_cost_usd": None}
    try:
        args = command(job, root)
        with (state / f"{job_id}.stdout.log").open("wb") as out, (state / f"{job_id}.stderr.log").open("wb") as err:
            proc = subprocess.Popen(args, cwd=root, env=child_environment(), stdout=out, stderr=err,
                                    start_new_session=os.name != "nt", creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            try:
                code = proc.wait(timeout=job.timeout_seconds)
                result.update(status="succeeded" if code == 0 else "failed", exit_code=code)
            except subprocess.TimeoutExpired:
                if os.name == "nt":
                    subprocess.run(["taskkill.exe", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=15, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.wait(timeout=10)
                result.update(status="timed_out")
    except Exception as error:
        result.update(status="failed", error=type(error).__name__)
    result["wall_seconds"] = round(time.monotonic() - started, 6)
    raw_rate = settings().get("CLOUDROOM_LOCAL_CPU_USD_PER_HOUR", "")
    if raw_rate:
        try:
            rate = float(raw_rate)
            if math.isfinite(rate) and rate >= 0:
                result["local_estimated_cost_usd"] = result["wall_seconds"] * rate / 3600
        except ValueError:
            pass
    result["artifacts"] = [f"{job_id}.stdout.log", f"{job_id}.stderr.log"]
    return result


def drain(state: Path, root: Path = ROOT, max_workers: int = 2, jobs_per_worker: int = 2) -> dict:
    """One controller, bounded queue-depth scaling, idle-to-zero. No cloud autoscaler."""
    desired_workers(0, max_workers, jobs_per_worker)
    state.mkdir(parents=True, exist_ok=True)
    lock = state / "worker.lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    transitions, completed = [], 0
    try:
        with db_open(state) as db, ThreadPoolExecutor(max_workers=max_workers) as pool:
            if db.execute("SELECT count(*) FROM jobs WHERE status='running'").fetchone()[0]:
                raise RuntimeError("Interrupted running jobs require manual inspection; never automatically replay")
            active = {}
            while True:
                queued = db.execute("SELECT count(*) FROM jobs WHERE status='queued'").fetchone()[0]
                desired = desired_workers(queued + len(active), max_workers, jobs_per_worker)
                if not transitions or transitions[-1] != desired:
                    transitions.append(desired)
                while queued and len(active) < desired:
                    row = db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created LIMIT 1").fetchone()
                    db.execute("UPDATE jobs SET status='running' WHERE id=?", (row["id"],))
                    db.commit()
                    future = pool.submit(execute, row["id"], Job.model_validate_json(row["spec"]), state, root)
                    active[future] = row["id"]
                    queued -= 1
                if not active:
                    break
                finished, _ = wait(active, return_when=FIRST_COMPLETED)
                for future in finished:
                    result = future.result()
                    db.execute("UPDATE jobs SET status=?, result=? WHERE id=?", (result["status"], json.dumps(result), active.pop(future)))
                    db.commit()
                    completed += 1
        return {"completed": completed, "worker_targets": transitions, "remote_provisioned": 0}
    finally:
        lock.unlink()


def report(state: Path) -> dict:
    if not (state / "queue.sqlite3").exists():
        return {"jobs": [], "remote_cost_usd": 0, "local_estimated_cost_usd": None, "pricing": "not configured"}
    # Read-only MCP reporting must not create or mutate the queue.
    uri = (state / "queue.sqlite3").resolve().as_uri() + "?mode=ro"
    db = sqlite3.connect(uri, uri=True, timeout=10)
    try:
        rows = db.execute("SELECT id,status,result FROM jobs ORDER BY created").fetchall()
    finally:
        db.close()
    jobs = [{"id": i, "status": s, "result": json.loads(r) if r else None} for i, s, r in rows]
    results = [j["result"] for j in jobs if j["result"]]
    estimates = [r["local_estimated_cost_usd"] for r in results]
    return {"jobs": jobs, "remote_cost_usd": 0, "local_estimated_cost_usd": sum(estimates) if estimates and all(e is not None for e in estimates) else None, "pricing": "local estimates only; remote unavailable", "measured_wall_seconds": sum(r["wall_seconds"] for r in results)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=ROOT / ".cloudroom-state")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    sub.add_parser("targets")
    sub.add_parser("report")
    add = sub.add_parser("submit")
    add.add_argument("manifest", type=Path)
    worker = sub.add_parser("drain")
    worker.add_argument("--max-workers", type=int, default=2)
    worker.add_argument("--jobs-per-worker", type=int, default=2)
    args = parser.parse_args()
    if args.action == "status":
        result = probe()
    elif args.action == "targets":
        result = TARGETS
    elif args.action == "submit":
        result = {"job_id": submit(Job.model_validate_json(args.manifest.read_text(encoding="utf-8")), args.state)}
    elif args.action == "drain":
        result = drain(args.state, max_workers=args.max_workers, jobs_per_worker=args.jobs_per_worker)
    else:
        result = report(args.state)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

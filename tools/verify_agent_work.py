"""Run fixed offline checks and retain their real output; never execute task text."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHECKS = {
    "controller": ([sys.executable, "-m", "pytest", "tools/test_agent_master.py", "-q"],
                   ["tools/agent_master.py", "tools/test_agent_master.py"]),
    "offline": ([sys.executable, "-m", "pytest", "tools/test_ea_readiness.py",
                 "mql5-training/offline_tests", "-q"],
                ["tools/ea_readiness.py", "tools/test_ea_readiness.py",
                 "mql5-training/offline_pipeline.py", "mql5-training/offline_tests",
                 "mql5-training/source_manifest.json", "mql5-training/curated"]),
    "ea-source": ([sys.executable, "tools/ea_readiness.py"],
                  ["Hybrid_Microstructure_EA_V1.0.mq5", "ResearchFramework.mq5",
                   "HybridMicrostructure"]),
    "ea-entry": ([sys.executable, "tools/ea_readiness.py",
                  "Hybrid_Microstructure_EA_V1.0.mq5"],
                 ["Hybrid_Microstructure_EA_V1.0.mq5",
                  "HybridMicrostructure/ParamUX.mqh", "HybridMicrostructure/AIBridge.mqh",
                  "HybridMicrostructure/AIBridgeUX.mqh",
                  "HybridMicrostructure/AISignalsEngineFailClosed.mqh"]),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snapshot(root: Path, paths: list[str]) -> dict[str, str]:
    hashes = {}
    for name in paths:
        path = root / name
        candidates = (sorted(p for p in path.rglob("*") if p.is_file()
                             and p.suffix in {".mqh", ".mq5", ".py", ".txt", ".json"})
                      if path.is_dir() else [path])
        for candidate in candidates:
            if not candidate.resolve().is_relative_to(root.resolve()):
                raise ValueError("Check source escapes project root")
            hashes[str(candidate.relative_to(root))] = digest(candidate.read_bytes())
    return hashes


def run_check(name: str, root: Path = ROOT) -> tuple[Path, dict]:
    if name not in CHECKS:
        raise ValueError("Unknown check; arbitrary commands are not supported")
    command, paths = CHECKS[name]
    before = snapshot(root, paths)
    directory = root / ".cloudroom-state" / "verification" / uuid.uuid4().hex
    if not directory.resolve().is_relative_to(root.resolve()):
        raise ValueError("Evidence directory escapes project root")
    directory.mkdir(parents=True)
    timed_out = False
    try:
        result = subprocess.run(command, cwd=root, capture_output=True, timeout=120,
                                check=False, shell=False)
        stdout, stderr, code = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as error:
        stdout, stderr, code = error.stdout or b"", error.stderr or b"", None
        timed_out = True
    after = snapshot(root, paths)
    (directory / "stdout.txt").write_bytes(stdout)
    (directory / "stderr.txt").write_bytes(stderr)
    report = {"schema": 1, "check": name, "command": command,
              "utc": datetime.now(timezone.utc).isoformat(), "exit_code": code,
              "timed_out": timed_out, "sources_before": before, "sources_after": after,
              "passed": code == 0 and before == after and not timed_out,
              "stdout_sha256": digest(stdout), "stderr_sha256": digest(stderr),
              "trust": "local execution record; not cryptographic attestation"}
    manifest = directory / "report.json"
    manifest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return manifest, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=sorted(CHECKS))
    args = parser.parse_args()
    if shutil.which(sys.executable) is None:
        parser.error("Python interpreter unavailable")
    manifest, report = run_check(args.check)
    print(json.dumps({"report": str(manifest), "sha256": digest(manifest.read_bytes()),
                      "passed": report["passed"], "exit_code": report["exit_code"]}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Verification must capture failures and reject source changes and shell input."""
import subprocess
from unittest.mock import patch

import pytest
import verify_agent_work as verifier


def fixture(tmp_path):
    (tmp_path / "source.py").write_text("original")
    return patch.dict(verifier.CHECKS, {"fixture": (["fixed", "argument"], ["source.py"])})


def test_arbitrary_command_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        verifier.run_check("echo bypass; true", tmp_path)
    assert not (tmp_path / ".cloudroom-state").exists()


def test_failure_and_output_retained(tmp_path):
    with fixture(tmp_path), patch.object(subprocess, "run") as execute:
        execute.return_value = subprocess.CompletedProcess([], 3, b"failed test", b"error")
        path, result = verifier.run_check("fixture", tmp_path)
    assert not result["passed"]
    assert result["exit_code"] == 3
    assert (path.parent / "stdout.txt").read_bytes() == b"failed test"
    assert execute.call_args.kwargs["shell"] is False


def test_changed_source_rejects_success(tmp_path):
    def mutate(*args, **kwargs):
        (tmp_path / "source.py").write_text("changed during test")
        return subprocess.CompletedProcess([], 0, b"ok", b"")
    with fixture(tmp_path), patch.object(subprocess, "run", side_effect=mutate):
        _, result = verifier.run_check("fixture", tmp_path)
    assert not result["passed"]


def test_timeout_never_passes(tmp_path):
    with fixture(tmp_path), patch.object(subprocess, "run", side_effect=
                                        subprocess.TimeoutExpired(["fixed"], 120)):
        path, result = verifier.run_check("fixture", tmp_path)
    assert path.is_file()
    assert result["timed_out"] and not result["passed"]


def test_symlinked_evidence_cannot_escape(tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (tmp_path / "project").mkdir()
    project = tmp_path / "project"
    (project / "source.py").write_text("source")
    (project / ".cloudroom-state").symlink_to(elsewhere, target_is_directory=True)
    with fixture(project), pytest.raises(ValueError):
        verifier.run_check("fixture", project)

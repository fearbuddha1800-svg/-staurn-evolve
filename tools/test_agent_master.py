"""Controller behavior, including races and evidence invalidation."""
import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from agent_master import Controller


def task(name, role=None, paths=None, deps=None):
    return {"id": name, "role": role or name, "owned_paths": paths or [name],
            "deps": deps or [], "acceptance": [{"id": "artifact", "path": name,
            "sha256": hashlib.sha256(b"ok").hexdigest()}]}


def setup(tmp_path, tasks, cap=3):
    for t in tasks:
        (tmp_path / t["id"]).write_bytes(b"ok")
    c = Controller(tmp_path / "state.db", tmp_path)
    c.initialize(tasks, cap)
    return c


def test_dependency_and_review(tmp_path):
    c = setup(tmp_path, [task("a"), task("b", deps=["a"])])
    assert [t["state"] for t in c.status()] == ["ready", "pending"]
    with pytest.raises(ValueError):
        c.claim("b", "bob", 60)
    c.claim("a", "alice", 60)
    with pytest.raises(ValueError):
        c.submit("a", "bob")
    c.submit("a", "alice")
    with pytest.raises(ValueError):
        c.review("a", "alice", True)
    c.review("a", "reviewer", True)
    assert [t["state"] for t in c.status()] == ["done", "ready"]
    with sqlite3.connect(c.db) as db:
        assert db.execute("select count(*) from evidence").fetchone()[0] == 2


def test_changed_artifact_and_rejection(tmp_path):
    c = setup(tmp_path, [task("a"), task("b", deps=["a"])])
    c.claim("a", "owner", 60)
    c.submit("a", "owner")
    (tmp_path / "a").write_bytes(b"changed")
    c.review("a", "reviewer", True)
    assert [t["state"] for t in c.status()] == ["blocked", "pending"]
    (tmp_path / "a").write_bytes(b"ok")
    c.claim("a", "owner", 60)
    c.submit("a", "owner")
    c.review("a", "reviewer", False, "needs work")
    assert c.status()[0]["state"] == "blocked"


def test_conflicts_and_cap(tmp_path):
    c = setup(tmp_path, [task("a", "dev", ["src"]),
                         task("b", "dev"), task("c", paths=["src/sub"]), task("d")], 1)
    c.claim("a", "one", 60)
    for name in ["b", "c", "d"]:
        with pytest.raises(ValueError):
            c.claim(name, "two", 60)


@pytest.mark.parametrize("same_role", [True, False])
def test_conflict_independent_of_cap(tmp_path, same_role):
    c = setup(tmp_path, [task("a", "dev", ["src"]),
                         task("b", "dev" if same_role else "qa",
                              ["other"] if same_role else ["src/sub"])])
    c.claim("a", "one", 60)
    with pytest.raises(ValueError):
        c.claim("b", "two", 60)


def test_expiry(tmp_path):
    c = setup(tmp_path, [task("a")])
    c.claim("a", "old", 60)
    with sqlite3.connect(c.db) as db:
        db.execute("update tasks set expires=0")
    with pytest.raises(ValueError):
        c.submit("a", "old")
    c.claim("a", "new", 60)
    assert c.status()[0]["owner"] == "new"


def test_atomic_claim(tmp_path):
    c = setup(tmp_path, [task("a"), task("b")], 1)
    def claim(name):
        try:
            Controller(c.db, tmp_path).claim(name, name, 60)
            return True
        except ValueError:
            return False
    with ThreadPoolExecutor(2) as pool:
        assert sum(pool.map(claim, ["a", "b"])) == 1


@pytest.mark.parametrize("edit", [
    {"deps": ["missing"]}, {"deps": ["a"]}, {"owned_paths": ["../escape"]},
    {"owned_paths": ["/abs"]}, {"acceptance": []}, {"command": "evil"},
])
def test_invalid_specs(tmp_path, edit):
    t = task("a") | edit
    with pytest.raises(ValueError):
        Controller(tmp_path / "state.db", tmp_path).initialize([t])


def test_cycle_and_reinitialization(tmp_path):
    with pytest.raises(ValueError):
        setup(tmp_path, [task("a", deps=["b"]), task("b", deps=["a"])])
    c = setup(tmp_path, [task("a")])
    with pytest.raises(ValueError):
        c.initialize([task("b")])


def test_symlink_escape(tmp_path):
    c = setup(tmp_path, [task("a")])
    (tmp_path / "a").unlink()
    (tmp_path / "a").symlink_to("/etc/passwd")
    c.claim("a", "owner", 60)
    c.submit("a", "owner")
    assert c.status()[0]["state"] == "blocked"


def test_future_artifact_pinned_and_mutation_rejected(tmp_path):
    t = task("future")
    t["acceptance"][0]["sha256"] = None
    c = Controller(tmp_path / "state.db", tmp_path)
    c.initialize([t])
    c.claim("future", "worker", 60)
    (tmp_path / "future").write_text("actual verification report")
    c.submit("future", "worker")
    assert c.status()[0]["state"] == "review"
    (tmp_path / "future").write_text("different report")
    c.review("future", "reviewer", True)
    assert c.status()[0]["state"] == "blocked"


def test_future_artifact_done_and_missing_evidence_rejected(tmp_path):
    t = task("future")
    t["acceptance"][0]["sha256"] = None
    c = Controller(tmp_path / "state.db", tmp_path)
    c.initialize([t])
    c.claim("future", "worker", 60)
    (tmp_path / "future").write_text("report")
    with pytest.raises(ValueError):
        c.review("future", "reviewer", True)
    c.submit("future", "worker")
    c.review("future", "reviewer", True)
    assert c.status()[0]["state"] == "done"


def test_plain_pass_and_missing_record_cannot_complete(tmp_path):
    c = setup(tmp_path, [task("a")])
    c.claim("a", "worker", 60)
    with pytest.raises(TypeError):
        c.submit("a", "worker", passed=True)
    c.submit("a", "worker")
    with sqlite3.connect(c.db) as db:
        db.execute("delete from evidence")
    with pytest.raises(ValueError):
        c.review("a", "reviewer", True)
    assert c.status()[0]["state"] == "review"

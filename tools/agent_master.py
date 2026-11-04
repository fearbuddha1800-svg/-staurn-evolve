"""Local task bookkeeping; hash evidence is integrity, not test attestation."""
import argparse
import hashlib
import json
import re
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path, PurePosixPath


def relative(value):
    if not isinstance(value, str) or not value or "\\" in value or ":" in value:
        raise ValueError("paths must be relative POSIX paths")
    p = PurePosixPath(value)
    if p.is_absolute() or ".." in p.parts or str(p) != value or value == ".":
        raise ValueError("paths must be normalized and contained")
    return value


def overlaps(a, b):
    a, b = a.casefold(), b.casefold()
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def validate(tasks):
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("spec must be a nonempty task array")
    ids = set()
    for t in tasks:
        if not isinstance(t, dict) or set(t) != {"id", "role", "owned_paths", "deps", "acceptance"}:
            raise ValueError("invalid task fields")
        for key in ("id", "role"):
            if not isinstance(t[key], str) or not t[key].strip():
                raise ValueError("id and role must be nonempty strings")
        if t["id"] in ids:
            raise ValueError("duplicate id")
        ids.add(t["id"])
        for key in ("owned_paths", "deps", "acceptance"):
            if not isinstance(t[key], list) or (key != "deps" and not t[key]):
                raise ValueError("invalid task lists")
        for path in t["owned_paths"]:
            relative(path)
        checks = set()
        for a in t["acceptance"]:
            if not isinstance(a, dict) or set(a) != {"id", "path", "sha256"}:
                raise ValueError("acceptance requires id, path, sha256")
            if not isinstance(a["id"], str) or not a["id"] or a["id"] in checks:
                raise ValueError("duplicate or empty acceptance id")
            checks.add(a["id"])
            relative(a["path"])
            if a["sha256"] is not None and (not isinstance(a["sha256"], str) or not re.fullmatch("[0-9a-f]{64}", a["sha256"])):
                raise ValueError("expected lowercase SHA-256")
    graph = {t["id"]: t["deps"] for t in tasks}
    visited, active = set(), set()
    def visit(name):
        if not isinstance(name, str) or name not in graph or name in active:
            raise ValueError("unknown dependency or cycle")
        if name in visited:
            return
        active.add(name)
        for dep in graph[name]:
            visit(dep)
        active.remove(name)
        visited.add(name)
    for name in graph:
        visit(name)


class Controller:
    def __init__(self, db, root):
        self.db, self.root = Path(db).resolve(), Path(root).resolve()

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.db, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def initialize(self, tasks, workers=3):
        validate(tasks)
        if type(workers) is not int or workers < 1:
            raise ValueError("workers must be positive")
        with self.transaction() as db:
            db.execute("CREATE TABLE IF NOT EXISTS config(root TEXT, workers INTEGER)")
            if db.execute("SELECT 1 FROM config").fetchone():
                raise ValueError("already initialized")
            db.execute("CREATE TABLE tasks(id TEXT PRIMARY KEY, spec TEXT, state TEXT, owner TEXT, expires REAL, reason TEXT)")
            db.execute("CREATE TABLE evidence(task TEXT, phase TEXT, checks TEXT, recorded REAL)")
            db.execute("INSERT INTO config VALUES (?, ?)", (str(self.root), workers))
            for t in tasks:
                db.execute("INSERT INTO tasks VALUES (?, ?, 'pending', NULL, NULL, '')",
                           (t["id"], json.dumps(t, sort_keys=True)))

    def refresh(self, db):
        config = db.execute("SELECT * FROM config").fetchone()
        if not config or config["root"] != str(self.root):
            raise ValueError("root differs from initialized root")
        db.execute("UPDATE tasks SET state='blocked', reason='claim expired', owner=NULL, expires=NULL WHERE state='running' AND expires<=?", (time.time(),))
        rows = db.execute("SELECT * FROM tasks ORDER BY id").fetchall()
        done = {r["id"] for r in rows if r["state"] == "done"}
        for r in rows:
            if r["state"] in ("pending", "ready"):
                state = "ready" if set(json.loads(r["spec"])["deps"]) <= done else "pending"
                db.execute("UPDATE tasks SET state=? WHERE id=?", (state, r["id"]))
        return config

    def status(self):
        with self.transaction() as db:
            self.refresh(db)
            return [dict(r) for r in db.execute("SELECT id,state,owner,expires,reason FROM tasks ORDER BY id")]

    def row(self, db, name):
        r = db.execute("SELECT * FROM tasks WHERE id=?", (name,)).fetchone()
        if r is None:
            raise ValueError("unknown task")
        return r

    def claim(self, name, owner, ttl=900):
        if not isinstance(owner, str) or not owner.strip() or type(ttl) is not int or not 1 <= ttl <= 86400:
            raise ValueError("owner required; ttl must be 1..86400 seconds")
        with self.transaction() as db:
            config = self.refresh(db)
            r = self.row(db, name)
            t = json.loads(r["spec"])
            done = {x[0] for x in db.execute("SELECT id FROM tasks WHERE state='done'")}
            if r["state"] not in ("ready", "blocked") or not set(t["deps"]) <= done:
                raise ValueError("task is not claimable")
            running = db.execute("SELECT spec FROM tasks WHERE state='running'").fetchall()
            if len(running) >= config["workers"]:
                raise ValueError("worker cap reached")
            for other in running:
                s = json.loads(other[0])
                if t["role"].casefold() == s["role"].casefold() or any(
                    overlaps(a, b) for a in t["owned_paths"] for b in s["owned_paths"]
                ):
                    raise ValueError("running role/path conflict")
            db.execute("DELETE FROM evidence WHERE task=?", (name,))
            db.execute("UPDATE tasks SET state='running',owner=?,expires=?,reason='' WHERE id=?",
                       (owner, time.time() + ttl, name))

    def verify(self, db, r, phase):
        checks = []
        prior = db.execute("SELECT checks FROM evidence WHERE task=? AND phase='submit'", (r["id"],)).fetchone()
        pinned = {c["id"]: c["observed"] for c in json.loads(prior[0])} if prior else {}
        for a in json.loads(r["spec"])["acceptance"]:
            actual, error = None, ""
            try:
                path = (self.root / a["path"]).resolve()
                if not path.is_relative_to(self.root) or not path.is_file():
                    raise ValueError("artifact outside root or missing")
                digest = hashlib.sha256()
                if path.stat().st_size == 0:
                    raise ValueError("empty artifact")
                with path.open("rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        digest.update(chunk)
                actual = digest.hexdigest()
            except (OSError, ValueError) as exc:
                error = str(exc)
            expected = a["sha256"] if a["sha256"] is not None else (pinned.get(a["id"]) if phase == "review" else actual)
            checks.append(dict(a, observed=actual, error=error, matched=actual is not None and not error and actual == expected))
        db.execute("INSERT INTO evidence VALUES (?, ?, ?, ?)",
                   (r["id"], phase, json.dumps(checks, sort_keys=True), time.time()))
        return all(c["matched"] for c in checks)

    def submit(self, name, owner):
        with self.transaction() as db:
            self.refresh(db)
            r = self.row(db, name)
            if r["state"] != "running" or r["owner"] != owner:
                raise ValueError("live claim owner required")
            passed = self.verify(db, r, "submit")
            db.execute("UPDATE tasks SET state=?,expires=NULL,reason=? WHERE id=?",
                       ("review" if passed else "blocked", "" if passed else "verification failed", name))

    def review(self, name, reviewer, approve, reason=""):
        if not isinstance(reviewer, str) or not reviewer.strip() or type(approve) is not bool:
            raise ValueError("reviewer and boolean decision required")
        if not approve and not reason.strip():
            raise ValueError("rejection reason required")
        with self.transaction() as db:
            self.refresh(db)
            r = self.row(db, name)
            if r["state"] != "review" or reviewer == r["owner"]:
                raise ValueError("separate reviewer required for submitted task")
            recorded = db.execute("SELECT checks FROM evidence WHERE task=? AND phase='submit'", (name,)).fetchone()
            if not recorded or not all(c["matched"] for c in json.loads(recorded[0])):
                raise ValueError("recorded successful verification required")
            passed = self.verify(db, r, "review") if approve else False
            db.execute("UPDATE tasks SET state=?,reason=? WHERE id=?",
                       ("done" if passed else "blocked", json.dumps({"reviewer": reviewer, "reason": reason if not approve else ("approved" if passed else "verification failed")}, sort_keys=True), name))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--root", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("initialize")
    init.add_argument("--spec", required=True)
    init.add_argument("--workers", type=int, default=3)
    commands.add_parser("status")
    for name in ("claim", "submit", "review"):
        p = commands.add_parser(name)
        p.add_argument("id")
        if name == "review":
            p.add_argument("--reviewer", required=True)
            p.add_argument("--decision", choices=("approve", "reject"), required=True)
            p.add_argument("--reason", default="")
        else:
            p.add_argument("--owner", required=True)
        if name == "claim":
            p.add_argument("--ttl", type=int, default=900)
    args = parser.parse_args(argv)
    c = Controller(args.db, args.root)
    try:
        if args.command == "initialize":
            c.initialize(json.loads(Path(args.spec).read_text()), args.workers)
        elif args.command == "claim":
            c.claim(args.id, args.owner, args.ttl)
        elif args.command == "submit":
            c.submit(args.id, args.owner)
        elif args.command == "review":
            c.review(args.id, args.reviewer, args.decision == "approve", args.reason)
        print(json.dumps({"tasks": c.status()}, sort_keys=True))
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc)}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

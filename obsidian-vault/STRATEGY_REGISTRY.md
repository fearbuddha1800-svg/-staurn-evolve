---
slug: strategy_registry
type: note
graph: gitnexus
---

"""Versioned local Pine strategy registry.

File polling is portable and content-addressed (not mtime-only). A failed edit
retains the last validated revision. Compilation/watch/backtest are explicit
trusted-owner operations, never enabled merely by a dashboard HTTP request.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import threading
import time
from tv_pine_import import parse_tv_export

BASE = Path(__file__).resolve().parent
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}')


def compile_pine(source: str) -> dict:
    """Syntax validation only; does not connect to MT5 or execute a strategy."""
    try:
        result = subprocess.run(
            ['node', '--max-old-space-size=256', str(BASE / 'pine_compile_bridge.js')],
            input=source, capture_output=True, encoding='utf-8', timeout=15,
            cwd=str(BASE), env={k: v for k, v in os.environ.items()
                                if k.upper() in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'TMPDIR')})
        if result.returncode or len(result.stdout) > 16384:
            return {'ok': False, 'error': 'PineTS compiler failed'}
        decoded = json.loads(result.stdout)
        if not isinstance(decoded, dict) or not isinstance(decoded.get('ok'), bool):
            raise ValueError('Invalid compiler response')
        return decoded
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {'ok': False, 'error': f'PineTS compiler unavailable: {type(exc).__name__}'}


class StrategyRegistry:
    def __init__(self, directory=None, *, compiler=compile_pine, cache=None,
                 discovery_roots=None, auto_backtest=False, backtester=None):
        self.directory = Path(directory or BASE / 'strategies').resolve()
        self.cache = Path(cache or self.directory.parent / '.cache' / 'strategy-registry').resolve()
        self.compiler = compiler
        self.roots = tuple(dict.fromkeys(Path(p).resolve() for p in (
            discovery_roots if discovery_roots is not None else
            (self.directory, self.directory.parent / 'luxalgo', self.directory.parent.parent / 'luxalgo'))))
        self.auto_backtest = auto_backtest
        self.backtester = backtester
        self._paths = {}
        self._lock = threading.RLock()
        self._scan_lock = threading.Lock()
        self._entries = {}
        self._active = {}
        self._seen = {}
        self._stop = threading.Event()
        self._thread = None
        self.watcher_error = None

    def _id(self, strategy_id):
        if not isinstance(strategy_id, str) or not _ID.fullmatch(strategy_id):
            raise ValueError('Invalid strategy id')
        return strategy_id

    def _path(self, strategy_id):
        target = self.directory / (self._id(strategy_id) + '.pine')
        if target.resolve().parent != self.directory or target.is_symlink():
            raise ValueError('Strategy must be a direct local file, not a symlink')
        return target

    def _write(self, target, source):
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.tmp-' + os.urandom(8).hex())
        try:
            temporary.write_text(source, encoding='utf-8', newline='\n')
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)

    def _discover(self):
        """Stable collision-free IDs; never traverse package trees or symlinks."""
        found = {}
        visited = set()
        excluded = {'node_modules', '.git', '.cache', 'dist', '__pycache__', '.venv'}
        for root in self.roots:
            if not root.is_dir() or root.is_symlink():
                continue
            for folder, dirs, files in os.walk(root, followlinks=False):
                dirs[:] = sorted(d for d in dirs if d not in excluded and
                                 not (Path(folder) / d).is_symlink())
                for name in sorted(files):
                    path = Path(folder) / name
                    if path.suffix.lower() != '.pine' or path.is_symlink():
                        continue
                    resolved = path.resolve()
                    if not resolved.is_relative_to(root) or resolved in visited:
                        continue
                    visited.add(resolved)
                    if root == self.directory and path.parent == self.directory and _ID.fullmatch(path.stem):
                        strategy_id = path.stem
                    else:
                        relative = str(root) + '/' + path.relative_to(root).as_posix()
                        slug = re.sub('[^A-Za-z0-9_-]', '-', path.stem)[:45].strip('-') or 'pine'
                        strategy_id = 'pine-' + slug + '-' + hashlib.sha256(relative.encode()).hexdigest()[:16]
                    if strategy_id in found:
                        raise ValueError('Strategy discovery ID collision')
                    found[strategy_id] = path
        return found

    def refresh(self, *, validate=True):
        """Discover edits/deletions. Metadata-only reads never launch Node."""
        with self._scan_lock:
            paths = self._discover()
            discovered = set(paths)
            self._paths = paths
            for strategy_id, path in sorted(paths.items()):
                try:
                    if path.stat().st_size > 65536:
                        raise ValueError('Pine source too large')
                    source = path.read_text(encoding='utf-8-sig')
                    fingerprint = hashlib.sha256(source.encode('utf-8')).hexdigest()
                    with self._lock:
                        if self._seen.get(strategy_id) == (fingerprint, validate):
                            continue
                    parsed = parse_tv_export(source)
                    digest = hashlib.sha256(parsed['source'].encode('utf-8')).hexdigest()
                    compiled = self.compiler(parsed['source']) if validate else {'ok': None}
                    if validate and not compiled.get('ok'):
                        raise ValueError(compiled.get('error', 'PineTS rejected source'))
                    entry = {k: v for k, v in parsed.items() if k != 'source'}
                    display_path = os.path.relpath(path, self.directory.parent).replace('\\', '/')
                    entry.update(id=strategy_id, path=display_path,
                                 revision=digest, status='ready' if validate else 'unvalidated',
                                 error=None, updated_at=time.time())
                    if validate:
                        self._write(self.cache / strategy_id / (digest + '.pine'), parsed['source'])
                    candidate_ok = True
                    if validate and self.auto_backtest:
                        result = self._backtest_source(strategy_id, parsed['source'],
                            symbol=(parsed['symbols'] or ['XAUUSD'])[0],
                            timeframe=parsed['timeframe'] or 'H1', count=1000)
                        candidate_ok = result.get('ok') is True and result.get('bars', 0) >= 500
                        entry['status'] = 'research-ready' if candidate_ok else 'backtest-failed'
                        entry['error'] = None if candidate_ok else result.get('error', 'Insufficient actual MT5 bars')
                    with self._lock:
                        if validate and candidate_ok:
                            self._active[strategy_id] = (digest, parsed['source'])
                        active = self._active.get(strategy_id)
                        entry['active_revision'] = active[0] if active else None
                        self._entries[strategy_id] = entry
                        self._seen[strategy_id] = (fingerprint, validate)
                except (OSError, UnicodeError, ValueError) as exc:
                    with self._lock:
                        # Reverting a broken edit to the exact last-good bytes must
                        # clear error state rather than hitting the unchanged fast path.
                        self._seen.pop(strategy_id, None)
                        previous = self._entries.get(strategy_id, {'id': strategy_id, 'path': 'strategies/' + path.name})
                        self._entries[strategy_id] = {**previous, 'status': 'error', 'error': str(exc)[:1000]}
            with self._lock:
                for deleted in set(self._entries) - discovered:
                    self._entries.pop(deleted, None)
                    self._active.pop(deleted, None)
                    self._seen.pop(deleted, None)
        return self.list()

    def list(self):
        with self._lock:
            return copy.deepcopy([self._entries[k] for k in sorted(self._entries)])

    def source(self, strategy_id):
        """Return immutable last-known-good source, not a racing filesystem read."""
        self._id(strategy_id)
        with self._lock:
            if strategy_id not in self._active:
                raise ValueError('No compiled revision; run trusted registry refresh first')
            return self._active[strategy_id][1]

    def start(self, interval=2.0):
        if interval < 0.05:
            raise ValueError('Polling interval must be at least 0.05 seconds')
        if self._thread and self._thread.is_alive():
            return self
        self.refresh()
        self._stop.clear()
        def watch():
            while not self._stop.wait(interval):
                try:
                    self.refresh()
                    self.watcher_error = None
                except Exception as exc:
                    self.watcher_error = str(exc)[:1000]
        self._thread = threading.Thread(target=watch, name='pine-strategy-watcher', daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=20)
            if self._thread.is_alive():
                raise RuntimeError('Strategy watcher did not stop')

    def import_export(self, strategy_id, text, *, overwrite=False):
        target = self._path(strategy_id)
        if target.exists() and not overwrite:
            raise FileExistsError(target.name)
        parsed = parse_tv_export(text)
        result = self.compiler(parsed['source'])
        if not result.get('ok'):
            raise ValueError(result.get('error', 'PineTS validation failed'))
        self._write(target, parsed['source'])
        self.refresh()
        return next(e for e in self.list() if e['id'] == strategy_id)

    def revisions(self, strategy_id):
        self._id(strategy_id)
        return sorted(p.stem for p in (self.cache / strategy_id).glob('*.pine')
                      if re.fullmatch('[a-f0-9]{64}', p.stem))

    def rollback(self, strategy_id, revision):
        target = self._path(strategy_id)
        if not isinstance(revision, str) or not re.fullmatch('[a-f0-9]{64}', revision):
            raise ValueError('Expected full SHA256 revision')
        source = (self.cache / strategy_id / (revision + '.pine')).read_text(encoding='utf-8')
        # Validate on the current engine before replacing the working copy.
        return self.import_export(strategy_id, source, overwrite=True)

    def git_tag(self, strategy_id):
        """Explicit owner action: tag only an already committed, clean .pine file.

        Never stages or commits unrelated workspace changes. Tag contains both
        strategy id and semver to avoid collisions between independent strategies.
        """
        self._id(strategy_id)
        target = self._discover().get(strategy_id)
        if target is None:
            raise ValueError('Strategy is not discovered')
        parsed = parse_tv_export(target.read_text(encoding='utf-8'))
        def git(*args):
            return subprocess.run(['git', '-C', str(target.parent), *args], check=True,
                                  capture_output=True, encoding='utf-8', timeout=15).stdout.strip()
        git('ls-files', '--error-unmatch', '--', target.name)
        if git('status', '--porcelain', '--', target.name):
            raise ValueError('Commit the strategy before tagging')
        tag = f'strategy/{strategy_id}/v{parsed["version"]}'
        git('tag', '--', tag)
        if git('rev-parse', '--verify', 'refs/tags/' + tag) != git('rev-parse', 'HEAD'):
            raise RuntimeError('Strategy tag verification failed')
        return tag

    def _backtest_source(self, strategy_id, source, *, symbol, timeframe, count):
        from pine_runner import backtest_strategy
        digest = hashlib.sha256(source.encode('utf-8')).hexdigest()
        snapshot = self.cache / strategy_id / (digest + '.pine')
        self._write(snapshot, source)
        try:
            result = (self.backtester or backtest_strategy)(str(snapshot), symbol=symbol, timeframe=timeframe, count=count)
        except Exception as exc:
            result = {'ok': False, 'error': f'{type(exc).__name__}: {str(exc)[:500]}'}
        published = {**result, 'strategy_id': strategy_id, 'revision': digest,
                     'symbol': symbol, 'timeframe': timeframe, 'requested_bars': count,
                     'observed_at': time.time(),
                     'provenance': 'MT5 closed candles / PineTS simulation; not live account equity'}
        self._write(self.cache / strategy_id / 'backtest.json', json.dumps(published, allow_nan=False))
        return published

    def backtest(self, strategy_id, *, symbol='XAUUSD', timeframe='H1', count=1000):
        """Trusted local research only; does not record or execute trade signals."""
        if isinstance(count, bool) or not isinstance(count, int) or not 500 <= count <= 1500:
            raise ValueError('Registry backtests require 500..1500 closed bars')
        return self._backtest_source(strategy_id, self.source(strategy_id),
                                    symbol=symbol, timeframe=timeframe, count=count)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['list', 'watch', 'import', 'rollback', 'tag', 'backtest', 'approve', 'deploy'])
    parser.add_argument('--id')
    parser.add_argument('--file')
    parser.add_argument('--revision')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--symbol', default='XAUUSD')
    parser.add_argument('--timeframe', default='H1')
    parser.add_argument('--count', type=int, default=1000)
    parser.add_argument('--target', choices=['strategy.py', 'strategy2_live.py'])
    parser.add_argument('--risk-unit-cash', type=float)
    parser.add_argument('--acknowledge-live-policy', action='store_true')
    args = parser.parse_args()
    registry = StrategyRegistry(auto_backtest=args.command == 'watch')
    if args.command == 'list':
        print(json.dumps(registry.refresh(), indent=2))
    elif args.command == 'import':
        print(json.dumps(registry.import_export(args.id, Path(args.file).read_text(encoding='utf-8-sig'), overwrite=args.overwrite)))
    elif args.command == 'rollback':
        print(json.dumps(registry.rollback(args.id, args.revision)))
    elif args.command == 'tag':
        print(registry.git_tag(args.id))
    elif args.command in ('approve', 'deploy'):
        from registry_release import approve, deploy
        registry.refresh(validate=False)
        if args.command == 'approve':
            registry.refresh()
            output = approve(registry, args.id, risk_unit_cash=args.risk_unit_cash,
                             acknowledge_live_policy=args.acknowledge_live_policy)
        else:
            output = deploy(registry, args.id, args.revision, args.target)
        print(json.dumps(output, indent=2))
    elif args.command == 'backtest':
        registry.refresh()
        print(json.dumps(registry.backtest(args.id, symbol=args.symbol, timeframe=args.timeframe, count=args.count)))
    else:
        registry.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            registry.stop()


if __name__ == '__main__':
    main()

## Links from
- [[cockpit]]
- [[cockpit_runtime]]
- [[test_strategy_registry]]

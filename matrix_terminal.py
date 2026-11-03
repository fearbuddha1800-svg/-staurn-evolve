"""Shared, bounded observation feed. Never attaches to a broker or executes Pine."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import threading
import time


def stamp():
    return datetime.now(timezone.utc).isoformat()


class ObservationFeed:
    """One worker per source at most; slow integrations cannot multiply jobs."""
    def __init__(self, backend):
        self.backend = backend
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=6, thread_name_prefix='matrix-observer')
        self.pending = {}
        self.records = {}
        self.next_poll = 0.0
        self.revision = 0

    def snapshot(self):
        b = self.backend
        sources = {'state': b.state, 'health': b.health_data, 'neural': b.neural_data,
                   'luxalgo': b.luxalgo_data, 'edge': b.edge_data,
                   'strategies': b.strategies_data, 'pine': b.pine_data,
                   'portfolio': b.portfolio_data, 'latency': b.latency_data,
                   'inbox': b.inbox_data,
                   'market-intel': b.market_intel_data,
                   'prop-sim': lambda: b.prop_sim_data(2000),
                   'events': lambda: b.bus.history(30, exclude='pl_tick'),
                   'candles': lambda: b.candles_data('XAUUSD', 'H1', 100)}
        now = time.monotonic()
        with self.lock:
            for key, (future, started) in list(self.pending.items()):
                if future.done():
                    try:
                        data = future.result()
                        self.records[key] = {'observed_at': stamp(), 'data': data,
                                             'available': not (isinstance(data, dict) and
                                                               (data.get('error') or data.get('available') is False))}
                    except Exception:
                        self.records[key] = {'observed_at': stamp(), 'available': False,
                                             'reason': 'Source observation failed; inspect local service logs.'}
                    del self.pending[key]
                    self.revision += 1
            if now >= self.next_poll:
                for key, fn in sources.items():
                    if key not in self.pending:
                        self.pending[key] = (self.pool.submit(fn), now)
                self.next_poll = now + 5
            panels = {}
            for key in sources:
                record = dict(self.records.get(key, {'available': False, 'reason': 'Awaiting source observation', 'observed_at': None}))
                record['pending'] = key in self.pending
                record['stale'] = bool(key in self.pending and now - self.pending[key][1] > 15)
                panels[key] = record
            panels['cloudroom'] = {'available': False, 'observed_at': None,
                                   'reason': 'No verified Cloudroom telemetry adapter configured. No compute was provisioned.'}
            panels['pine-live'] = {'available': False, 'observed_at': None,
                                  'reason': 'Pine execution requires a credential-free OS-isolated worker; browser execution remains disabled.'}
            return {'schema': 'hq.matrix.v1', 'revision': self.revision,
                    'generated_at': stamp(), 'refresh_seconds': 5,
                    'execution_available': False, 'panels': panels}


def get_feed(server, backend):
    # The handler creates this under a module lock, not one producer per browser.
    with _FEED_LOCK:
        if not hasattr(server, 'matrix_feed'):
            server.matrix_feed = ObservationFeed(backend)
        return server.matrix_feed


_FEED_LOCK = threading.Lock()
_STREAM_SLOTS = threading.BoundedSemaphore(8)


def stream(handler, feed):
    if not _STREAM_SLOTS.acquire(blocking=False):
        handler._send(503, {'error': 'Observation stream capacity reached. Retry shortly.'})
        return
    try:
        handler.send_response(200)
        handler.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        handler.send_header('Cache-Control', 'no-store')
        handler.send_header('X-Content-Type-Options', 'nosniff')
        handler.send_header('X-Accel-Buffering', 'no')
        handler.send_header('Connection', 'close')
        handler.end_headers()
        handler.close_connection = True
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if not handler._authenticated():
                handler.wfile.write(b'event: session-expired\ndata: {}\n\n')
                handler.wfile.flush()
                break
            payload = json.dumps(feed.snapshot(), default=str, allow_nan=False)
            handler.wfile.write(('retry: 2000\nevent: matrix-snapshot\ndata: ' + payload + '\n\n').encode('utf-8'))
            handler.wfile.flush()
            time.sleep(2)
    except (BrokenPipeError, ConnectionResetError, OSError):
        pass
    finally:
        _STREAM_SLOTS.release()

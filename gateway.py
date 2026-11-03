"""Unified authenticated, observational gateway. No broker startup or write proxy.

Run: python gateway.py [--config gateway.yaml]. Requires PyYAML.
Uses the existing .cockpit-token or COCKPIT_TOKEN (Bearer/X-Cockpit-Token/
same-origin cookie). SSE uses the same auth; never put tokens in query strings.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import os
import queue
import sqlite3
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from pathlib import Path

import yaml
from cockpit_runtime import ApiError, CockpitHandler, load_token

BASE = Path(__file__).resolve().parent
LOCAL_HANDLERS = frozenset({"state", "inbox_data", "journal_data", "neural_data",
                            "strategies_data", "health_data", "luxalgo_data",
                            "latency_data", "lineage_data", "pine_data"})


def load_config(path):
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("Gateway configuration must be a mapping")
    if config.get("host", "127.0.0.1") not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Gateway must bind loopback; use an authenticated TLS edge remotely")
    for key, default, low, high in (("port", 8490, 0, 65535),
                                   ("health_interval", 15, 1, 3600),
                                   ("upstream_timeout", 3, 0.1, 30)):
        value = config.get(key, default)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise ValueError(f"Invalid {key}")
        if key == "port" and not isinstance(value, int):
            raise ValueError("port must be an integer")
        config[key] = value
    services = config.get("services")
    if not isinstance(services, dict) or not services:
        raise ValueError("services must be a nonempty mapping")
    for name, service in services.items():
        if not isinstance(service, dict) or service.get("kind") not in {"local", "http"}:
            raise ValueError(f"Invalid service: {name}")
        if service["kind"] == "local":
            if service.get("health_handler") not in LOCAL_HANDLERS:
                raise ValueError(f"Unknown health handler: {name}")
        else:
            url = urllib.parse.urlsplit(service.get("url", ""))
            if (url.scheme != "http" or url.hostname not in {"localhost", "127.0.0.1", "::1"}
                    or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}):
                raise ValueError("HTTP upstreams must be loopback origins without credentials")
            if (url.port or 80) == config["port"]:
                raise ValueError("Upstream cannot point to this gateway")
            if not service.get("health_path", "/health").startswith("/"):
                raise ValueError("health_path must be absolute")
    routes = config.get("routes", [])
    if not isinstance(routes, list):
        raise ValueError("routes must be a list")
    seen = set()
    for route in routes:
        path = route.get("path", "")
        if not path.startswith("/api/") or path in seen or path in {
                "/api/services", "/api/gateway/health", "/api/gateway/events"}:
            raise ValueError("Invalid, duplicate or reserved route")
        seen.add(path)
        if route.get("service") not in services:
            raise ValueError("Unknown route service")
        service = services[route["service"]]
        if "handler" in route:
            if service["kind"] != "local" or route["handler"] not in LOCAL_HANDLERS:
                raise ValueError("Unknown local route handler")
        elif service["kind"] == "local" and route["service"] != "cockpit":
            raise ValueError("Local aliases without handlers must target cockpit")
        if not route.get("upstream_path", "/api").startswith("/"):
            raise ValueError("upstream_path must be absolute")
    return config


class EventBroadcaster:
    """Poll persisted shared event_bus rows, fan out to bounded subscriber queues.

    This sees events emitted by other processes, unlike event_bus subscriptions.
    New subscribers receive a ready frame; Last-Event-ID replays up to 1000 rows.
    Overflow disconnects the slow client rather than silently losing events.
    """
    def __init__(self, db_path):
        self.db_path = str(db_path)
        self.lock = threading.Lock()
        self.clients = set()
        self.stop = threading.Event()
        self.thread = None
        self.cursor = self.latest()

    def rows(self, after, limit=1000):
        if not Path(self.db_path).exists():
            return []
        with closing(sqlite3.connect(Path(self.db_path).resolve().as_uri() + "?mode=ro", uri=True, timeout=1)) as conn:
            return conn.execute("SELECT rowid, type, payload, ts, event_id, source, trace_id FROM events WHERE rowid > ? ORDER BY rowid LIMIT ?", (after, limit)).fetchall()

    def latest(self):
        try:
            if not Path(self.db_path).exists():
                return 0
            with closing(sqlite3.connect(Path(self.db_path).resolve().as_uri() + "?mode=ro", uri=True, timeout=1)) as conn:
                return conn.execute("SELECT COALESCE(MAX(rowid),0) FROM events").fetchone()[0]
        except sqlite3.Error:
            return 0

    def subscribe(self, after=None):
        client = queue.Queue(maxsize=1024)
        with self.lock:
            if after is not None:
                rows = self.rows(after, 1001)
                if len(rows) > 1000:
                    raise ValueError("Replay window exceeded; reload snapshot before subscribing")
                for row in rows:
                    client.put_nowait(row)
                # Replay can be ahead of polling; the handler deduplicates by ID.
            self.clients.add(client)
        return client

    def unsubscribe(self, client):
        with self.lock:
            self.clients.discard(client)

    def run(self):
        while not self.stop.wait(0.25):
            try:
                with self.lock:
                    for row in self.rows(self.cursor):
                        self.cursor = row[0]
                        for client in tuple(self.clients):
                            try:
                                client.put_nowait(row)
                            except queue.Full:
                                self.clients.discard(client)
                                while not client.empty():
                                    client.get_nowait()
                                client.put_nowait(None)
            except sqlite3.Error:
                continue

    def start(self):
        self.thread = threading.Thread(target=self.run, daemon=True, name="gateway-events")
        self.thread.start()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class GatewayServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, config, backend, token):
        self.config = config
        self.backend = backend
        self.cockpit_token = token
        self.registry_lock = threading.Lock()
        self.registry = {}
        self.stop = threading.Event()
        bus = getattr(backend, 'bus', None)
        db_path = getattr(bus, 'db', None) or os.environ.get('SIGNAL_RELAY_EVENT_DB') or Path(backend.BASE) / 'signals.db'
        self.event_stream = EventBroadcaster(db_path)
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        super().__init__((config.get("host", "127.0.0.1"), config["port"]), GatewayHandler)

    def probe(self, name, service):
        started = time.monotonic()
        result = {"name": name, "kind": service["kind"], "checked_at": time.time(),
                  "observational": True}
        try:
            if service["kind"] == "http":
                request = urllib.request.Request(service["url"].rstrip("/") + service.get("health_path", "/health"))
                with self.opener.open(request, timeout=self.config["upstream_timeout"]) as response:
                    result.update(status="up" if response.status == 200 else "degraded", http_status=response.status)
            else:
                # Adapter availability is not proof a trading engine/model is running.
                if not callable(getattr(self.backend, service["health_handler"], None)):
                    raise RuntimeError("adapter missing")
                result.update(status="available", scope="read_only_adapter", runtime_health="inspect_service_endpoint")
        except Exception:
            result.update(status="down", error="health_probe_failed")
        result["latency_ms"] = round((time.monotonic() - started) * 1000, 2)
        result["routes"] = [r["path"] for r in self.config.get("routes", []) if r["service"] == name]
        with self.registry_lock:
            self.registry[name] = result

    def refresh(self):
        with ThreadPoolExecutor(max_workers=min(8, len(self.config["services"]))) as pool:
            list(pool.map(lambda item: self.probe(*item), self.config["services"].items()))

    def monitor(self):
        while not self.stop.is_set():
            self.refresh()
            self.stop.wait(self.config["health_interval"])

    def start_workers(self):
        self.event_stream.start()
        self.monitor_thread = threading.Thread(target=self.monitor, daemon=True, name="gateway-health")
        self.monitor_thread.start()

    def server_close(self):
        self.stop.set()
        self.event_stream.stop.set()
        super().server_close()
        for thread in (self.event_stream.thread, getattr(self, "monitor_thread", None)):
            if thread:
                thread.join(timeout=self.config["upstream_timeout"] + 1)


class GatewayHandler(CockpitHandler):
    @property
    def backend(self):
        return self.server.backend

    def log_message(self, fmt, *args):
        # Never log URL queries, cookies, authorization or upstream bodies.
        pass

    def _json(self, body, status=200):
        return self._send(status, body)

    def _dispatch(self, method):
        if method != 'GET':
            return super()._dispatch(method)
        self._local_host()
        parsed = urllib.parse.urlsplit(self.path)
        if parsed.scheme or parsed.netloc or parsed.fragment:
            raise ApiError(400, 'Invalid request target')
        if parsed.path.startswith('/api/') and not self._authenticated():
            raise ApiError(401, 'Unauthorized')
        path = parsed.path
        if path == "/api/services":
            with self.server.registry_lock:
                services = list(self.server.registry.values())
            return self._json({"services": services, "read_only": True})
        if path == "/api/gateway/health":
            with self.server.registry_lock:
                services = dict(self.server.registry)
            degraded = len(services) < len(self.server.config["services"]) or any(s["status"] == "down" for s in services.values())
            return self._json({"status": "degraded" if degraded else "up", "services": services, "read_only": True})
        if path == "/api/gateway/events":
            return self.events()
        for route in sorted(self.server.config.get("routes", []), key=lambda r: len(r["path"]), reverse=True):
            if path == route["path"] or (route.get("prefix") and path.startswith(route["path"] + "/")):
                if "handler" in route:
                    try:
                        return self._json(getattr(self.backend, route["handler"])())
                    except Exception:
                        return self._json({"error": "service_unavailable"}, 503)
                target = route.get("upstream_path", "/api") + path[len(route["path"]):]
                if parsed.query:
                    target += "?" + parsed.query
                service = self.server.config["services"][route["service"]]
                if service["kind"] == "http":
                    return self.proxy(service, target)
                original = self.path
                try:
                    self.path = target
                    return super()._dispatch('GET')
                finally:
                    self.path = original
        return super()._dispatch('GET')

    def proxy(self, service, target):
        headers = {"Accept": "application/json"}
        token = os.environ.get(service.get("token_env", ""), "")
        if token:
            headers["Authorization"] = "Bearer " + token
        request = urllib.request.Request(service["url"].rstrip("/") + target, headers=headers, method="GET")
        try:
            response = self.server.opener.open(request, timeout=self.server.config["upstream_timeout"])
        except urllib.error.HTTPError as error:
            # No redirect, challenge, cookies or untrusted upstream errors forwarded.
            return self._json({"error": "upstream_http_error", "upstream_status": error.code}, 502)
        except (OSError, urllib.error.URLError):
            return self._json({"error": "upstream_unavailable"}, 503)
        with response:
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                return self._json({"error": "upstream_response_too_large"}, 502)
            try:
                payload = json.loads(raw)
            except (ValueError, UnicodeError):
                return self._json({"error": "upstream_invalid_json"}, 502)
            return self._json(payload)

    def events(self):
        after = self.headers.get("Last-Event-ID")
        try:
            after = int(after) if after is not None else None
            if after is not None and after < 0:
                raise ValueError("negative cursor")
            client = self.server.event_stream.subscribe(after)
        except (ValueError, sqlite3.Error):
            return self._json({"error": "invalid_or_expired_event_cursor"}, 409)
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        last = after or 0
        try:
            self.wfile.write(b"event: ready\ndata: {\"stream\":\"signals.db\"}\n\n")
            self.wfile.flush()
            while not self.server.stop.is_set():
                try:
                    row = client.get(timeout=1)
                except queue.Empty:
                    self.wfile.write(b": heartbeat\n\n")
                    self.wfile.flush()
                    continue
                if row is None:
                    break
                event_id, event_type, data, timestamp, uuid, source, trace_id = row
                if event_id <= last:
                    continue
                last = event_id
                payload = json.dumps({"type": event_type, "payload": json.loads(data), "ts": timestamp,
                                      "event_id": uuid, "source": source, "trace_id": trace_id})
                self.wfile.write(f"id: {event_id}\nevent: message\ndata: {payload}\n\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError, ValueError):
            pass
        finally:
            self.server.event_stream.unsubscribe(client)
            self.close_connection = True


def create_server(config_path=BASE / "gateway.yaml", *, backend=None, token=None):
    config = load_config(config_path)
    if backend is None:
        import cockpit as backend
    return GatewayServer(config, backend, token or load_token(backend.BASE))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default=str(BASE / "gateway.yaml"))
    args = parser.parse_args()
    server = create_server(args.config)
    server.start_workers()
    print(f"Read-only gateway: http://{server.server_address[0]}:{server.server_address[1]}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

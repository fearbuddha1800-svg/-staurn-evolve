"""Read-only LuxAlgo MCP intelligence; no invented decay/regime/whale inference.
Contracts: luxalgo-mcp-server/src/entries/node-http.ts and
src/tools/{edge,trackers}/tools.ts. Streamable HTTP on localhost:3333/mcp.
"""
from __future__ import annotations
import asyncio
from contextlib import AsyncExitStack, contextmanager
from datetime import datetime, timezone, timedelta
import json
import os
from pathlib import Path
import time
from event_bus import bus, make_event

LUXALGO_MCP_URL = os.getenv("LUXALGO_MCP_URL", "http://localhost:3333/mcp")
POLL_INTERVAL = max(30, int(os.getenv("LUXALGO_ORCHESTRATOR_POLL", "60")))
CALL_TIMEOUT = 8
MAX_RESPONSE_BYTES = 256_000


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def unavailable(reason, provenance):
    return {"available": False, "reason": reason, "provenance": provenance}


@contextmanager
def single_instance(path):
    """OS-held lock, automatically released on death; never trust a stale PID."""
    handle = open(path, "a+b")
    locked = False
    try:
        handle.seek(0)
        if os.name == "nt":
            import msvcrt
            if os.path.getsize(path) == 0:
                handle.write(b"0")
                handle.flush()
                handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        locked = True
        yield
    finally:
        if locked:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_UN)
        handle.close()


class MCPAdapter:
    """Persistent SDK session; bounded read timeouts, capped reconnect backoff.

    AnyIO context entry/exit stays on the same task, not inside wait_for.
    """
    def __init__(self, url=LUXALGO_MCP_URL, clock=time.monotonic):
        self.url, self.clock = url, clock
        self.session = self.stack = None
        self.tools = set()
        self.retry_at, self.backoff = 0.0, 5
        self.reason = "not connected"

    async def close(self):
        stack, self.stack = self.stack, None
        self.session = None
        self.tools.clear()
        if stack:
            await stack.aclose()

    async def failed(self, reason):
        self.reason = reason
        try:
            await self.close()
        except Exception:
            pass
        self.retry_at = self.clock() + self.backoff
        self.backoff = min(300, self.backoff * 2)

    async def connect(self):
        if self.session:
            return True
        if self.clock() < self.retry_at:
            return False
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client
            self.stack = AsyncExitStack()
            read, write, _ = await self.stack.enter_async_context(
                streamablehttp_client(self.url, timeout=CALL_TIMEOUT, sse_read_timeout=CALL_TIMEOUT))
            self.session = await self.stack.enter_async_context(
                ClientSession(read, write, read_timeout_seconds=timedelta(seconds=CALL_TIMEOUT)))
            await self.session.initialize()
            listed = await self.session.list_tools()
            self.tools = {tool.name for tool in listed.tools[:128]}
            self.backoff, self.reason = 5, "connected"
            return True
        except Exception as exc:
            await self.failed(f"MCP unavailable ({type(exc).__name__})")
            return False

    async def call(self, name, arguments):
        if not await self.connect():
            return unavailable(self.reason, self.url)
        if name not in self.tools:
            return unavailable(f"tool not exposed: {name}", self.url)
        try:
            result = await asyncio.wait_for(self.session.call_tool(name, arguments), CALL_TIMEOUT)
            if result.isError:
                return unavailable(f"{name} returned a tool error", self.url)
            data = getattr(result, "structuredContent", None)
            if data is None:
                text = next((c.text for c in result.content if c.type == "text"), "")
                if len(text.encode("utf-8")) > MAX_RESPONSE_BYTES:
                    return unavailable("response exceeds byte budget", self.url)
                data = json.loads(text)
            if not isinstance(data, dict) or len(json.dumps(data)) > MAX_RESPONSE_BYTES:
                return unavailable("invalid/oversize response", self.url)
            return {"available": True, "data": data, "provenance": f"{self.url}#{name}"}
        except Exception as exc:
            await self.failed(f"{name} unavailable ({type(exc).__name__})")
            return unavailable(self.reason, self.url)


class LuxAlgoOrchestrator:
    def __init__(self, adapter=None, event_bus=None, symbol=None, preset=None, dataset=None):
        self.adapter = adapter or MCPAdapter()
        self.bus = event_bus or bus
        # Explicit selection only: never substitute SPY/BTC for an MT5 symbol.
        self.symbol = symbol or os.getenv("LUXALGO_EDGE_SYMBOL")
        self.preset = preset or os.getenv("LUXALGO_EDGE_PRESET")
        self.dataset = dataset or os.getenv("LUXALGO_TRACKER_DATASET")
        self.running = False
        self.catalog, self.status = {}, {}
        self.catalog_at = -float("inf")
        self.catalog_retry_at, self.catalog_backoff = 0.0, 30

    async def discover(self):
        now = time.monotonic()
        if now - self.catalog_at < 3600 or now < self.catalog_retry_at:
            return
        found = {}
        for name in ("trackers_datasets", "edge_symbols", "edge_presets"):
            result = await self.adapter.call(name, {})
            if result.get("available") is True:
                found[name] = result["data"]
        self.catalog = found
        if len(found) == 3:
            self.catalog_at, self.catalog_backoff = now, 30
        else:
            self.catalog_retry_at = now + self.catalog_backoff
            self.catalog_backoff = min(300, self.catalog_backoff * 2)

    async def run_poll_cycle(self):
        await self.discover()
        observed = utcnow()
        trackers = unavailable("explicit dataset missing/not in discovery", "trackers_datasets")
        datasets = self.catalog.get("trackers_datasets", {}).get("datasets", [])
        if self.dataset and any(d.get("id") == self.dataset for d in datasets if isinstance(d, dict)):
            trackers = await self.adapter.call("trackers_latest", {"dataset": self.dataset, "limit": 5})
        tracker_status = {k: v for k, v in trackers.items() if k != "data"}
        tracker_status["dataset"] = self.dataset
        if trackers.get("available"):
            tracker_status["last_ingested_at"] = trackers["data"].get("lastIngestedAt")
            tracker_status["returned"] = len(trackers["data"].get("rows", [])[:5])
        regime = unavailable("public-record counts are not a validated regime model", "trackers_latest")
        whale = unavailable("no market-wide options-flow tool; broker trades are owner activity",
                            "luxalgo-mcp-server/src/tools")
        edge = unavailable("explicit symbol/preset missing/not in discovery", "edge_symbols/edge_presets")
        symbols = self.catalog.get("edge_symbols", {}).get("symbols", [])
        presets = self.catalog.get("edge_presets", {}).get("presets", [])
        if (self.symbol and self.preset
                and any(s.get("symbol") == self.symbol for s in symbols if isinstance(s, dict))
                and any(p.get("id") == self.preset for p in presets if isinstance(p, dict))):
            edge = await self.adapter.call("edge_report", {"symbol": self.symbol, "preset": self.preset})
        edge_payload = {k: v for k, v in edge.items() if k != "data"}
        edge_payload.update({"observed_at": observed,
                             "edge_data": {"symbol": self.symbol, "preset": self.preset, "alpha_decay": None},
                             "interpretation": "historical statistics only; no validated decay source"})
        if edge.get("available"):
            edge_payload["report"] = edge["data"]
        for event_type, payload in (("luxalgo_regime_shift", regime),
                                    ("luxalgo_whale_options", whale), ("luxalgo_edge_stats", edge_payload)):
            self.bus.publish(make_event(event_type, "luxalgo_orchestrator", {"observed_at": observed, **payload}))
        self.status = {"observed_at": observed, "transport": "streamable-http",
                       "provenance": getattr(self.adapter, "url", "injected adapter"),
                       "trackers": tracker_status, "regime": regime, "whale_options": whale,
                       "edge": {k: v for k, v in edge_payload.items() if k != "report"},
                       "catalog_available": sorted(self.catalog), "available": bool(self.catalog),
                       "trading_policy_changed": False}
        self.bus.publish(make_event("engine_status", "luxalgo_orchestrator", self.status))
        return self.status

    async def run(self):
        self.running = True
        try:
            while self.running:
                try:
                    await self.run_poll_cycle()
                except Exception as exc:
                    self.status = {"available": False, "observed_at": utcnow(),
                                   "reason": f"poll unavailable ({type(exc).__name__})",
                                   "provenance": LUXALGO_MCP_URL}
                    self.bus.publish(make_event("engine_status", "luxalgo_orchestrator", self.status))
                await asyncio.sleep(POLL_INTERVAL)
        finally:
            await self.adapter.close()

    def stop(self):
        self.running = False


def main():
    try:
        with single_instance(Path(__file__).with_suffix(".lock")):
            asyncio.run(LuxAlgoOrchestrator().run())
    except BlockingIOError:
        print("LuxAlgo orchestrator already running")
    except OSError as exc:
        # Windows byte-range lock conflict is EACCES, not BlockingIOError.
        if exc.errno == 13:
            print("LuxAlgo orchestrator lock unavailable")
        else:
            raise
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()

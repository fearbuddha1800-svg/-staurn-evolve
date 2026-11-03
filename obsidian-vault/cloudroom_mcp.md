---
slug: cloudroom_mcp
type: note
graph: gitnexus
---

"""Project-owned read-only MCP adapter, not an upstream Cloudroom compute server."""
from mcp.server.fastmcp import FastMCP
from cloudroom_offload import ROOT, TARGETS, desired_workers, probe, report

mcp = FastMCP("Cloudroom offline research readiness")


@mcp.tool()
def status() -> dict:
    """Probe local WSL Cloudroom. Service readiness is NOT hosted compute readiness."""
    return probe()


@mcp.tool()
def offload_targets() -> dict:
    """Describe offline research targets and local-only fallback contracts."""
    return TARGETS


@mcp.tool()
def costs() -> dict:
    """Read measured offline queue runtime and optional local estimates; no cloud billing."""
    result = report(ROOT / ".cloudroom-state")
    jobs = result.pop("jobs")
    return {**result, "job_count": len(jobs), "recent_jobs": jobs[-50:]}


@mcp.tool()
def scaling_plan(queue_depth: int, max_workers: int = 2, jobs_per_worker: int = 2) -> dict:
    """Read-only bounded LOCAL concurrency plan; never provisions remote instances."""
    if isinstance(queue_depth, bool) or isinstance(max_workers, bool) or isinstance(jobs_per_worker, bool):
        raise ValueError("Expected integers, not booleans")
    return {"desired_local_workers": desired_workers(queue_depth, max_workers, jobs_per_worker), "remote_provisioning_enabled": False}


if __name__ == "__main__":
    mcp.run(transport="stdio")


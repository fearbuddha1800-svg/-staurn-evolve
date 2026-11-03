---
slug: model_router
type: note
graph: gitnexus
---

"""model_router.py — bounded AI call routing with deadline, concurrency, and budget caps.

When a provider is unavailable or the budget is exhausted, the router ABSTAINS
(returning an explicit 'abstained' result) rather than raising or returning a
fabricated answer. The router never blocks the caller indefinitely.

Bounds:
- Per-call deadline: each call must complete within deadline_s seconds
- Maximum concurrency: at most max_concurrency calls run simultaneously
- Budget cap: total spend across all calls must not exceed budget_total

Abstention: when a bound is exceeded or no provider is available, the router
returns a RouterResult with a specific status and reason. It never raises or
returns a fabricated answer.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol


class RouterStatus(Enum):
    SUCCESS = "success"
    ABSTAINED = "abstained"
    DEADLINE_EXCEEDED = "deadline_exceeded"
    BUDGET_EXHAUSTED = "budget_exhausted"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    CONCURRENCY_LIMIT = "concurrency_limit"


@dataclass
class RouterResult:
    """Result of a routed AI call."""
    status: RouterStatus
    provider: Optional[str] = None
    data: Any = None
    reason: Optional[str] = None
    elapsed_ms: float = 0.0
    cost: float = 0.0

    @property
    def ok(self) -> bool:
        return self.status == RouterStatus.SUCCESS

    @property
    def abstained(self) -> bool:
        return self.status in (
            RouterStatus.ABSTAINED,
            RouterStatus.DEADLINE_EXCEEDED,
            RouterStatus.BUDGET_EXHAUSTED,
            RouterStatus.PROVIDER_UNAVAILABLE,
            RouterStatus.CONCURRENCY_LIMIT,
        )


@dataclass
class RouterConfig:
    """Configuration for the model router.

    max_concurrency: Maximum number of simultaneous AI calls.
    deadline_s: Per-call deadline in seconds.
    budget_total: Maximum total spend across all calls.
    clock: callable returning current time (for testing). Defaults to time.monotonic.
    concurrency_timeout_s: Maximum time to wait for a concurrency slot.
        Defaults to None (use remaining deadline). Set explicitly for
        deterministic concurrency testing.
    """
    max_concurrency: int = 3
    deadline_s: float = 10.0
    budget_total: float = 1.0
    clock: Callable[[], float] = time.monotonic
    concurrency_timeout_s: Optional[float] = None


class Provider(Protocol):
    """Protocol for AI providers."""
    name: str

    def is_available(self) -> bool: ...
    def call(self, prompt: str, **kwargs) -> Any: ...
    def cost(self) -> float: ...


# Module-level thread pool for provider calls with timeout
_executor = ThreadPoolExecutor(max_workers=100, thread_name_prefix="model-router")


class ModelRouter:
    """Bounded AI call router.

    Enforces per-call deadline, maximum concurrency, and spend budget.
    Abstains explicitly when bounds are exceeded or providers unavailable.
    Never blocks the caller indefinitely.

    Concurrency behavior: when max_concurrency calls are active, additional
    calls WAIT up to the remaining deadline for a slot. If no slot opens
    within that time, the call ABSTAINS with CONCURRENCY_LIMIT.
    """

    def __init__(self, config: RouterConfig, providers: List[Provider]):
        self.config = config
        self.providers = providers
        self._semaphore = threading.Semaphore(config.max_concurrency)
        self._spend = 0.0
        self._spend_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Budget
    # ------------------------------------------------------------------
    def _check_budget(self, estimated_cost: float) -> bool:
        """Check if there's enough budget for a call."""
        with self._spend_lock:
            return self._spend + estimated_cost <= self.config.budget_total

    def _record_spend(self, cost: float) -> None:
        """Record spend after a call."""
        with self._spend_lock:
            self._spend += cost

    @property
    def spend(self) -> float:
        """Current total spend."""
        with self._spend_lock:
            return self._spend

    @property
    def budget_remaining(self) -> float:
        """Remaining budget."""
        with self._spend_lock:
            return max(0.0, self.config.budget_total - self._spend)

    # ------------------------------------------------------------------
    # Concurrency
    # ------------------------------------------------------------------
    def _try_acquire_concurrency(self, timeout: float) -> bool:
        """Try to acquire a concurrency slot within timeout."""
        return self._semaphore.acquire(timeout=timeout)

    def _release_concurrency(self) -> None:
        """Release a concurrency slot."""
        self._semaphore.release()

    # ------------------------------------------------------------------
    # Provider call with timeout
    # ------------------------------------------------------------------
    def _call_with_timeout(self, provider: Provider, prompt: str,
                           timeout: float, **kwargs) -> Any:
        """Call a provider with a timeout using the shared thread pool."""
        future = _executor.submit(provider.call, prompt, **kwargs)
        try:
            return future.result(timeout=timeout)
        except FutureTimeoutError:
            raise TimeoutError(
                f"Provider {provider.name} exceeded {timeout:.2f}s timeout"
            )

    # ------------------------------------------------------------------
    # Main routing
    # ------------------------------------------------------------------
    def route(self, prompt: str, **kwargs) -> RouterResult:
        """Route an AI call with deadline, concurrency, and budget enforcement.

        Tries each available provider in order. Abstains if:
        - No provider is available
        - Budget is exhausted
        - Deadline is exceeded
        - Concurrency limit is reached (with timeout)

        Never blocks indefinitely: the concurrency acquire uses a timeout
        derived from the remaining deadline.
        """
        start = self.config.clock()
        deadline = start + self.config.deadline_s

        # Check budget first (cheapest, non-blocking)
        if not self._check_budget(0.01):  # minimal estimate
            return RouterResult(
                status=RouterStatus.BUDGET_EXHAUSTED,
                reason=f"Budget exhausted: {self._spend:.4f}/{self.config.budget_total:.4f}",
                elapsed_ms=(self.config.clock() - start) * 1000,
            )

        # Try to acquire concurrency slot
        remaining = deadline - self.config.clock()
        if remaining <= 0:
            return RouterResult(
                status=RouterStatus.DEADLINE_EXCEEDED,
                reason="Deadline already exceeded before concurrency acquire",
                elapsed_ms=(self.config.clock() - start) * 1000,
            )

        # Use explicit concurrency timeout if set, otherwise use remaining deadline
        acquire_timeout = (
            self.config.concurrency_timeout_s
            if self.config.concurrency_timeout_s is not None
            else remaining
        )
        acquire_timeout = min(acquire_timeout, remaining)

        if not self._try_acquire_concurrency(timeout=acquire_timeout):
            return RouterResult(
                status=RouterStatus.CONCURRENCY_LIMIT,
                reason=f"Could not acquire concurrency slot within {acquire_timeout:.2f}s "
                       f"(max_concurrency={self.config.max_concurrency})",
                elapsed_ms=(self.config.clock() - start) * 1000,
            )

        try:
            timed_out = False
            # Try each provider
            for provider in self.providers:
                if not provider.is_available():
                    continue

                # Check remaining time
                now = self.config.clock()
                if now >= deadline:
                    return RouterResult(
                        status=RouterStatus.DEADLINE_EXCEEDED,
                        reason="Deadline exceeded before provider call",
                        elapsed_ms=(now - start) * 1000,
                    )

                # Check budget
                if not self._check_budget(provider.cost()):
                    return RouterResult(
                        status=RouterStatus.BUDGET_EXHAUSTED,
                        reason=f"Budget exhausted: {self._spend:.4f}/{self.config.budget_total:.4f}",
                        elapsed_ms=(self.config.clock() - start) * 1000,
                    )

                # Call provider with remaining timeout
                call_timeout = deadline - self.config.clock()
                if call_timeout <= 0:
                    return RouterResult(
                        status=RouterStatus.DEADLINE_EXCEEDED,
                        reason="Deadline exceeded before provider call",
                        elapsed_ms=(self.config.clock() - start) * 1000,
                    )

                try:
                    result = self._call_with_timeout(
                        provider, prompt, call_timeout, **kwargs
                    )
                    cost = provider.cost()
                    self._record_spend(cost)
                    return RouterResult(
                        status=RouterStatus.SUCCESS,
                        provider=provider.name,
                        data=result,
                        elapsed_ms=(self.config.clock() - start) * 1000,
                        cost=cost,
                    )
                except TimeoutError:
                    timed_out = True
                    continue  # Try next provider
                except Exception:
                    continue  # Provider failed, try next

            # No provider succeeded — distinguish timeout from other failures
            if timed_out:
                return RouterResult(
                    status=RouterStatus.DEADLINE_EXCEEDED,
                    reason="All available providers exceeded the deadline",
                    elapsed_ms=(self.config.clock() - start) * 1000,
                )
            return RouterResult(
                status=RouterStatus.PROVIDER_UNAVAILABLE,
                reason="No available provider succeeded",
                elapsed_ms=(self.config.clock() - start) * 1000,
            )
        finally:
            self._release_concurrency()

## Links from
- [[ai_filter]]
- [[test_ai_router_integration]]
- [[test_model_router]]

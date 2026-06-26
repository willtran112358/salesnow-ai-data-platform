"""
Retry & error-handling utilities for crawler batch jobs and CRM sync.

Per the 2026-06-26 discussion, the crawler runs as scheduled batch / back jobs
and downstream systems (Salesforce AppExchange, HubSpot, LLM agents) consume the
stream — so transient failures need bounded retry with exponential backoff plus
a dead-letter path for records that exhaust retries.
"""

from __future__ import annotations

import functools
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, TypeVar

T = TypeVar("T")


@dataclass
class RetryPolicy:
    max_attempts: int = 5
    base_delay_s: float = 1.0
    max_delay_s: float = 60.0
    jitter: bool = True
    retry_on: tuple[type[Exception], ...] = (Exception,)

    def delay_for(self, attempt: int) -> float:
        """Exponential backoff: base * 2^(attempt-1), capped, with optional jitter."""
        raw = self.base_delay_s * (2 ** (attempt - 1))
        capped = min(raw, self.max_delay_s)
        if self.jitter:
            capped *= 0.5 + random.random() / 2  # 50%-100% of the delay
        return capped


@dataclass
class DeadLetter:
    """Collects payloads that exhausted all retry attempts for later replay."""

    items: list[dict[str, Any]] = field(default_factory=list)

    def add(self, payload: dict[str, Any], error: str, attempts: int) -> None:
        self.items.append(
            {"payload": payload, "error": error, "attempts": attempts}
        )

    def __len__(self) -> int:
        return len(self.items)


def with_retry(
    policy: RetryPolicy | None = None,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that retries a callable using the given policy."""
    policy = policy or RetryPolicy()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_error: Exception | None = None
            for attempt in range(1, policy.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except policy.retry_on as exc:  # noqa: PERF203
                    last_error = exc
                    if attempt == policy.max_attempts:
                        break
                    sleep(policy.delay_for(attempt))
            raise RuntimeError(
                f"{func.__name__} failed after {policy.max_attempts} attempts"
            ) from last_error

        return wrapper

    return decorator


def process_batch(
    records: list[dict[str, Any]],
    handler: Callable[[dict[str, Any]], None],
    policy: RetryPolicy | None = None,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> DeadLetter:
    """
    Process a batch with per-record retry; failures land in a dead-letter queue
    instead of failing the whole job (keeps the back job resilient).
    """
    policy = policy or RetryPolicy()
    dlq = DeadLetter()
    retrying_handler = with_retry(policy, sleep=sleep)(handler)

    for record in records:
        try:
            retrying_handler(record)
        except RuntimeError as exc:
            dlq.add(record, str(exc.__cause__ or exc), policy.max_attempts)

    return dlq

"""Unit tests for retry and dead-letter handling."""

import pytest

from src.ingestion.retry import RetryPolicy, process_batch, with_retry


def test_retry_succeeds_after_failures() -> None:
    calls = {"n": 0}

    @with_retry(RetryPolicy(max_attempts=3, base_delay_s=0), sleep=lambda _: None)
    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("transient")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 3


def test_retry_exhausts_and_raises() -> None:
    @with_retry(RetryPolicy(max_attempts=2, base_delay_s=0), sleep=lambda _: None)
    def always_fail() -> None:
        raise ValueError("boom")

    with pytest.raises(RuntimeError):
        always_fail()


def test_dead_letter_collects_failures() -> None:
    def handler(record: dict) -> None:
        if record["id"] == 2:
            raise ValueError("bad record")

    records = [{"id": 1}, {"id": 2}, {"id": 3}]
    dlq = process_batch(
        records,
        handler,
        RetryPolicy(max_attempts=2, base_delay_s=0),
        sleep=lambda _: None,
    )
    assert len(dlq) == 1
    assert dlq.items[0]["payload"]["id"] == 2


def test_backoff_is_capped() -> None:
    policy = RetryPolicy(base_delay_s=1, max_delay_s=10, jitter=False)
    assert policy.delay_for(1) == 1
    assert policy.delay_for(2) == 2
    assert policy.delay_for(10) == 10  # capped

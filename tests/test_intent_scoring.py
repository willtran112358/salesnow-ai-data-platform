"""Unit tests for intent scoring."""

from src.ai.intent_scoring import ActivityFeatures, compute_intent_score


def test_high_hiring_intent() -> None:
    features = ActivityFeatures(
        job_postings_30d=15,
        job_postings_prev_30d=5,
        employee_growth_rate=0.2,
        funding_events_90d=1,
    )
    score = compute_intent_score("test-company-id", features)
    assert score.hiring_intent > 0.5
    assert 0.0 <= score.composite_score <= 1.0


def test_zero_activity_low_score() -> None:
    features = ActivityFeatures()
    score = compute_intent_score("test-company-id", features)
    assert score.composite_score == 0.0

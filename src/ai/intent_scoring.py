"""
Intent scoring model for SalesNow activity signals.

Combines hiring velocity, employee growth, and funding events into a composite score.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class ActivityFeatures:
    job_postings_30d: int = 0
    job_postings_prev_30d: int = 0
    employee_growth_rate: float = 0.0
    funding_events_90d: int = 0
    news_mentions_30d: int = 0


@dataclass
class IntentScore:
    company_id: str
    score_date: date
    hiring_intent: float
    growth_intent: float
    funding_intent: float
    composite_score: float
    model_version: str = "v1.0.0"


WEIGHTS = {
    "hiring": 0.35,
    "growth": 0.30,
    "funding": 0.25,
    "news": 0.10,
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def score_hiring_intent(features: ActivityFeatures) -> float:
    if features.job_postings_prev_30d == 0:
        velocity = 1.0 if features.job_postings_30d > 0 else 0.0
    else:
        velocity = features.job_postings_30d / features.job_postings_prev_30d
    return _clamp(velocity / 3.0)


def score_growth_intent(features: ActivityFeatures) -> float:
    return _clamp(features.employee_growth_rate / 0.5)


def score_funding_intent(features: ActivityFeatures) -> float:
    return _clamp(features.funding_events_90d / 2.0)


def compute_intent_score(company_id: str, features: ActivityFeatures) -> IntentScore:
    hiring = score_hiring_intent(features)
    growth = score_growth_intent(features)
    funding = score_funding_intent(features)
    news = _clamp(features.news_mentions_30d / 10.0)

    composite = (
        WEIGHTS["hiring"] * hiring
        + WEIGHTS["growth"] * growth
        + WEIGHTS["funding"] * funding
        + WEIGHTS["news"] * news
    )

    return IntentScore(
        company_id=company_id,
        score_date=date.today(),
        hiring_intent=round(hiring, 4),
        growth_intent=round(growth, 4),
        funding_intent=round(funding, 4),
        composite_score=round(composite, 4),
    )

"""Scores a validated payment: features, then the score, then the
decision, and the response the merchant gets."""

from dataclasses import dataclass
from typing import Any

from bannin.decision import decide
from bannin.features import build_features
from bannin.scorer import StubScorer
from bannin.thresholds import Thresholds


@dataclass(frozen=True)
class ScoredPayment:
    """The response, and what produced it, for the payment's log row."""

    response: dict[str, Any]
    features: dict[str, Any]
    model_version: str
    thresholds_version: str


def score_payment(
    fields: dict[str, Any],
    ignored: list[dict[str, str]],
    scorer: StubScorer,
    thresholds: Thresholds,
) -> ScoredPayment:
    """Scores the accepted fields and builds the response, with the
    fields in the order api/openapi.yaml lists them (ScoreResponse)."""
    features = build_features(fields)
    score = scorer.score(features)
    response = {
        "payment_id": fields["payment_id"],
        "decision": decide(score.value, thresholds),
        # Unrounded: the decision was made on this exact value.
        "score": score.value,
        "reasons": [],  # no reasons until a real model gives them
        "ignored_fields": ignored,
    }
    return ScoredPayment(
        response=response,
        features=features,
        model_version=score.model_version,
        thresholds_version=thresholds.version,
    )

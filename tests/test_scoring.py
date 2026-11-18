"""Scoring a validated payment, through to the response body."""

import pytest

from bannin.scorer import StubScorer
from bannin.scoring import ScoredPayment, score_payment
from bannin.thresholds import Thresholds

THRESHOLDS = Thresholds(version="thresholds-v1", review=60, decline=85)
FIELDS = {
    "payment_id": "pay_001",
    "amount": 1000,
    "currency": "USD",
    "card_id": "card_abc",
}
IGNORED = [{"field": "card_bin", "code": "invalid", "message": "must be 6 or 8 digits"}]


@pytest.mark.parametrize(
    ("score", "decision"),
    [(10, "approve"), (70, "review"), (90, "decline")],
)
def test_the_response_for_each_decision(score, decision):
    scored = score_payment(FIELDS, IGNORED, StubScorer(score=score), THRESHOLDS)
    assert scored == ScoredPayment(
        response={
            "payment_id": "pay_001",
            "decision": decision,
            "score": score,
            "reasons": [],
            "ignored_fields": IGNORED,
        },
        features={},
        model_version="stub-0.1.0",
        thresholds_version="thresholds-v1",
    )


def test_the_fields_come_in_the_order_of_the_spec():
    scored = score_payment(FIELDS, [], StubScorer(), THRESHOLDS)
    assert list(scored.response) == [
        "payment_id",
        "decision",
        "score",
        "reasons",
        "ignored_fields",
    ]


def test_the_score_is_not_rounded():
    scored = score_payment(FIELDS, [], StubScorer(score=59.9999), THRESHOLDS)
    assert scored.response["score"] == 59.9999
    assert scored.response["decision"] == "approve"

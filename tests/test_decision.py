"""The decision for a score, at and around each threshold."""

import pytest

from bannin.decision import decide
from bannin.thresholds import Thresholds

THRESHOLDS = Thresholds(version="thresholds-v1", review=60, decline=85)


@pytest.mark.parametrize(
    ("score", "decision"),
    [
        (0, "approve"),
        (59.99, "approve"),  # just below review, not rounded up
        (60, "review"),  # at review
        (84.5, "review"),
        (84.9999, "review"),  # just below decline
        (85, "decline"),  # at decline
        (100, "decline"),
    ],
)
def test_the_decision_for_a_score(score, decision):
    assert decide(score, THRESHOLDS) == decision


def test_decimal_thresholds_are_compared_exactly():
    thresholds = Thresholds(version="thresholds-v2", review=72.5, decline=90.25)
    assert decide(72.4999, thresholds) == "approve"
    assert decide(72.5, thresholds) == "review"
    assert decide(90.25, thresholds) == "decline"

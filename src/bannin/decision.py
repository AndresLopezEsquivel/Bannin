"""Turns a score into the decision the merchant gets, from the two
thresholds."""

from typing import Literal

from bannin.thresholds import Thresholds

# The values of `decision` in api/openapi.yaml.
Decision = Literal["approve", "review", "decline"]


def decide(score: float, thresholds: Thresholds) -> Decision:
    """Declines a score at or above the decline threshold; otherwise
    sends one at or above the review threshold to review; otherwise
    approves. The score is compared as given, never rounded: 59.99 is
    approved when review is 60."""
    # Decline is checked first: every score that reaches decline also
    # reaches review, so the other order would never decline.
    if score >= thresholds.decline:
        return "decline"
    if score >= thresholds.review:
        return "review"
    return "approve"

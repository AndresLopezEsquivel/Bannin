"""Loads the two decision thresholds and their config version, once, at
startup. Any problem stops the app from starting, so a mistyped
threshold can't quietly change decisions."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class ThresholdsError(Exception):
    """The thresholds failed a check. The message names the check."""


@dataclass(frozen=True)
class Thresholds:
    """A score at or above `decline` is declined; otherwise, at or above
    `review` goes to review. `version` names this pair of thresholds, so
    a logged decision can be traced to them."""

    version: str
    review: float
    decline: float


def _is_score(value: Any) -> bool:
    # `type(...) in` rejects true and false (a bool is an int in Python).
    # The range check also rejects nan and inf, which the TOML config
    # format allows: every comparison with nan is False, so
    # `0 <= nan <= 100` is False.
    return type(value) in (int, float) and 0 <= value <= 100


def load_thresholds(table: Mapping[str, Any]) -> Thresholds:
    """Returns the thresholds from the config's [thresholds] table, or
    raises ThresholdsError for the first of the four checks that fails."""
    for name in ("version", "review", "decline"):
        if name not in table:
            raise ThresholdsError(f"thresholds check 1: {name} is missing.")
    review, decline, version = table["review"], table["decline"], table["version"]
    for name, value in (("review", review), ("decline", decline)):
        if not _is_score(value):
            raise ThresholdsError(
                f"thresholds check 2: {name} must be a number from 0 to 100."
            )
    if not review < decline:
        raise ThresholdsError(
            f"thresholds check 3: review ({review}) must be below decline ({decline})."
        )
    if not isinstance(version, str) or not version.strip():
        raise ThresholdsError("thresholds check 4: version must be non-blank text.")
    return Thresholds(version=version, review=review, decline=decline)

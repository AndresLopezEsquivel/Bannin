"""Scores a payment's features: the fraud risk from 0 to 100, and the
version of the model that produced it."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

# Approved under the thresholds the service ships with (review 60,
# decline 85), so the deployed service answers `approve`.
STUB_SCORE = 12.37
# Logged with each decision, so a decision made by the stub can't be
# mistaken for one made by a real model.
MODEL_VERSION = "stub-0.1.0"


@dataclass(frozen=True)
class Score:
    """The fraud risk from 0 to 100, unrounded, and the model behind it."""

    value: float
    model_version: str


class StubScorer:
    """Stands in for the fraud model: returns the same score for every
    payment. A real model replaces it with the same `score` method."""

    def __init__(self, score: float = STUB_SCORE) -> None:
        # The app always uses the default. Tests pass another score to
        # reach review and decline.
        self._score = score

    def score(self, features: Mapping[str, Any]) -> Score:
        """Returns the fixed score; the features aren't read."""
        return Score(value=self._score, model_version=MODEL_VERSION)

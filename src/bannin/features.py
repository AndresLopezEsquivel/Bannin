"""Turns a validated request into the features the model scores."""

from collections.abc import Mapping
from typing import Any


def build_features(fields: Mapping[str, Any]) -> dict[str, Any]:
    """Returns the features, by name, from the request's accepted fields.

    Empty for now: the stub scorer returns a fixed score and reads no
    features. A real model brings its own features here, and the scorer
    and the decision step don't change. The features are logged with
    each decision as computed, so `{}` is what the log will show.
    """
    # A new dict on every call, never a shared one, so a caller that
    # adds to it can't change the next request's features.
    return {}

"""Loads the two decision thresholds and their config version, once, at
startup. Any problem stops the app from starting, so a mistyped
threshold can't quietly change decisions."""

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ThresholdsError(Exception):
    """The thresholds can't be loaded. The message names the failed
    check, or the file problem."""


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
    # The range check also rejects nan and inf, which TOML (the format of
    # config/thresholds.toml) allows: every comparison with nan is False,
    # so `0 <= nan <= 100` is False.
    return type(value) in (int, float) and 0 <= value <= 100


def load_thresholds(table: Mapping[str, Any]) -> Thresholds:
    """Returns the thresholds from the parsed thresholds file, or raises
    ThresholdsError for the first of the four checks that fails."""
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


def load_thresholds_file(path: str | Path) -> Thresholds:
    """Reads the TOML file at `path`, then checks it as load_thresholds
    does. A file that can't be read or parsed raises ThresholdsError."""
    try:
        # tomllib reads bytes, so it decodes the file as UTF-8 itself.
        with open(path, "rb") as file:
            table = tomllib.load(file)
    except OSError as error:
        raise ThresholdsError(
            f"thresholds file: can't read {path} ({error.strerror})."
        ) from error
    except tomllib.TOMLDecodeError as error:
        raise ThresholdsError(
            f"thresholds file: {path} isn't valid TOML ({error})."
        ) from error
    return load_thresholds(table)


def load_thresholds_from_env(environ: Mapping[str, str]) -> Thresholds:
    """Loads the file BANNIN_THRESHOLDS_FILE names. There's no default
    path, so the app never runs on thresholds from an unexpected file."""
    path = environ.get("BANNIN_THRESHOLDS_FILE", "")
    if not path.strip():
        raise ThresholdsError("BANNIN_THRESHOLDS_FILE is missing or empty.")
    return load_thresholds_file(path)

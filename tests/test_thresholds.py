"""The startup checks on the decision thresholds, and reading them from
the thresholds file."""

from pathlib import Path

import pytest

from bannin.thresholds import (
    Thresholds,
    ThresholdsError,
    load_thresholds,
    load_thresholds_file,
    load_thresholds_from_env,
)

# The file the image ships with.
SHIPPED = Path(__file__).parents[1] / "config" / "thresholds.toml"

VALID = {"version": "thresholds-v1", "review": 60, "decline": 85}


def test_valid_thresholds_load():
    assert load_thresholds(VALID) == Thresholds("thresholds-v1", 60, 85)


def test_decimal_thresholds_load_unrounded():
    loaded = load_thresholds({**VALID, "review": 59.5, "decline": 85.25})
    assert (loaded.review, loaded.decline) == (59.5, 85.25)


def test_the_full_range_loads():
    loaded = load_thresholds({**VALID, "review": 0, "decline": 100})
    assert (loaded.review, loaded.decline) == (0, 100)


@pytest.mark.parametrize("name", ["version", "review", "decline"])
def test_a_missing_value_fails_check_1(name):
    table = {k: v for k, v in VALID.items() if k != name}
    with pytest.raises(ThresholdsError, match=f"^thresholds check 1: {name} "):
        load_thresholds(table)


@pytest.mark.parametrize("name", ["review", "decline"])
@pytest.mark.parametrize(
    "value",
    ["60", True, False, float("nan"), float("inf"), -1, 100.5, None],
)
def test_a_non_score_fails_check_2(name, value):
    with pytest.raises(ThresholdsError, match=f"^thresholds check 2: {name} "):
        load_thresholds({**VALID, name: value})


@pytest.mark.parametrize(("review", "decline"), [(85, 60), (70, 70)])
def test_review_not_below_decline_fails_check_3(review, decline):
    with pytest.raises(ThresholdsError, match="^thresholds check 3: "):
        load_thresholds({**VALID, "review": review, "decline": decline})


@pytest.mark.parametrize("version", ["", "   ", 1])
def test_a_blank_or_non_text_version_fails_check_4(version):
    with pytest.raises(ThresholdsError, match="^thresholds check 4: "):
        load_thresholds({**VALID, "version": version})


def test_the_shipped_file_loads():
    assert load_thresholds_file(SHIPPED) == Thresholds("thresholds-v1", 60, 85)


def test_a_file_that_fails_a_check_names_the_check(tmp_path):
    path = tmp_path / "thresholds.toml"
    path.write_text('version = "thresholds-v1"\nreview = 85\ndecline = 60\n')
    with pytest.raises(ThresholdsError, match="^thresholds check 3: "):
        load_thresholds_file(path)


def test_a_missing_file_stops_loading(tmp_path):
    with pytest.raises(ThresholdsError, match="^thresholds file: can't read "):
        load_thresholds_file(tmp_path / "missing.toml")


def test_a_file_that_isnt_toml_stops_loading(tmp_path):
    path = tmp_path / "thresholds.toml"
    path.write_text("review: 60\n")  # YAML, not TOML
    with pytest.raises(ThresholdsError, match="isn't valid TOML"):
        load_thresholds_file(path)


def test_the_env_names_the_file():
    loaded = load_thresholds_from_env({"BANNIN_THRESHOLDS_FILE": str(SHIPPED)})
    assert loaded.version == "thresholds-v1"


@pytest.mark.parametrize("environ", [{}, {"BANNIN_THRESHOLDS_FILE": "  "}])
def test_no_file_named_stops_loading(environ):
    with pytest.raises(ThresholdsError, match="^BANNIN_THRESHOLDS_FILE is missing"):
        load_thresholds_from_env(environ)

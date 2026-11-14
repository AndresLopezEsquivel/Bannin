"""The key check, called directly with made-up keys."""

import secrets

import pytest

from bannin.auth import check_key
from bannin.errors import ApiError

# New random keys on every run; none of them is a real key.
KEY_1 = "bn_" + secrets.token_urlsafe(32)
KEY_2 = "bn_" + secrets.token_urlsafe(32)
KEYS = {"key_01": KEY_1, "key_02": KEY_2}


@pytest.mark.parametrize(
    ("header", "key_id"),
    [
        (f"Bearer {KEY_1}", "key_01"),
        (f"Bearer {KEY_2}", "key_02"),
        (f"bearer {KEY_1}", "key_01"),  # the scheme is case-insensitive
        (f"Bearer  {KEY_1} ", "key_01"),  # extra spaces around the key
    ],
)
def test_valid_key_returns_its_id(header, key_id):
    assert check_key(header, KEYS) == key_id


@pytest.mark.parametrize(
    "header",
    [None, "", "Bearer", "Bearer   ", f"Basic {KEY_1}", KEY_1],
)
def test_missing_key(header):
    with pytest.raises(ApiError) as caught:
        check_key(header, KEYS)
    assert (caught.value.status, caught.value.code) == (401, "api_key_missing")
    assert caught.value.headers == {"WWW-Authenticate": "Bearer"}


@pytest.mark.parametrize(
    "sent",
    [
        "bn_wrong",
        KEY_1 + "x",  # a valid key with one more character
        KEY_1[:-1],  # a valid key with one character less
        KEY_1.upper(),  # keys are case-sensitive
        "bn_ünïcode",  # non-ASCII must give a 401, not a 500
        f"{KEY_1} {KEY_2}",  # two keys at once
    ],
)
def test_invalid_key(sent):
    with pytest.raises(ApiError) as caught:
        check_key(f"Bearer {sent}", KEYS)
    assert (caught.value.status, caught.value.code) == (401, "api_key_invalid")
    assert caught.value.headers == {"WWW-Authenticate": "Bearer"}
    assert sent not in caught.value.message


def test_no_keys_loaded_rejects_everything():
    with pytest.raises(ApiError):
        check_key(f"Bearer {KEY_1}", {})

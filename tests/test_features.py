"""The features built from a validated request."""

import pytest

from bannin.features import build_features

REQUIRED = {
    "payment_id": "pay_001",
    "amount": 1000,
    "currency": "USD",
    "card_id": "card_abc",
}


@pytest.mark.parametrize(
    "fields",
    [
        REQUIRED,
        {**REQUIRED, "card_bin": "42424242", "email": "test@example.com"},
    ],
)
def test_no_features_yet(fields):
    assert build_features(fields) == {}


def test_each_call_gets_its_own_dict():
    first = build_features(REQUIRED)
    first["added"] = 1
    assert build_features(REQUIRED) == {}

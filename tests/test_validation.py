"""The field checks, called directly. Every value is made up."""

import pytest

from bannin.errors import ApiError
from bannin.validation import check_required

# The spec's `required_only` example.
VALID = {
    "payment_id": "pay_001",
    "amount": 1000,
    "currency": "USD",
    "card_id": "card_abc",
}


def error_for(body):
    """Runs the check, which must fail, and returns (code, field)."""
    with pytest.raises(ApiError) as caught:
        check_required(body)
    assert caught.value.status == 400
    assert caught.value.error_type == "invalid_request"
    return caught.value.code, caught.value.field


def test_valid_request_returns_the_four_fields():
    assert check_required({**VALID, "colour": "red"}) == VALID


@pytest.mark.parametrize("field", list(VALID))
@pytest.mark.parametrize("value", ["absent", None, "", "   "])
def test_missing_empty_or_blank(field, value):
    body = {k: v for k, v in VALID.items() if k != field}
    if value != "absent":
        body[field] = value
    assert error_for(body) == ("parameter_missing", field)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("payment_id", 123),
        ("payment_id", "p" * 256),
        ("amount", 0),
        ("amount", -5),
        ("amount", 100_000_000),
        ("amount", 1000.0),
        ("amount", True),
        ("amount", "1000"),
        ("currency", "usd"),
        ("currency", "US"),
        ("currency", "USD\n"),
        ("currency", 840),
        ("card_id", ["card_abc"]),
        ("card_id", "c" * 256),
    ],
)
def test_wrong_type_or_format(field, value):
    assert error_for({**VALID, field: value}) == ("parameter_invalid", field)


@pytest.mark.parametrize(("field", "value"), [("amount", 1), ("amount", 99_999_999)])
def test_amount_limits_are_valid(field, value):
    assert check_required({**VALID, field: value})[field] == value


def test_the_earlier_field_is_reported():
    # card_id is missing too, but amount comes first.
    body = {"payment_id": "pay_001", "amount": 0, "currency": "USD"}
    assert error_for(body) == ("parameter_invalid", "amount")


def test_message_never_contains_the_value():
    with pytest.raises(ApiError) as caught:
        check_required({**VALID, "amount": 4242424242424242})
    assert "4242" not in caught.value.message
    assert caught.value.message == "amount must be a whole number from 1 to 99999999."

"""The field checks, called directly. Every value is made up."""

import pytest

from bannin.errors import ApiError
from bannin.validation import check_request, check_required

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


# Every optional field this check covers, with a valid made-up value.
OPTIONAL = {
    "order_id": "ord_001",
    "card_bin": "424242",
    "card_last4": "4242",
    "customer_id": "cus_001",
    "name": "Test Person",
    "phone": "+14155550100",
    "device_id": "dev_001",
    "user_agent": "u" * 1024,
}


def test_valid_optional_fields_are_accepted():
    body = {**VALID, **OPTIONAL, "card_bin": "42424242", "order_id": "   "}
    assert check_request(body) == (body, [])


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("card_bin", "4242", "must be 6 or 8 digits"),
        ("card_bin", "4242424", "must be 6 or 8 digits"),
        ("card_bin", 424242, "must be 6 or 8 digits"),
        ("card_last4", "424", "must be 4 digits"),
        ("card_last4", "\u0664\u0662\u0664\u0662", "must be 4 digits"),  # Arabic-Indic
        (
            "phone",
            "14155550100",
            "must be E.164: + then 1 to 15 digits, such as +14155550100",
        ),
        (
            "phone",
            "+" + "1" * 16,
            "must be E.164: + then 1 to 15 digits, such as +14155550100",
        ),
        ("user_agent", "u" * 1025, "must be text of 1 to 1024 characters"),
        ("order_id", "", "must be text of 1 to 255 characters"),
        ("name", None, "must be text of 1 to 255 characters"),
        ("device_id", "d" * 256, "must be text of 1 to 255 characters"),
        ("customer_id", ["cus_001"], "must be text of 1 to 255 characters"),
    ],
)
def test_invalid_optional_field_is_ignored(field, value, message):
    accepted, ignored = check_request({**VALID, field: value})
    assert accepted == VALID
    assert ignored == [{"field": field, "code": "invalid", "message": message}]


def test_unrecognized_fields_are_ignored_in_the_order_sent():
    body = {"colour": "red", **VALID, "card_bin": "4242", "size": 9}
    accepted, ignored = check_request(body)
    assert accepted == VALID
    assert [(i["field"], i["code"]) for i in ignored] == [
        ("colour", "unrecognized"),
        ("card_bin", "invalid"),
        ("size", "unrecognized"),
    ]
    assert ignored[0]["message"] == "is not a field Bannin uses"


def test_ignored_fields_never_contain_the_value():
    _, ignored = check_request({**VALID, "card_bin": "4242", "secret": "s3cr3t"})
    assert "4242" not in str(ignored)
    assert "s3cr3t" not in str(ignored)


def test_a_required_field_still_fails_first():
    with pytest.raises(ApiError) as caught:
        check_request({**VALID, "amount": 0, "card_bin": "4242"})
    assert caught.value.field == "amount"

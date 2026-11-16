"""Checks the fields of a scoring request against the rules in
api/openapi.yaml."""

import re
from typing import Any

from bannin.errors import ApiError

MAX_TEXT = 255
MAX_AMOUNT = 99_999_999


def _present(body: dict[str, Any], name: str) -> Any:
    """Returns the field's value. Absent, null, empty and blank count
    as missing."""
    value = body.get(name)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ApiError(
            400, "invalid_request", "parameter_missing", f"{name} is required.", name
        )
    return value


def _invalid(name: str, rule: str) -> ApiError:
    return ApiError(
        400, "invalid_request", "parameter_invalid", f"{name} must be {rule}.", name
    )


def _text(body: dict[str, Any], name: str) -> str:
    value = _present(body, name)
    if not isinstance(value, str) or len(value) > MAX_TEXT:
        raise _invalid(name, f"text of 1 to {MAX_TEXT} characters")
    return value


def _amount(body: dict[str, Any]) -> int:
    value = _present(body, "amount")
    # `type(...) is int` rejects true and false (a bool is an int in
    # Python) and 1000.0 (json.loads gives a float).
    if type(value) is not int or not 1 <= value <= MAX_AMOUNT:
        raise _invalid("amount", f"a whole number from 1 to {MAX_AMOUNT}")
    return value


def _currency(body: dict[str, Any]) -> str:
    value = _present(body, "currency")
    # fullmatch, so "USD\n" doesn't pass the way it would with `$`.
    if not isinstance(value, str) or not re.fullmatch(r"[A-Z]{3}", value):
        raise _invalid("currency", "three uppercase letters (ISO 4217), such as USD")
    return value


def check_required(body: dict[str, Any]) -> dict[str, Any]:
    """Returns the four required fields, or raises a 400 for the first
    one that's missing or invalid, in this order."""
    return {
        "payment_id": _text(body, "payment_id"),
        "amount": _amount(body),
        "currency": _currency(body),
        "card_id": _text(body, "card_id"),
    }

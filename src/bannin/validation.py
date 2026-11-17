"""Checks the fields of a scoring request against the rules in
api/openapi.yaml."""

import ipaddress
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any

from email_validator import EmailNotValidError, validate_email

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


def _text_of(max_len: int) -> Callable[[Any], bool]:
    """Returns a check that passes text of 1 to max_len characters."""
    return lambda value: isinstance(value, str) and 1 <= len(value) <= max_len


def _matches(pattern: str) -> Callable[[Any], bool]:
    """Returns a check that passes text matching the whole pattern."""
    # [0-9] rather than \d, which also matches digits from other scripts.
    return lambda value: isinstance(value, str) and bool(re.fullmatch(pattern, value))


# RFC 3339's date-time. fromisoformat alone also accepts no offset,
# 20261030T140500Z, week dates, +0200, and 24:00 as the next midnight.
RFC3339 = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt]([01][0-9]|2[0-3]):[0-9]{2}:[0-9]{2}"
    r"(\.[0-9]+)?([Zz]|[+-][0-9]{2}:[0-9]{2})"
)


def _date_time(value: Any) -> bool:
    """Passes RFC 3339 with an offset, for a date and time that exist."""
    if not isinstance(value, str) or not RFC3339.fullmatch(value):
        return False
    try:
        # upper(): fromisoformat rejects the lowercase t and z RFC 3339 allows.
        # It also rejects 2026-02-30 and the leap second :60.
        datetime.fromisoformat(value.upper())
    except ValueError:
        return False
    return True


def _ip_address(value: Any) -> bool:
    """Passes IPv4 or IPv6 text."""
    # ip_address also takes an int, and a %scope (fe80::1%eth0) that the
    # JSON Schema ipv6 format doesn't allow; both are rejected first.
    if not isinstance(value, str) or "%" in value:
        return False
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return False
    return True


def _email(value: Any) -> bool:
    """Passes an email address as RFC 5321 defines it."""
    if not isinstance(value, str):
        return False
    try:
        validate_email(
            value,
            check_deliverability=False,  # no DNS lookup on every request
            allow_smtputf8=False,  # RFC 5321 is ASCII before the @
            # RFC 5321 allows both; the library turns them off by default.
            allow_quoted_local=True,  # "a b"@example.com
            allow_domain_literal=True,  # test@[192.0.2.1]
        )
    except EmailNotValidError:
        return False
    return True


TEXT = f"must be text of 1 to {MAX_TEXT} characters"
UNRECOGNIZED = "is not a field Bannin uses"

# A check, and the message when the check fails. The message leaves out
# the field's name, since the ignored entry's `field` already gives it,
# and never includes the value.
Rule = tuple[Callable[[Any], bool], str]

# Each optional field and its rule.
OPTIONAL: dict[str, Rule] = {
    "attempted_at": (
        _date_time,
        "must be RFC 3339 with an offset, such as 2026-10-30T14:05:00Z",
    ),
    "order_id": (_text_of(MAX_TEXT), TEXT),
    "card_bin": (_matches(r"[0-9]{6}([0-9]{2})?"), "must be 6 or 8 digits"),
    "card_last4": (_matches(r"[0-9]{4}"), "must be 4 digits"),
    "customer_id": (_text_of(MAX_TEXT), TEXT),
    "name": (_text_of(MAX_TEXT), TEXT),
    "email": (_email, "must be an email address, such as test@example.com"),
    "phone": (
        _matches(r"\+[0-9]{1,15}"),
        "must be E.164: + then 1 to 15 digits, such as +14155550100",
    ),
    "ip_address": (
        _ip_address,
        "must be an IPv4 or IPv6 address, such as 192.0.2.1",
    ),
    "device_id": (_text_of(MAX_TEXT), TEXT),
    "user_agent": (_text_of(1024), "must be text of 1 to 1024 characters"),
}

# Known fields whose checks aren't written yet: skipped, not reported.
NOT_CHECKED_YET = {
    "billing_address",
    "shipping_address",
}


def _ignored(name: str, code: str, message: str) -> dict[str, str]:
    return {"field": name, "code": code, "message": message}


def _check_fields(
    fields: dict[str, Any], rules: dict[str, Rule]
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Returns the fields that pass their rules, and the ignored ones, in
    the order sent."""
    accepted: dict[str, Any] = {}
    ignored: list[dict[str, str]] = []
    for name, value in fields.items():
        rule = rules.get(name)
        if rule is None:
            ignored.append(_ignored(name, "unrecognized", UNRECOGNIZED))
            continue
        check, message = rule
        if check(value):
            accepted[name] = value
        else:
            ignored.append(_ignored(name, "invalid", message))
    return accepted, ignored


def check_request(body: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Returns the accepted fields and the ignored ones. Raises a 400 if a
    required field is missing or invalid; an optional field that's invalid
    or unrecognized is only listed as ignored, in the order it was sent."""
    required = check_required(body)
    rest = {
        name: value
        for name, value in body.items()
        # Required fields were checked above; the others are checked later.
        if name not in required and name not in NOT_CHECKED_YET
    }
    optional, ignored = _check_fields(rest, OPTIONAL)
    return {**required, **optional}, ignored

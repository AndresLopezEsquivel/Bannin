"""POST /score on the real app: the key first, then the body, then the
required fields."""

import secrets

import pytest
from fastapi.testclient import TestClient

from bannin.main import app

# A new random key on every run; not a real key.
KEY = "bn_" + secrets.token_urlsafe(32)
AUTH = {"Authorization": f"Bearer {KEY}"}

client = TestClient(app)


@pytest.fixture(autouse=True)
def loaded_keys():
    """Loads the made-up key for each test, then puts the old keys back."""
    old = app.state.keys
    app.state.keys = {"key_01": KEY}
    yield
    app.state.keys = old


def error_of(response):
    return response.json()["error"]


def test_no_key_comes_before_a_broken_body():
    response = client.post("/score", content=b'{"payment_id":')
    assert response.status_code == 401
    assert error_of(response)["code"] == "api_key_missing"
    assert response.headers["www-authenticate"] == "Bearer"


def test_wrong_key_comes_before_a_broken_body():
    response = client.post(
        "/score", content=b'{"payment_id":', headers={"Authorization": "Bearer bn_x"}
    )
    assert response.status_code == 401
    assert error_of(response)["code"] == "api_key_invalid"


@pytest.mark.parametrize(
    "body",
    [
        b'{"payment_id":',  # broken JSON
        b"",  # empty
        b"[1, 2]",  # an array
        b'"pay_001"',  # a string
        b"42",  # a number
        b"null",
        b"\xff\xfe\xfa",  # bytes that aren't text
        b"[" * 100_000,  # nested too deeply
    ],
)
def test_body_that_is_not_a_json_object(body):
    response = client.post("/score", content=body, headers=AUTH)
    assert response.status_code == 400
    assert error_of(response) == {
        "type": "invalid_request",
        "code": "body_invalid",
        "message": "The body must be a JSON object.",
    }


# The spec's (api/openapi.yaml) `required_only` example.
VALID = {
    "payment_id": "pay_001",
    "amount": 1000,
    "currency": "USD",
    "card_id": "card_abc",
}


def test_no_key_comes_before_a_missing_field():
    response = client.post("/score", content=b"{}")
    assert response.status_code == 401
    assert error_of(response)["code"] == "api_key_missing"


def test_missing_field_gets_400_with_the_field():
    response = client.post("/score", content=b"{}", headers=AUTH)
    assert response.status_code == 400
    assert error_of(response) == {
        "type": "invalid_request",
        "code": "parameter_missing",
        "message": "payment_id is required.",
        "field": "payment_id",
    }


def test_invalid_field_gets_400_with_the_field():
    response = client.post("/score", json={**VALID, "amount": 0}, headers=AUTH)
    assert response.status_code == 400
    assert error_of(response) == {
        "type": "invalid_request",
        "code": "parameter_invalid",
        "message": "amount must be a whole number from 1 to 99999999.",
        "field": "amount",
    }


def test_valid_request_gets_503_until_scoring_exists():
    response = client.post("/score", json=VALID, headers=AUTH)
    assert response.status_code == 503
    assert error_of(response)["code"] == "service_unavailable"


def test_invalid_optional_field_still_gets_503():
    body = {**VALID, "card_bin": "4242", "colour": "red"}
    response = client.post("/score", json=body, headers=AUTH)
    assert response.status_code == 503

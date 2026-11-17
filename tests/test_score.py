"""POST /score on the real app: the key first, then the body's size,
then the body, then the required fields, then scoring."""

import asyncio
import json
import secrets

import pytest
from fastapi.testclient import TestClient

from bannin.main import app
from bannin.scorer import StubScorer
from bannin.thresholds import Thresholds

# A new random key on every run; not a real key.
KEY = "bn_" + secrets.token_urlsafe(32)
AUTH = {"Authorization": f"Bearer {KEY}"}

client = TestClient(app)


@pytest.fixture(autouse=True)
def loaded_state():
    """Sets what startup would (the made-up key, thresholds and the stub
    scorer) for each test, then puts the old values back."""
    names = ("keys", "thresholds", "scorer")
    old = {name: getattr(app.state, name, None) for name in names}
    app.state.keys = {"key_01": KEY}
    app.state.thresholds = Thresholds(version="thresholds-v1", review=60, decline=85)
    app.state.scorer = StubScorer()
    yield
    for name, value in old.items():
        setattr(app.state, name, value)


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
        b"[" * 65_536,  # nested too deeply, at the size limit
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


def test_body_at_the_size_limit_is_read():
    # Trailing spaces are valid JSON, so this passes every check.
    body = json.dumps(VALID).encode().ljust(65_536)
    assert client.post("/score", content=body, headers=AUTH).status_code == 503


def test_body_over_the_size_limit_gets_413():
    response = client.post("/score", content=b" " * 65_537, headers=AUTH)
    assert response.status_code == 413
    assert error_of(response) == {
        "type": "invalid_request",
        "code": "body_too_large",
        "message": "The body must be at most 65536 bytes.",
    }


def test_chunked_body_over_the_size_limit_gets_413():
    # A generator has no length, so the client sends it chunked.
    chunks = (b" " * 1000 for _ in range(70))
    response = client.post("/score", content=chunks, headers=AUTH)
    assert response.status_code == 413


def test_no_key_comes_before_the_body_size():
    response = client.post("/score", content=b" " * 70_000)
    assert response.status_code == 401


def send_raw(content_length, chunks):
    """Calls the app the way Uvicorn does (ASGI), since the test client
    always sets Content-Length to the real size. Returns the status and
    how many chunks the app read."""
    pending, sent, reads = list(chunks), [], 0

    async def receive():
        nonlocal reads
        reads += 1
        body = pending.pop(0) if pending else b""
        return {"type": "http.request", "body": body, "more_body": bool(pending)}

    async def send(message):
        sent.append(message)

    headers = {**AUTH, "Content-Length": str(content_length)}
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/score",
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    asyncio.run(app(scope, receive, send))
    return sent[0]["status"], reads


def test_large_declared_length_gets_413_without_reading():
    assert send_raw(524_288_000, [b"{}"]) == (413, 0)


def test_short_declared_length_with_a_long_body_gets_413():
    # Byte 65,537 arrives in chunk 66, and the app stops reading there.
    assert send_raw(2000, [b" " * 1000] * 70) == (413, 66)

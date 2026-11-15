"""The error object, on a small app with routes that fail on purpose."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from bannin.errors import ApiError, add_error_handlers

app = FastAPI()
add_error_handlers(app)


@app.get("/with-field")
def with_field():
    raise ApiError(
        400,
        "invalid_request",
        "parameter_missing",
        "amount is required.",
        field="amount",
    )


@app.get("/no-field")
def no_field():
    raise ApiError(
        401,
        "authentication",
        "api_key_missing",
        "Send an API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.get("/bug")
def bug():
    raise RuntimeError("secret detail")


# Returns the 500 response instead of raising the bug in the test.
client = TestClient(app, raise_server_exceptions=False)


def test_api_error_with_field():
    response = client.get("/with-field")
    assert response.status_code == 400
    assert response.json() == {
        "error": {
            "type": "invalid_request",
            "code": "parameter_missing",
            "message": "amount is required.",
            "field": "amount",
        }
    }


def test_api_error_without_field_and_with_header():
    response = client.get("/no-field")
    assert response.status_code == 401
    assert "field" not in response.json()["error"]
    assert response.headers["www-authenticate"] == "Bearer"


def test_unexpected_exception_is_a_500_without_details():
    response = client.get("/bug")
    assert response.status_code == 500
    error = response.json()["error"]
    assert (error["type"], error["code"]) == ("server_error", "internal_error")
    assert "secret detail" not in response.text

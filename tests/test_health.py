"""GET /health, and the routes the app must not serve."""

import pytest
from fastapi.testclient import TestClient

from bannin.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_rejects_post():
    assert client.post("/health").status_code == 405


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_generated_docs_are_not_served(path):
    assert client.get(path).status_code == 404


def test_health_is_not_in_the_schema():
    assert "/health" not in app.openapi()["paths"]

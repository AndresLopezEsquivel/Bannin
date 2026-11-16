"""Loading the keys at startup, with made-up keys."""

import secrets

import pytest
from fastapi.testclient import TestClient

from bannin.keys import KeyConfigError, load_keys
from bannin.main import app

# New random keys on every run; none of them is a real key.
KEY_1 = "bn_" + secrets.token_urlsafe(32)
KEY_2 = "bn_" + secrets.token_urlsafe(32)


def env(keys: str) -> dict[str, str]:
    return {"BANNIN_KEYS_SOURCE": "env", "BANNIN_API_KEYS": keys}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (f"key_01={KEY_1}", {"key_01": KEY_1}),
        (f"key_01={KEY_1},key_02={KEY_2}", {"key_01": KEY_1, "key_02": KEY_2}),
        (f" key_01={KEY_1} , key_02={KEY_2} ", {"key_01": KEY_1, "key_02": KEY_2}),
    ],
)
def test_valid_keys(value, expected):
    assert load_keys(env(value)) == expected


@pytest.mark.parametrize(
    "environ",
    [
        {},  # no source
        {"BANNIN_KEYS_SOURCE": "file", "BANNIN_API_KEYS": f"key_01={KEY_1}"},
        {"BANNIN_KEYS_SOURCE": "env"},  # no keys
        env(""),
        env("  "),
        env(KEY_1),  # a key without its ID
        env(f"Key-1={KEY_1}"),  # a bad ID
        env("key_01="),  # an ID without its key
        env(f"key_01={KEY_1},"),  # an empty entry
        env(f"key_01={KEY_1},key_01={KEY_2}"),  # the same ID twice
        env(f"key_01={KEY_1},key_02={KEY_1}"),  # the same key twice
        env(f"key_01={KEY_1},key_02={KEY_2},key_03=bn_x"),  # three keys
    ],
)
def test_bad_config_stops_loading_without_naming_a_key(environ):
    with pytest.raises(KeyConfigError) as caught:
        load_keys(environ)
    assert KEY_1 not in str(caught.value)
    assert KEY_2 not in str(caught.value)


@pytest.fixture
def restore_keys():
    """Puts back the app's keys after a test that starts the app."""
    old = app.state.keys
    yield
    app.state.keys = old


def test_app_loads_keys_at_startup(monkeypatch, restore_keys):
    monkeypatch.setenv("BANNIN_KEYS_SOURCE", "env")
    monkeypatch.setenv("BANNIN_API_KEYS", f"key_01={KEY_1}")
    # `with` runs the lifespan: startup on entry, shutdown on exit.
    with TestClient(app) as client:
        response = client.post(
            "/score",
            json={
                "payment_id": "pay_001",
                "amount": 1000,
                "currency": "USD",
                "card_id": "card_abc",
            },
            headers={"Authorization": f"Bearer {KEY_1}"},
        )
    assert response.status_code == 503  # the key and the request were accepted


def test_app_does_not_start_without_keys(monkeypatch, restore_keys):
    monkeypatch.setenv("BANNIN_KEYS_SOURCE", "env")
    monkeypatch.delenv("BANNIN_API_KEYS", raising=False)
    with pytest.raises(KeyConfigError), TestClient(app):
        pass

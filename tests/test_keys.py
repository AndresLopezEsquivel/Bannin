"""Loading the keys at startup, with made-up keys, and the app's startup
with its keys and thresholds."""

import secrets
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bannin.keys import KeyConfigError, load_keys
from bannin.main import app
from bannin.thresholds import ThresholdsError

# New random keys on every run; none of them is a real key.
KEY_1 = "bn_" + secrets.token_urlsafe(32)
KEY_2 = "bn_" + secrets.token_urlsafe(32)

# The thresholds file the image ships with.
SHIPPED = Path(__file__).parents[1] / "config" / "thresholds.toml"


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
    """Puts back what startup sets on the app after a test that starts it."""
    names = ("keys", "thresholds", "scorer")
    old = {name: getattr(app.state, name, None) for name in names}
    yield
    for name, value in old.items():
        setattr(app.state, name, value)


def test_app_loads_keys_at_startup(monkeypatch, restore_keys):
    monkeypatch.setenv("BANNIN_KEYS_SOURCE", "env")
    monkeypatch.setenv("BANNIN_API_KEYS", f"key_01={KEY_1}")
    monkeypatch.setenv("BANNIN_THRESHOLDS_FILE", str(SHIPPED))
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
    assert response.status_code == 200  # the key and the request were accepted
    assert app.state.thresholds.version == "thresholds-v1"


def test_app_does_not_start_without_keys(monkeypatch, restore_keys):
    monkeypatch.setenv("BANNIN_KEYS_SOURCE", "env")
    monkeypatch.delenv("BANNIN_API_KEYS", raising=False)
    with pytest.raises(KeyConfigError), TestClient(app):
        pass


def test_app_does_not_start_with_bad_thresholds(monkeypatch, restore_keys, tmp_path):
    monkeypatch.setenv("BANNIN_KEYS_SOURCE", "env")
    monkeypatch.setenv("BANNIN_API_KEYS", f"key_01={KEY_1}")
    bad = tmp_path / "thresholds.toml"
    bad.write_text('version = "thresholds-v1"\nreview = 85\ndecline = 60\n')
    monkeypatch.setenv("BANNIN_THRESHOLDS_FILE", str(bad))
    with pytest.raises(ThresholdsError, match="^thresholds check 3: "), TestClient(app):
        pass

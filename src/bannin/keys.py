"""Loads the valid API keys once, at startup. Any problem stops the app
from starting, so a misconfigured service fails visibly instead of
rejecting every request."""

import re
from collections.abc import Mapping
from typing import Any

import boto3

# Up to two keys at once, so a key can be replaced without downtime.
MAX_KEYS = 2
# A key's ID, such as key_01. Not secret: it's what gets logged.
_KEY_ID = re.compile(r"key_\d{2}")
# In Parameter Store, each key is a parameter under this path, such as
# /bannin/api-keys/key_01; the last segment is its ID.
SSM_PATH = "/bannin/api-keys"


class KeyConfigError(Exception):
    """The keys can't be loaded. Messages name key IDs, never keys."""


def _keys_from_env(environ: Mapping[str, str]) -> dict[str, str]:
    """Parse BANNIN_API_KEYS, such as "key_01=bn_abc,key_02=bn_def"."""
    value = environ.get("BANNIN_API_KEYS", "")
    if not value.strip():
        raise KeyConfigError("BANNIN_API_KEYS is missing or empty.")
    keys: dict[str, str] = {}
    entries = [e.strip() for e in value.split(",")]
    for number, entry in enumerate(entries, start=1):
        key_id, _, key = entry.partition("=")
        # Only the entry's position is named: a malformed entry may be a
        # key pasted without its ID.
        if not _KEY_ID.fullmatch(key_id) or not key:
            raise KeyConfigError(f"BANNIN_API_KEYS: entry {number} isn't key_NN=<key>.")
        if key_id in keys:
            raise KeyConfigError(f"BANNIN_API_KEYS: {key_id} appears twice.")
        keys[key_id] = key
    return keys


def _keys_from_ssm(client: Any) -> dict[str, str]:
    """Read every parameter directly under SSM_PATH, decrypted."""
    keys: dict[str, str] = {}
    # AWS returns at most 10 parameters per call; the paginator makes
    # as many calls as needed.
    pages = client.get_paginator("get_parameters_by_path").paginate(
        Path=SSM_PATH, WithDecryption=True
    )
    for page in pages:
        for parameter in page["Parameters"]:
            name = parameter["Name"]  # a name, not secret
            key_id = name.rsplit("/", 1)[-1]
            if not _KEY_ID.fullmatch(key_id):
                raise KeyConfigError(f"{name}: the ID isn't key_NN.")
            # A String parameter would keep the key unencrypted.
            if parameter["Type"] != "SecureString":
                raise KeyConfigError(f"{name} isn't a SecureString.")
            keys[key_id] = parameter["Value"]
    if not keys:
        raise KeyConfigError(f"No parameters under {SSM_PATH}.")
    return keys


def load_keys(environ: Mapping[str, str], ssm_client: Any = None) -> dict[str, str]:
    """Return the valid keys by ID, from the source BANNIN_KEYS_SOURCE names.

    With ssm, boto3 finds the region in AWS_DEFAULT_REGION and the
    credentials on its own (on the instance, its role's). Tests pass
    `ssm_client` to use a fake one instead.
    """
    source = environ.get("BANNIN_KEYS_SOURCE")
    if source == "env":
        keys = _keys_from_env(environ)
    elif source == "ssm":
        keys = _keys_from_ssm(ssm_client or boto3.client("ssm"))
    else:
        raise KeyConfigError("BANNIN_KEYS_SOURCE must be env or ssm.")

    if len(keys) > MAX_KEYS:
        raise KeyConfigError(f"{len(keys)} keys found; at most {MAX_KEYS} allowed.")
    # Two IDs for the same key would make the logged ID ambiguous.
    if len(set(keys.values())) != len(keys):
        raise KeyConfigError("Two key IDs have the same key.")
    return keys

"""The API key check: the first thing every scoring request goes through."""

import hmac
from collections.abc import Mapping

from bannin.errors import ApiError

# Both 401s tell the client which scheme to use (RFC 9110, section 15.5.2).
_CHALLENGE = {"WWW-Authenticate": "Bearer"}


def check_key(authorization: str | None, keys: Mapping[str, str]) -> str:
    """Return the ID of the key in an `Authorization: Bearer <key>` header.

    `keys` maps each key ID to its key, such as {"key_01": "bn_..."}.
    Raises a 401 ApiError if no key was sent or it matches none. The key
    sent is never put in the error.
    """
    # `authorization` is the raw text of the `Authorization` header,
    # exactly as the client sent it. It may be None if the header was missing.
    # Example header:
    # "Authorization: Bearer bn_1234567890abcdef". The route reads the header's
    # value, the part after `Authorization: ` (`Bearer bn_1234567890abcdef`),
    # and passes it to this function.
    scheme, _, sent = (authorization or "").partition(" ")
    sent = sent.strip()
    if scheme.lower() != "bearer" or not sent:
        raise ApiError(
            401,
            "authentication",
            "api_key_missing",
            "Send an API key as `Authorization: Bearer <key>`.",
            headers=_CHALLENGE,
        )

    # compare_digest takes the same time wherever the first difference
    # is, so response times don't reveal how much of a key was right.
    # Bytes, because it rejects str with non-ASCII characters. Every key
    # is compared, without stopping at a match.
    found = None
    for key_id, key in keys.items():
        if hmac.compare_digest(sent.encode(), key.encode()):
            found = key_id
    if found is None:
        raise ApiError(
            401,
            "authentication",
            "api_key_invalid",
            "The API key is invalid.",
            headers=_CHALLENGE,
        )
    return found

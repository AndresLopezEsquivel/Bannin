"""The Bannin scoring API."""

import json
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import NoReturn

from fastapi import FastAPI, Request

from bannin.auth import check_key
from bannin.errors import ApiError, add_error_handlers
from bannin.keys import load_keys
from bannin.scorer import MODEL_VERSION, StubScorer
from bannin.scoring import score_payment
from bannin.thresholds import load_thresholds_from_env
from bannin.validation import check_request

# Uvicorn's own logger, so these lines show in the container's log next
# to Uvicorn's (structured logging comes later).
log = logging.getLogger("uvicorn.error")

# The largest body /score reads, in bytes (64 KiB). Caddy's cap in
# infra/app/Caddyfile is a backstop above it, not a replacement.
MAX_BODY = 64 * 1024


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Runs once at startup, before the first request. If the keys or
    the thresholds can't be loaded, the error stops the app from starting."""
    app.state.keys = load_keys(os.environ)
    log.info("Loaded API keys: %s", ", ".join(sorted(app.state.keys)))
    # Read once: a threshold change takes a restart, so each running app
    # decides with exactly one version of the thresholds.
    t = app.state.thresholds = load_thresholds_from_env(os.environ)
    app.state.scorer = StubScorer()
    log.info(
        "Loaded thresholds %s (review %s, decline %s); scorer %s",
        t.version,
        t.review,
        t.decline,
        MODEL_VERSION,
    )
    yield


# api/openapi.yaml is the published spec, so FastAPI's generated docs
# pages and its generated spec (/openapi.json) are not served.
app = FastAPI(
    title="Bannin Scoring API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    lifespan=lifespan,
)
add_error_handlers(app)
# The valid API keys, by key ID. Empty, so every key is rejected, until
# the lifespan above loads them at startup.
app.state.keys = {}


async def _read_body(request: Request) -> bytes:
    """Returns the body, or raises a 413 as soon as it's over MAX_BODY
    bytes, so a large body is never held in memory."""
    too_large = ApiError(
        413,
        "invalid_request",
        "body_too_large",
        f"The body must be at most {MAX_BODY} bytes.",
    )
    # A declared length over the limit is rejected without reading. The
    # server has already rejected a malformed one; isascii() keeps out
    # digits like "²", which isdigit() accepts but int() doesn't.
    declared = request.headers.get("content-length", "")
    if declared.isascii() and declared.isdigit() and int(declared) > MAX_BODY:
        raise too_large
    # The declared length isn't trusted, and a chunked body has none, so
    # the bytes are counted as they arrive.
    chunks, size = [], 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BODY:
            raise too_large
        chunks.append(chunk)
    return b"".join(chunks)


# For operators, not merchants: no key, and not in the API's schema.
@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    """Report that the app is running. The Postgres check comes later."""
    return {"status": "ok"}


# response_model=None: FastAPI builds no response schema from the return
# type, since the route always raises for now (NoReturn).
@app.post("/score", response_model=None)
async def score(request: Request) -> NoReturn:
    """Check the key, then the body's size, then that the body is a
    JSON object, then the required fields, then score the payment. The
    decision isn't sent yet: it's logged before it's sent, and the log
    isn't built, so a scored request gets a 503."""
    # Kept on the request, so the decision log can record which key was used.
    request.state.key_id = check_key(
        request.headers.get("authorization"), request.app.state.keys
    )

    # The body is parsed here rather than by FastAPI, so the key is always
    # checked first and bad JSON gets our 400 instead of FastAPI's 422.
    # ValueError covers broken JSON and bytes that aren't text;
    # RecursionError covers JSON nested too deeply to parse.
    try:
        body = json.loads(await _read_body(request))
    except ValueError, RecursionError:
        body = None
    if not isinstance(body, dict):
        raise ApiError(
            400, "invalid_request", "body_invalid", "The body must be a JSON object."
        )

    # Raises a 400 for the first required field that's missing or invalid.
    # Invalid or unrecognized optional fields are only listed as ignored.
    request.state.fields, request.state.ignored = check_request(body)

    # Kept on the request for the decision log's row, written before the
    # response is sent.
    request.state.scored = score_payment(
        request.state.fields,
        request.state.ignored,
        request.app.state.scorer,
        request.app.state.thresholds,
    )

    raise ApiError(
        503,
        "server_error",
        "service_unavailable",
        "Bannin can't score payments right now. Retry later.",
    )

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
from bannin.validation import check_required

# Uvicorn's own logger, so these lines show in the container's log next
# to Uvicorn's (structured logging comes later).
log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Runs once at startup, before the first request. If the keys can't
    be loaded, the error stops the app from starting."""
    app.state.keys = load_keys(os.environ)
    log.info("Loaded API keys: %s", ", ".join(sorted(app.state.keys)))
    yield


# api/openapi.yaml is the published spec, so FastAPI's generated docs
# pages and spec are not served.
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


# For operators, not merchants: no key, and not in the API's schema.
@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    """Report that the app is running. The Postgres check comes later."""
    return {"status": "ok"}


# response_model=None: FastAPI builds no response schema from the return
# type, since the route always raises for now (NoReturn).
@app.post("/score", response_model=None)
async def score(request: Request) -> NoReturn:
    """Check the key, then that the body is a JSON object, then the
    required fields. Scoring isn't built yet, so a request that passes
    all three gets a 503."""
    # Kept on the request, so the decision log can record which key was used.
    request.state.key_id = check_key(
        request.headers.get("authorization"), request.app.state.keys
    )

    # The body is parsed here rather than by FastAPI, so the key is always
    # checked first and bad JSON gets our 400 instead of FastAPI's 422.
    # ValueError covers broken JSON and bytes that aren't text;
    # RecursionError covers JSON nested too deeply to parse.
    try:
        body = json.loads(await request.body())
    except ValueError, RecursionError:
        body = None
    if not isinstance(body, dict):
        raise ApiError(
            400, "invalid_request", "body_invalid", "The body must be a JSON object."
        )

    # Raises a 400 for the first required field that's missing or invalid.
    request.state.fields = check_required(body)

    raise ApiError(
        503,
        "server_error",
        "service_unavailable",
        "Bannin can't score payments right now. Retry later.",
    )

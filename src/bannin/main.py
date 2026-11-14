"""The Bannin scoring API."""

import json
from typing import NoReturn

from fastapi import FastAPI, Request

from bannin.auth import check_key
from bannin.errors import ApiError, add_error_handlers

# api/openapi.yaml is the published spec, so FastAPI's generated docs
# pages and spec are not served.
app = FastAPI(
    title="Bannin Scoring API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)
add_error_handlers(app)
# The valid API keys, by key ID. None are loaded yet, so every key is
# rejected; loading them at startup comes later.
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
    """Check the key, then that the body is a JSON object. Scoring isn't
    built yet, so a request that passes both gets a 503."""
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

    raise ApiError(
        503,
        "server_error",
        "service_unavailable",
        "Bannin can't score payments right now. Retry later.",
    )

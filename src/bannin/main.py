"""The Bannin scoring API."""

from fastapi import FastAPI

# api/openapi.yaml is the published spec, so FastAPI's generated docs
# pages and spec are not served.
app = FastAPI(
    title="Bannin Scoring API",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


# For operators, not merchants: no key, and not in the API's schema.
@app.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    """Report that the app is running. The Postgres check comes later."""
    return {"status": "ok"}

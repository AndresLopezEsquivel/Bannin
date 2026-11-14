"""Error responses. Every error is one JSON object, as in api/openapi.yaml:
{"error": {"type": ..., "code": ..., "message": ..., "field": ...}}."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Raised anywhere in a request; the handler below turns it into the
    response. `field` is left out of the response when it's None."""

    def __init__(
        self,
        status: int,
        error_type: str,
        code: str,
        message: str,
        field: str | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.error_type = error_type
        self.code = code
        self.message = message
        self.field = field
        self.headers = headers


async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
    error = {"type": exc.error_type, "code": exc.code, "message": exc.message}
    if exc.field is not None:
        error["field"] = exc.field
    return JSONResponse({"error": error}, status_code=exc.status, headers=exc.headers)


# Any other exception is a bug. The response says nothing about it, so no
# internal detail (or request value) reaches the caller; the server still
# logs the traceback.
async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
    return await _api_error(
        request,
        ApiError(
            500,
            "server_error",
            "internal_error",
            "Something went wrong in Bannin. "
            "Retrying with the same payment_id is safe.",
        ),
    )


def add_error_handlers(app: FastAPI) -> None:
    # `add_exception_handler` registers a function that turns one kind
    # of exception into an HTTP response. For example, during a request,
    # if an ApiError is raised, FastAPI calls _api_error().
    # If FastAPI doesn't recognize the exception class, it ends
    # at Exception, which is handled by _unexpected().
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(Exception, _unexpected)

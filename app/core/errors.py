"""Centralized exception handlers.

All error responses flow through this module. Handlers **must never** leak:

- Python stack traces
- API keys, tokens, or other secrets
- Internal file paths or environment variable values
- The original exception object

The HTTP status codes follow the specification exactly:

- 400 — malformed JSON or otherwise unparseable request
- 422 — request parses but violates a Pydantic constraint
- 500 — unexpected server error
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.error import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def _envelope(code: str, message: str, details: list[ErrorDetail] | None = None) -> dict[str, Any]:
    """Build the standard ``{"error": {...}}`` response body."""

    return ErrorResponse(code=code, message=message, details=details or []).model_dump()


def _safe_validation_messages(exc: RequestValidationError) -> list[ErrorDetail]:
    """Extract only field paths and short messages from a Pydantic error.

    Pydantic's ``errors()`` is trusted to never contain secrets, but we keep
    only the first 5 entries and a short message to avoid leaking verbose
    internals to clients.
    """

    out: list[ErrorDetail] = []
    for err in exc.errors()[:5]:
        loc = [str(part) for part in err.get("loc", [])]
        out.append(
            ErrorDetail(
                field=".".join(loc) if loc else None,
                message=str(err.get("msg", "invalid value")),
            )
        )
    return out


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all custom handlers to ``app``.

    Called from the application factory in :mod:`app.main`.
    """

    @app.exception_handler(RequestValidationError)
    async def _on_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # Schema parses as JSON but is semantically invalid → 422.
        logger.info("validation_error", extra={"detail_count": len(exc.errors())})
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope(
                code="validation_error",
                message="The request body is invalid.",
                details=_safe_validation_messages(exc),
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _on_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Pass-through for explicit HTTPException raises from routes.
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code=f"http_{exc.status_code}", message=message),
        )

    @app.exception_handler(Exception)
    async def _on_unhandled(_: Request, exc: Exception) -> JSONResponse:
        # Last-resort handler. Log full context server-side, return generic body.
        logger.exception("unhandled_exception", extra={"exc_type": type(exc).__name__})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope(
                code="internal_server_error",
                message="An unexpected error occurred. Please try again later.",
            ),
        )

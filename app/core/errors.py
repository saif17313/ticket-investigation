"""Centralized non-sensitive error handlers."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def register_exception_handlers(app: FastAPI) -> None:
    """Attach API error handlers while preserving the public error contract."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        malformed = any(error.get("type") == "json_invalid" for error in errors)
        missing_required = any(error.get("type") == "missing" for error in errors)
        if malformed or missing_required:
            return JSONResponse(
                status_code=400,
                content={"detail": "Malformed request body."},
            )
        return JSONResponse(
            status_code=422,
            content={"detail": "Request validation failed."},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_: Request, __: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error."},
        )

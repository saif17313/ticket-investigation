"""FastAPI application entrypoint for QueueStorm Investigator."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes import router

app = FastAPI(
    title="QueueStorm Investigator",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Return controlled, non-sensitive errors for malformed and invalid input."""
    errors = exc.errors()
    malformed = any(error.get("type") == "json_invalid" for error in errors)
    missing_required = any(error.get("type") == "missing" for error in errors)
    if malformed or missing_required:
        return JSONResponse(status_code=400, content={"detail": "Malformed request body."})
    return JSONResponse(status_code=422, content={"detail": "Request validation failed."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, __: Exception) -> JSONResponse:
    """Avoid returning stack traces or internal details to callers."""
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


app.include_router(router)

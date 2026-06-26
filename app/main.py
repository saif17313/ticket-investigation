"""FastAPI application entrypoint.

The application object is constructed here and the API routers are mounted
in their dedicated modules. Cross-cutting concerns (logging, lifespan,
exception handlers) are wired in :mod:`app.core`.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Process-level startup and shutdown hooks."""

    settings = get_settings()
    configure_logging(level=settings.log_level)
    yield


def create_app() -> FastAPI:
    """Application factory.

    Returning a factory (instead of a module-level ``app``) makes the
    application trivially testable: each test instantiates its own copy
    with overridden dependencies.
    """

    app = FastAPI(
        title="QueueStorm Investigator",
        version="0.1.0",
        description="Internal AI copilot for fintech support agents.",
        lifespan=lifespan,
    )

    # Routers are mounted in later steps (Step 7+). Importing here would
    # create circular dependencies, so we keep the wiring explicit.
    from app.api.router import api_router  # local import to avoid cycles

    app.include_router(api_router)
    return app


app = create_app()

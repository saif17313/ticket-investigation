"""FastAPI application entrypoint for QueueStorm Investigator."""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging


@asynccontextmanager
async def lifespan(app_: FastAPI) -> AsyncIterator[None]:
    """Configure process-level concerns without touching public routes."""

    _ = app_
    configure_logging(get_settings().log_level)
    yield


def create_app() -> FastAPI:
    """Create the API app with docs disabled per the challenge contract."""

    app = FastAPI(
        title="QueueStorm Investigator",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "null"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
        allow_credentials=False,
        max_age=600,
    )
    register_exception_handlers(app)
    app.include_router(router)
    return app


app = create_app()

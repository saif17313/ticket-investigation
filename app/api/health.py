"""``GET /health`` endpoint.

Returns the exact response shape required by the specification:

    {"status": "ok"}

No additional fields, no headers, no side effects.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Locked response model for ``GET /health``."""

    model_config = ConfigDict(extra="forbid")

    status: str


@router.get("/health", response_model=HealthResponse, summary="Liveness probe")
async def health() -> HealthResponse:
    """Return the service health indicator."""

    return HealthResponse(status="ok")

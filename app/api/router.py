"""Top-level API router.

Each endpoint lives in its own module under :mod:`app.api` and is registered
here. Keeping the registry centralized makes the full HTTP surface easy to
audit at a glance.
"""

from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter()

# Routers are registered here in later steps. Health is mounted in Step 7.
from app.api.health import router as health_router  # noqa: E402

api_router.include_router(health_router)

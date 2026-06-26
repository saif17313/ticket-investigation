"""``POST /analyze-ticket`` route.

The handler is intentionally thin: it parses the request via Pydantic and
delegates the actual investigation to :class:`InvestigatorService`. All
error handling and response shaping lives in the orchestrator and the
centralized exception handlers.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import provide_investigator
from app.schemas import AnalyzeRequest, AnalyzeResponse
from app.services.investigator import InvestigatorService

router = APIRouter(tags=["investigation"])

_InvestigatorDep = Annotated[InvestigatorService, Depends(provide_investigator)]


@router.post(
    "/analyze-ticket",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_200_OK,
    summary="Investigate a customer support ticket",
)
async def analyze_ticket(
    request: AnalyzeRequest,
    investigator: _InvestigatorDep,
) -> AnalyzeResponse:
    """Run a full investigation and return the structured result."""

    return await investigator.analyze(request)
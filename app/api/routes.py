"""Required QueueStorm HTTP endpoints."""

from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends

from app.api.deps import provide_investigator
from app.schemas.models import AnalyzeTicketRequest, AnalyzeTicketResponse
from app.services.investigator import InvestigatorService

router = APIRouter()
InvestigatorDep = Annotated[InvestigatorService, Depends(provide_investigator)]


@router.get("/health")
def health() -> dict[str, str]:
    """Readiness endpoint required by the judge harness."""
    return {"status": "ok"}


@router.post("/analyze-ticket", response_model=AnalyzeTicketResponse)
async def analyze_ticket_route(
    request: AnalyzeTicketRequest,
    investigator: InvestigatorDep,
) -> AnalyzeTicketResponse:
    """Analyze one support complaint and its optional transaction evidence."""
    return await investigator.analyze(request)

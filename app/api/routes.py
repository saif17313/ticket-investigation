"""Required QueueStorm HTTP endpoints."""

from fastapi import APIRouter

from app.core.analyzer import analyze_ticket
from app.schemas.models import AnalyzeTicketRequest, AnalyzeTicketResponse

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    """Readiness endpoint required by the judge harness."""
    return {"status": "ok"}


@router.post("/analyze-ticket", response_model=AnalyzeTicketResponse)
def analyze_ticket_route(request: AnalyzeTicketRequest) -> AnalyzeTicketResponse:
    """Analyze one support complaint and its optional transaction evidence."""
    return analyze_ticket(request)

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.rate_limiter import check_roadmap_rate_limit
from app.schemas.roadmap import RoadmapRequest, RoadmapResponse
from app.services import roadmap as roadmap_service

router = APIRouter()


@router.post(
    "/roadmap",
    response_model=RoadmapResponse,
    dependencies=[Depends(check_roadmap_rate_limit)],
)
async def create_roadmap(payload: RoadmapRequest) -> RoadmapResponse:
    try:
        steps = await roadmap_service.get_or_generate_roadmap(payload.subject)
    except roadmap_service.RoadmapGenerationError as exc:
        print("ERROR : " , exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc) or "The AI service is currently unavailable.",
        ) from exc
    except roadmap_service.RoadmapParsingError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc) or "The AI service returned an unparsable roadmap.",
        ) from exc

    return RoadmapResponse(roadmap=steps)
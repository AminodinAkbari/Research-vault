from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class RoadmapRequest(BaseModel):
    """Payload for POST /api/v1/roadmap."""

    subject: str = Field(..., min_length=1, max_length=200)

    @field_validator("subject")
    @classmethod
    def _strip_subject(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("subject must not be blank")
        return stripped


class RoadmapStep(BaseModel):
    """One step of a generated research roadmap."""

    step: str
    keywords: list[str] = Field(default_factory=list)


class RoadmapResponse(BaseModel):
    """Response body for POST /api/v1/roadmap."""

    roadmap: list[RoadmapStep]
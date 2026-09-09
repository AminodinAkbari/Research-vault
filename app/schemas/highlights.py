from __future__ import annotations

import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

class ExplainRequest(BaseModel):
    selected_text: str
    start_offset: int
    end_offset: int

class HighlightRead(BaseModel):
    id: uuid.UUID
    link_id: uuid.UUID
    selected_text: str
    annotation: str | None
    start_offset: int
    end_offset: int
    color: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HighlightCreate(BaseModel):
    selected_text: str
    annotation: str | None = None
    start_offset: int = 0
    end_offset: int = 0
    color: str | None = None
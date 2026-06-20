from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user
from app.models.user import User

router = APIRouter()


@router.get("")
async def list_projects(current_user: User = Depends(get_current_user)) -> dict[str, uuid.UUID]:
    """Minimal protected endpoint proving JWT auth + user isolation works.

    Returns the authenticated user's ID. Replace with real project listing
    (scoped to current_user.id) in a future milestone.
    """
    return {"user_id": current_user.id}
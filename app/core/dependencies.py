from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.services import project as project_service
from app.services.auth import get_user_by_id

# tokenUrl is used for OpenAPI/Swagger UI metadata only; the login endpoint
# itself accepts a JSON body rather than an OAuth2 form.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise _credentials_exception

    subject = payload.get("sub")
    if subject is None:
        raise _credentials_exception

    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        raise _credentials_exception

    user = await get_user_by_id(db, user_id)
    if user is None:
        raise _credentials_exception

    return user


async def get_current_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Path-param dependency: resolves `project_id` from the URL and verifies
    it exists and belongs to the current user.

    Use this on any route nested under /projects/{project_id}/... to get the
    ownership check for free. Raises 404 if the project doesn't exist, 403 if
    it belongs to someone else.
    """
    try:
        return await project_service.get_owned_project(
            db, project_id=project_id, user_id=current_user.id
        )
    except project_service.ProjectNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        ) from exc
    except project_service.ProjectForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project",
        ) from exc
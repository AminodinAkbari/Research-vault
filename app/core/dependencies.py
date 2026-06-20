from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
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
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.auth import AuthLogin, AuthRegister, RegisterResponse, TokenResponse
from app.services.auth import (
    AuthError,
    authenticate_user,
    issue_token_for_user,
    register_user,
)

router = APIRouter()


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    payload: AuthRegister,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    """Register a new user and return an access token.

    Raises 409 CONFLICT if the email address is already registered.
    """
    try:
        user = await register_user(db, email=payload.email, password=payload.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    token = issue_token_for_user(user)
    return RegisterResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
        access_token=token,
        token_type="bearer",
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: AuthLogin,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate a user and issue a JWT access token.

    Raises 401 UNAUTHORIZED for invalid credentials.
    """
    try:
        user = await authenticate_user(db, email=payload.email, password=payload.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    token = issue_token_for_user(user)
    return TokenResponse(access_token=token)

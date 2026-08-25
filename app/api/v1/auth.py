from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import COOKIE_NAME
from app.core.rate_limiter import auth_rate_limit
from app.db.session import get_db
from app.schemas.auth import AuthLogin, AuthRegister, RegisterResponse, TokenResponse
from app.services.auth import (
    AuthError,
    authenticate_user,
    issue_token_for_user,
    register_user,
)

router = APIRouter()


def _set_auth_cookie(response: Response, token: str) -> None:
    """Set the JWT as an httpOnly cookie so the server-rendered UI (app/api/ui.py)
    stays authenticated across full-page navigations, in addition to the token
    being returned in the JSON body for API/programmatic clients.
    """
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # TODO: flip to True once the app is served over HTTPS
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        path="/",
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limit)],
)
async def register(
    payload: AuthRegister,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> RegisterResponse:
    try:
        user = await register_user(db, email=payload.email, password=payload.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    token = issue_token_for_user(user)
    _set_auth_cookie(response, token)
    return RegisterResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
        access_token=token,
        token_type="bearer",
    )


@router.post("/login", response_model=TokenResponse, dependencies=[Depends(auth_rate_limit)])
async def login(
    payload: AuthLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        user = await authenticate_user(db, email=payload.email, password=payload.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    token = issue_token_for_user(user)
    _set_auth_cookie(response, token)
    return TokenResponse(access_token=token)
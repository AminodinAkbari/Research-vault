from __future__ import annotations

from pydantic import BaseModel, EmailStr

from app.schemas.user import TokenResponse, UserRead

__all__ = ["AuthRegister", "AuthLogin", "TokenResponse", "RegisterResponse"]


class AuthRegister(BaseModel):
    email: EmailStr
    password: str


class AuthLogin(BaseModel):
    email: EmailStr
    password: str


class RegisterResponse(UserRead):
    """User data returned alongside an access token on successful registration."""

    access_token: str
    token_type: str = "bearer"
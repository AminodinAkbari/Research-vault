from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User


class AuthError(Exception):
    """Raised for registration/authentication failures (bad credentials, duplicate email, ...)."""


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def register_user(db: AsyncSession, *, email: str, password: str) -> User:
    """Create a new user. Raises AuthError if the email is already taken."""
    existing = await get_user_by_email(db, email)
    if existing is not None:
        raise AuthError("A user with this email already exists.")

    user = User(email=email, hashed_password=hash_password(password))
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, *, email: str, password: str) -> User:
    """Validate credentials and return the matching user. Raises AuthError otherwise."""
    user = await get_user_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthError("Invalid email or password.")
    return user


def issue_token_for_user(user: User) -> str:
    """Mint a signed JWT access token for an authenticated user."""
    return create_access_token(subject=user.id)
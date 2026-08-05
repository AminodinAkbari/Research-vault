from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Request, status
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
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# Name of the httpOnly cookie set by /api/v1/auth/login and /api/v1/auth/register,
# used by the server-rendered UI (app/api/ui.py, app/api/ui_project.py) to
# authenticate page loads.
COOKIE_NAME = "access_token"

_credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def _resolve_user_from_token(token: str | None, db: AsyncSession) -> User | None:
    """Decode a JWT and look up the corresponding user. Returns None on any failure.

    Shared by both the header-based (API) and cookie-based (UI) auth
    dependencies so the actual token → user resolution logic lives in
    exactly one place.
    """
    if not token:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None

    subject = payload.get("sub")
    if subject is None:
        return None

    try:
        user_id = uuid.UUID(subject)
    except ValueError:
        return None

    return await get_user_by_id(db, user_id)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """API auth dependency: requires a valid `Authorization: Bearer <token>` header."""
    user = await _resolve_user_from_token(token, db)
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


# ---------------------------------------------------------------------------
# Cookie-based auth — used by the server-rendered HTML UI
# (app/api/ui.py, app/api/ui_project.py). The JWT is identical in shape to
# the header-based token; it's just carried in an httpOnly cookie instead of
# an Authorization header so plain page navigations and <form>/HTMX requests
# stay authenticated without any manual header wiring.
# ---------------------------------------------------------------------------

async def get_current_user_from_cookie(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """UI auth dependency: requires a valid `access_token` cookie.

    Redirects to /login (via a 303 response) instead of returning a JSON 401,
    since this guards HTML pages rendered for a browser rather than API calls.
    """
    token = request.cookies.get(COOKIE_NAME)
    user = await _resolve_user_from_token(token, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return user


async def get_optional_current_user_from_cookie(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Like `get_current_user_from_cookie`, but returns None instead of
    redirecting. Used on public pages (login/register/root) that want to know
    whether someone is already signed in without forcing a redirect loop.
    """
    token = request.cookies.get(COOKIE_NAME)
    return await _resolve_user_from_token(token, db)


async def get_current_project_from_cookie(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user_from_cookie),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """UI counterpart to `get_current_project`: resolves `project_id` from the
    URL using cookie-based auth and verifies ownership. Delegates to the same
    `project_service` used by the JSON API — no ownership logic duplicated.

    Raises 404 if the project doesn't exist, 403 if it belongs to someone else.
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
        
# ---------------------------------------------------------------------------
# Combined dependencies using `optional` oauth2 schema which can seen in "oauth2_scheme_optional" variable.
# In these type of schemas, If authorization header not exists, API use access_token for verify users instead.
# In this method, user still should be logged in"
# ---------------------------------------------------------------------------


async def get_current_user_combined(
    request: Request,
    token: str = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Combined auth: tries header-based auth first, falls back to cookie-based auth.

    Used for API endpoints accessed via both API clients (Authorization header)
    and browser navigation (access_token cookie), like file downloads.
    """
    user = await _resolve_user_from_token(token, db)
    if user is not None:
        return user

    cookie_token = request.cookies.get(COOKIE_NAME)
    user = await _resolve_user_from_token(cookie_token, db)
    if user is not None:
        return user

    raise _credentials_exception


async def get_current_project_combined(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user_combined),
    db: AsyncSession = Depends(get_db),
) -> Project:
    """Combined auth version of get_current_project: accepts both Authorization header and access_token cookie.

    Use this on API endpoints that may be accessed via plain browser navigation
    (e.g., file downloads via <a href>).
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
        
async def get_optional_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """API auth dependency variant that does not require authentication.

    Returns the current user if a valid `Authorization: Bearer <token>`
    header is present, otherwise None instead of raising. Used by endpoints
    that support both authenticated and anonymous callers — e.g.
    POST /api/v1/roadmap, which rate-limits per user when authenticated and
    falls back to per-IP limiting otherwise.
    """
    auth_header = request.headers.get("Authorization", "")
    token: str | None = None
    if auth_header.lower().startswith("bearer "):
        token = auth_header[len("bearer "):].strip()
    return await _resolve_user_from_token(token, db)
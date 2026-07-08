from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_current_user_from_cookie,
    get_optional_current_user_from_cookie,
)
from app.core.templates import templates
from app.db.session import get_db
from app.models.user import User
from app.services import project as project_service

# include_in_schema=False on the router keeps these HTML pages out of the
# OpenAPI/Swagger docs, which describe the JSON API only.
router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
async def root(
    current_user: User | None = Depends(get_optional_current_user_from_cookie),
) -> RedirectResponse:
    destination = "/dashboard" if current_user else "/login"
    return RedirectResponse(url=destination, status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    current_user: User | None = Depends(get_optional_current_user_from_cookie),
):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "login.html", name="login.html", context={"request": request, "current_user": None}
    )


@router.get("/register", response_class=HTMLResponse)
async def register_page(
    request: Request,
    current_user: User | None = Depends(get_optional_current_user_from_cookie),
):
    if current_user:
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        "register.html", name="register.html",context={"request": request, "current_user": None}
    )


@router.post("/logout")
async def logout() -> RedirectResponse:
    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("access_token", path="/")
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(
    request: Request,
    current_user: User = Depends(get_current_user_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    projects = await project_service.list_projects(db, user_id=current_user.id)
    return templates.TemplateResponse(
        "dashboard.html",
        name="dashboard.html",
        context={"request": request, "current_user": current_user, "projects": projects},
    )


@router.post("/dashboard/projects", response_class=HTMLResponse)
async def create_project_ui(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    current_user: User = Depends(get_current_user_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    """Create a project via the existing project service (no logic duplicated
    from the JSON API) and return the refreshed project list fragment for
    HTMX to swap into the page. Falls back to a full-page redirect for
    non-HTMX (e.g. JS-disabled) form submissions.
    """
    await project_service.create_project(
        db,
        user_id=current_user.id,
        name=name.strip(),
        description=description.strip() or None,
    )
    projects = await project_service.list_projects(db, user_id=current_user.id)

    if request.headers.get("HX-Request"):
        return templates.TemplateResponse(
            "partials/project_list.html", name="partials/project_list.html", context={"request": request, "projects": projects}
        )
    return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
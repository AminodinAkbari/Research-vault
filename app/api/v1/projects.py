from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_project, get_current_project_combined, get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import project as project_service

from fastapi.responses import Response
from app.db.session import get_db
from app.services import export

router = APIRouter()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    """Create a new project owned by the current user."""
    return await project_service.create_project(
        db,
        user_id=current_user.id,
        name=payload.name,
        description=payload.description,
    )


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectRead]:
    """List all projects owned by the current user."""
    return await project_service.list_projects(db, user_id=current_user.id)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project: Project = Depends(get_current_project)) -> ProjectRead:
    """Get the project identified by the path parameter."""
    return project


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    payload: ProjectUpdate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    """Apply a partial update to the current project."""
    return await project_service.apply_project_update(
        db, project=project, update_data=payload.model_dump(exclude_unset=True)
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete the current project and all of its notes, links, and tags."""
    await project_service.delete_project(db, project=project)


def _slugify(name: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", name).strip().lower()
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug or "project"


@router.get("/{project_id}/export/markdown")
async def export_project_markdown(
    project: Project = Depends(get_current_project_combined),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """
    Export a project's notes, saved links, and highlights as a single
    downloadable Markdown file.

    Auth/ownership is identical to every other `/projects/{project_id}/...`
    endpoint: `get_current_project` accepts either the `Authorization:
    Bearer` header or the `access_token` cookie, resolves the project, and
    404s / 403s exactly like the rest of the API — nothing new to test there.
    Because the cookie is accepted here too, the UI can link straight to
    this endpoint with a plain `<a href>` (see templates/project_detail.html)
    without a separate UI-only export route.

    All the actual data-gathering and Markdown assembly lives in
    `export.build_project_markdown` — this route is just the usual
    thin adapter (call service, translate to an HTTP response).
    """
    markdown = await export.build_project_markdown(session, project=project)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = f"{_slugify(project.name)}-{stamp}.md"

    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

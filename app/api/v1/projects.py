from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_project, get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services import project as project_service

router = APIRouter()


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
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
    return await project_service.list_projects(db, user_id=current_user.id)


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project: Project = Depends(get_current_project)) -> ProjectRead:
    return project


@router.put("/{project_id}", response_model=ProjectRead)
async def update_project(
    payload: ProjectUpdate,
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> ProjectRead:
    return await project_service.apply_project_update(
        db, project=project, update_data=payload.model_dump(exclude_unset=True)
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project: Project = Depends(get_current_project),
    db: AsyncSession = Depends(get_db),
) -> None:
    await project_service.delete_project(db, project=project)
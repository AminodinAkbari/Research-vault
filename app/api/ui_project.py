from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_project_from_cookie, get_current_user_from_cookie
from app.core.templates import templates
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.services import link as link_service
from app.services import note as note_service
from app.services import tag as tag_service

# include_in_schema=False keeps these HTML fragment/page routes out of the
# OpenAPI/Swagger docs, which describe the JSON API only.
router = APIRouter(include_in_schema=False)


# ---------------------------------------------------------------------------
# Project detail page
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail_page(
    request: Request,
    project: Project = Depends(get_current_project_from_cookie),
    current_user: User = Depends(get_current_user_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    # get_current_project_from_cookie already depends on
    # get_current_user_from_cookie internally, so FastAPI resolves that
    # dependency once per request and reuses it here (no duplicate DB hit).
    links = await link_service.list_links(db, project_id=project.id)
    return templates.TemplateResponse(
        "project_detail.html", name="project_detail.html",
        context={
            "request": request,
            "current_user": current_user,
            "project": project,
            "links": links,
        },
    )


# ---------------------------------------------------------------------------
# Notes
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/notes/list", response_class=HTMLResponse)
async def list_notes_ui(
    request: Request,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    notes = await note_service.list_notes(db, project_id=project.id)
    return templates.TemplateResponse(
        "notes/_list.html", name="notes/_list.html", context={"request": request, "project": project, "notes": notes}
    )


@router.post("/projects/{project_id}/notes", response_class=HTMLResponse)
async def create_note_ui(
    request: Request,
    title: str = Form(...),
    content: str = Form(""),
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    await note_service.create_note(
        db, project_id=project.id, title=title.strip(), content=content
    )
    notes = await note_service.list_notes(db, project_id=project.id)
    return templates.TemplateResponse(
        "notes/_list.html", name="notes/_list.html", context={"request": request, "project": project, "notes": notes}
    )


@router.get("/projects/{project_id}/notes/{note_id}/edit", response_class=HTMLResponse)
async def edit_note_form_ui(
    request: Request,
    note_id: uuid.UUID,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    try:
        note = await note_service.get_note(db, project_id=project.id, note_id=note_id)
    except note_service.NoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Note not found") from exc

    return templates.TemplateResponse(
        "notes/_edit_form.html", name="notes/_edit_form.html", context={"request": request, "project": project, "note": note}
    )


@router.put("/projects/{project_id}/notes/{note_id}", response_class=HTMLResponse)
async def update_note_ui(
    request: Request,
    note_id: uuid.UUID,
    title: str = Form(...),
    content: str = Form(""),
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    try:
        note = await note_service.update_note(
            db,
            project_id=project.id,
            note_id=note_id,
            update_data={"title": title.strip(), "content": content},
        )
    except note_service.NoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Note not found") from exc

    return templates.TemplateResponse(
        "notes/_note_item.html", name="notes/_note_item.html", context={"request": request, "project": project, "note": note}
    )


@router.delete("/projects/{project_id}/notes/{note_id}")
async def delete_note_ui(
    note_id: uuid.UUID,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await note_service.delete_note(db, project_id=project.id, note_id=note_id)
    except note_service.NoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Note not found") from exc

    # 200 with an empty body: HTMX swaps the (now-empty) response into the
    # note's own element (hx-target="closest .note-item", hx-swap="outerHTML"
    # on the client), which removes it from the DOM.
    return Response(status_code=status.HTTP_200_OK, content="")


# ---------------------------------------------------------------------------
# Note ↔ tag associations
# ---------------------------------------------------------------------------


@router.get(
    "/projects/{project_id}/notes/{note_id}/tags/available", response_class=HTMLResponse
)
async def available_tags_for_note_ui(
    request: Request,
    note_id: uuid.UUID,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    try:
        note = await note_service.get_note(db, project_id=project.id, note_id=note_id)
    except note_service.NoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Note not found") from exc

    all_tags = await tag_service.list_tags(db, project_id=project.id)
    attached_ids = {tag.id for tag in note.tags}
    available_tags = [tag for tag in all_tags if tag.id not in attached_ids]

    return templates.TemplateResponse(
        "notes/_tag_picker.html", name="notes/_tag_picker.html",
        context={
            "request": request,
            "project": project,
            "note": note,
            "available_tags": available_tags,
        },
    )


@router.post("/projects/{project_id}/notes/{note_id}/tags", response_class=HTMLResponse)
async def attach_tag_to_note_ui(
    request: Request,
    note_id: uuid.UUID,
    tag_id: uuid.UUID = Form(...),
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    try:
        note = await note_service.attach_tags(
            db, project_id=project.id, note_id=note_id, tag_ids=[tag_id]
        )
    except note_service.NoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Note not found") from exc

    return templates.TemplateResponse(
        "notes/_note_item.html", name="notes/_note_item.html", context={"request": request, "project": project, "note": note}
    )


@router.delete(
    "/projects/{project_id}/notes/{note_id}/tags/{tag_id}", response_class=HTMLResponse
)
async def detach_tag_from_note_ui(
    request: Request,
    note_id: uuid.UUID,
    tag_id: uuid.UUID,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    try:
        note = await note_service.detach_tag(
            db, project_id=project.id, note_id=note_id, tag_id=tag_id
        )
    except note_service.NoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Note not found") from exc

    return templates.TemplateResponse(
        "notes/_note_item.html", name="notes/_note_item.html", context={"request": request, "project": project, "note": note}
    )


# ---------------------------------------------------------------------------
# Project tags
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/tags/list", response_class=HTMLResponse)
async def list_tags_ui(
    request: Request,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    tags = await tag_service.list_tags(db, project_id=project.id)
    return templates.TemplateResponse(
        "tags/_list.html", name="tags/_list.html",
        context={"request": request, "project": project, "tags": tags, "error": None},
    )


@router.post("/projects/{project_id}/tags", response_class=HTMLResponse)
async def create_tag_ui(
    request: Request,
    name: str = Form(...),
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    error: str | None = None
    clean_name = name.strip()
    try:
        await tag_service.create_tag(db, project_id=project.id, name=clean_name)
    except tag_service.TagAlreadyExistsError:
        error = f'A tag named "{clean_name}" already exists in this project.'

    tags = await tag_service.list_tags(db, project_id=project.id)
    return templates.TemplateResponse(
        "tags/_list.html", name="tags/_list.html",
        context={"request": request, "project": project, "tags": tags, "error": error},
    )


@router.delete("/projects/{project_id}/tags/{tag_id}")
async def delete_tag_ui(
    tag_id: uuid.UUID,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await tag_service.delete_tag(db, project_id=project.id, tag_id=tag_id)
    except tag_service.TagNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Tag not found") from exc

    return Response(status_code=status.HTTP_200_OK, content="")
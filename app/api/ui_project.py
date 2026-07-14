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
from app.services import collected_search as collected_search_service
from app.services import highlight as highlight_service
from app.services import link as link_service
from app.services import note as note_service
from app.services import tag as tag_service
from app.services.searxng import search_searxng

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
    source_link_id: uuid.UUID | None = None,
):
    # get_current_project_from_cookie already depends on
    # get_current_user_from_cookie internally, so FastAPI resolves that
    # dependency once per request and reuses it here (no duplicate DB hit).
    #
    # `links` doubles as the data source for the Links tab's initial state
    # AND the "source link" dropdown on the note-creation form below.
    links = await link_service.list_links(db, project_id=project.id)
    return templates.TemplateResponse(
        "project_detail.html",
        name="project_detail.html",
        context= {
            "request": request,
            "current_user": current_user,
            "project": project,
            "links": links,
            "selected_source_link_id": str(source_link_id) if source_link_id else "",
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
        "notes/_list.html",
        name= "notes/_list.html",
        context = {"request": request, "project": project, "notes": notes}
    )


@router.post("/projects/{project_id}/notes", response_class=HTMLResponse)
async def create_note_ui(
    request: Request,
    title: str = Form(...),
    content: str = Form(""),
    source_link_id: str = Form(""),
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    parsed_source_link_id = uuid.UUID(source_link_id) if source_link_id else None
    await note_service.create_note(
        db,
        project_id=project.id,
        title=title.strip(),
        content=content,
        source_link_id=parsed_source_link_id,
    )
    notes = await note_service.list_notes(db, project_id=project.id)
    return templates.TemplateResponse(
        "notes/_list.html",
        name="notes/_list.html",
        context= {"request": request, "project": project, "notes": notes}
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

    links = await link_service.list_links(db, project_id=project.id)
    return templates.TemplateResponse(
        "notes/_edit_form.html",
        name= "notes/_edit_form.html",
        context = {"request": request, "project": project, "note": note, "links": links},
    )


@router.put("/projects/{project_id}/notes/{note_id}", response_class=HTMLResponse)
async def update_note_ui(
    request: Request,
    note_id: uuid.UUID,
    title: str = Form(...),
    content: str = Form(""),
    source_link_id: str = Form(""),
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    parsed_source_link_id = uuid.UUID(source_link_id) if source_link_id else None
    try:
        note = await note_service.update_note(
            db,
            project_id=project.id,
            note_id=note_id,
            update_data={
                "title": title.strip(),
                "content": content,
                "source_link_id": parsed_source_link_id,
            },
        )
    except note_service.NoteNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Note not found") from exc

    return templates.TemplateResponse(
        "notes/_note_item.html",
        name= "notes/_note_item.html",
        context= {"request": request, "project": project, "note": note}
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
        "notes/_tag_picker.html",
        name= "notes/_tag_picker.html",
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
        "notes/_note_item.html",
        name="notes/_note_item.html",
        context={"request": request, "project": project, "note": note}
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
        "notes/_note_item.html",
        name="notes/_note_item.html",
        context={"request": request, "project": project, "note": note}
    )


# ---------------------------------------------------------------------------
# Project tags (+ click-to-filter)
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/tags/list", response_class=HTMLResponse)
async def list_tags_ui(
    request: Request,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    tags = await tag_service.list_tags(db, project_id=project.id)
    return templates.TemplateResponse(
        "tags/_list.html",
        name="tags/_list.html",
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
        "tags/_list.html",
        name="tags/_list.html",
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


@router.get("/projects/{project_id}/tags/{tag_id}/items", response_class=HTMLResponse)
async def tag_items_ui(
    request: Request,
    tag_id: uuid.UUID,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    try:
        tag = await tag_service.get_tag(db, project_id=project.id, tag_id=tag_id)
    except tag_service.TagNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Tag not found") from exc

    notes, links = await tag_service.get_tagged_items(
        db, project_id=project.id, tag_id=tag.id
    )
    return templates.TemplateResponse(
        "tags/_tag_items.html",
        name="tags/_tag_items.html",
        context={"request": request, "project": project, "tag": tag, "notes": notes, "links": links},
    )


# ---------------------------------------------------------------------------
# Saved links
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/links/list", response_class=HTMLResponse)
async def list_links_ui(
    request: Request,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    links = await link_service.list_links(db, project_id=project.id)
    return templates.TemplateResponse(
        "links/_list.html",
        name="links/_list.html",
        context={"request": request, "project": project, "links": links}
    )


@router.get("/projects/{project_id}/links/{link_id}", response_class=HTMLResponse)
async def get_link_item_ui(
    request: Request,
    link_id: uuid.UUID,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    """Single-link fragment, used by the pending-extraction poller in
    links/_link_item.html (hx-trigger="load delay:3s") to refresh its own
    status without reloading the whole list.
    """
    try:
        link = await link_service.get_link(db, project_id=project.id, link_id=link_id)
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Link not found") from exc

    return templates.TemplateResponse(
        "links/_link_item.html",
        name="links/_link_item.html",
        context={"request": request, "project": project, "link": link}
    )


@router.get("/projects/{project_id}/links/{link_id}/content", response_class=HTMLResponse)
async def link_content_ui(
    request: Request,
    link_id: uuid.UUID,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    try:
        link = await link_service.get_link(db, project_id=project.id, link_id=link_id)
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Link not found") from exc

    return templates.TemplateResponse(
        "links/_extracted_content.html",
        name="links/_extracted_content.html",
        context={"request": request, "link": link}
    )


@router.post("/projects/{project_id}/links/{link_id}/extract", response_class=HTMLResponse)
async def extract_link_ui(
    request: Request,
    link_id: uuid.UUID,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    try:
        link = await link_service.trigger_extraction(
            db, project_id=project.id, link_id=link_id
        )
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Link not found") from exc

    return templates.TemplateResponse(
        "links/_link_item.html",
        name="links/_link_item.html",
        context={"request": request, "project": project, "link": link}
    )


@router.delete("/projects/{project_id}/links/{link_id}")
async def delete_link_ui(
    link_id: uuid.UUID,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await link_service.delete_link(db, project_id=project.id, link_id=link_id)
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Link not found") from exc

    return Response(status_code=status.HTTP_200_OK, content="")


# ---------------------------------------------------------------------------
# Reader mode + highlights
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/links/{link_id}/read", response_class=HTMLResponse)
async def link_reader_page(
    request: Request,
    link_id: uuid.UUID,
    project: Project = Depends(get_current_project_from_cookie),
    current_user: User = Depends(get_current_user_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    try:
        link = await link_service.get_link(db, project_id=project.id, link_id=link_id)
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Link not found") from exc

    highlights = await highlight_service.list_highlights(db, link_id=link.id)
    return templates.TemplateResponse(
        "links/read.html",
        name="links/read.html",
        context= {
            "request": request,
            "current_user": current_user,
            "project": project,
            "link": link,
            "highlights": highlights,
        },
    )


@router.post(
    "/projects/{project_id}/links/{link_id}/highlights", response_class=HTMLResponse
)
async def create_highlight_ui(
    request: Request,
    link_id: uuid.UUID,
    selected_text: str = Form(...),
    annotation: str = Form(""),
    start_offset: int = Form(0),
    end_offset: int = Form(0),
    color: str = Form(None),
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    try:
        link = await link_service.get_link(db, project_id=project.id, link_id=link_id)
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Link not found") from exc

    clean_text = selected_text.strip()
    if clean_text:
        await highlight_service.create_highlight(
            db,
            link_id=link.id,
            selected_text=clean_text,
            annotation=annotation.strip() or None,
            start_offset=start_offset,
            end_offset=end_offset,
            color=color,
        )

    highlights = await highlight_service.list_highlights(db, link_id=link.id)
    return templates.TemplateResponse(
        "links/_highlights_list.html",
        name="links/_highlights_list.html",
        context={"request": request, "project": project, "link": link, "highlights": highlights},
    )


@router.delete(
    "/projects/{project_id}/links/{link_id}/highlights/{highlight_id}"
)
async def delete_highlight_ui(
    link_id: uuid.UUID,
    highlight_id: uuid.UUID,
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
) -> Response:
    try:
        await link_service.get_link(db, project_id=project.id, link_id=link_id)
    except link_service.LinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Link not found") from exc

    try:
        await highlight_service.delete_highlight(
            db, link_id=link_id, highlight_id=highlight_id
        )
    except highlight_service.HighlightNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Highlight not found") from exc

    return Response(status_code=status.HTTP_200_OK, content="")


# ---------------------------------------------------------------------------
# Web search (SearXNG) + saving results as links
# ---------------------------------------------------------------------------


@router.post("/projects/{project_id}/search/web", response_class=HTMLResponse)
async def web_search_ui(
    request: Request,
    query: str = Form(...),
    project: Project = Depends(get_current_project_from_cookie),
):
    clean_query = query.strip()
    error: str | None = None
    results = []

    if clean_query:
        try:
            results = await search_searxng(clean_query)
        except HTTPException as exc:
            error = str(exc.detail)
    else:
        error = "Enter a search term."

    return templates.TemplateResponse(
        "search/_web_results.html",
        name="search/_web_results.html",
        context={
            "request": request,
            "project": project,
            "results": results,
            "query": clean_query,
            "error": error,
        },
    )


@router.post("/projects/{project_id}/links/save", response_class=HTMLResponse)
async def save_link_ui(
    request: Request,
    url: str = Form(...),
    title: str = Form(...),
    snippet: str = Form(""),
    search_query: str = Form(""),
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    await link_service.create_link(
        db,
        project_id=project.id,
        url=url,
        title=title,
        snippet=snippet,
        search_query=search_query.strip() or None,
    )
    return templates.TemplateResponse("search/_link_saved.html",
                                      name="search/_link_saved.html",
                                      context={"request": request}
                                      )


# ---------------------------------------------------------------------------
# Full-text search across notes & links
# ---------------------------------------------------------------------------


@router.get("/projects/{project_id}/search/collected", response_class=HTMLResponse)
async def collected_search_ui(
    request: Request,
    q: str = "",
    project: Project = Depends(get_current_project_from_cookie),
    db: AsyncSession = Depends(get_db),
):
    clean_q = q.strip()
    results = await collected_search_service.search_collected(
        db, project_id=project.id, q=clean_q
    )
    return templates.TemplateResponse(
        "search/_collected_results.html",
        name="search/_collected_results.html",
        context={"request": request, "project": project, "results": results, "q": clean_q},
    )

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.highlight import Highlight
from app.models.project import Project
from app.services import link as link_service
from app.services import note as note_service


async def _highlights_by_link_id(
    session: AsyncSession, link_ids: list[UUID]
) -> dict[UUID, list[Highlight]]:
    """Bulk-fetch highlights for a set of links, grouped by link_id."""
    if not link_ids:
        return {}
    stmt = (
        select(Highlight)
        .where(Highlight.link_id.in_(link_ids))
        .order_by(Highlight.created_at.asc())
    )
    result = await session.execute(stmt)
    grouped: dict[UUID, list[Highlight]] = defaultdict(list)
    for highlight in result.scalars().all():
        grouped[highlight.link_id].append(highlight)
    return grouped


def _md_escape(text: str | None) -> str:
    """Escape Markdown-significant characters in short, single-line fields
    (titles). Body/content fields are rendered as prose or blockquotes below,
    where a stray '*' or '_' from a note or an arbitrary web page is
    cosmetically harmless, so they're left unescaped.
    """
    return re.sub(r"([\\`*_\[\]])", r"\\\1", text or "")


def _blockquote(text: str) -> str:
    """Render (possibly multi-line) text as a Markdown blockquote."""
    return "\n".join(f"> {line}" if line else ">" for line in text.strip().splitlines())


async def build_project_markdown(session: AsyncSession, *, project: Project) -> str:
    """
    Assemble the full Markdown export for one project:
      - H1 heading (project name) + description
      - "## Notes" section: title, content, source link, tags
      - "## Links" section: title, URL, extracted content (if completed),
        tags, and nested highlights

    Ownership is assumed already checked by the caller (the route depends on
    `get_current_project`, same as every other project-scoped endpoint) —
    this function just renders whatever project it's given.
    """
    notes = await note_service.list_notes(session, project_id=project.id)
    links = await link_service.list_links(session, project_id=project.id)
    links_by_id = {link.id: link for link in links}
    highlights_by_link = await _highlights_by_link_id(session, [link.id for link in links])

    out: list[str] = [f"# {_md_escape(project.name)}"]
    if project.description:
        out += ["", project.description]
    out += [
        "",
        f"_Exported {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC_",
        "",
        "---",
        "",
        "## Notes",
        "",
    ]

    if not notes:
        out += ["_No notes yet._", ""]
    for note in notes:
        out.append(f"### {_md_escape(note.title)}")
        out.append("")
        if note.content:
            out += [note.content, ""]

        source = links_by_id.get(note.source_link_id) if note.source_link_id else None
        if source:
            out += [f"**Source:** [{_md_escape(source.title)}]({source.url})", ""]

        if note.tags:
            out += ["**Tags:** " + ", ".join(f"`{t.name}`" for t in note.tags), ""]

        out += ["---", ""]

    out += ["## Links", ""]
    if not links:
        out += ["_No links saved yet._", ""]
    for link in links:
        out.append(f"### {_md_escape(link.title)}")
        out.append("")
        out += [f"<{link.url}>", ""]

        if link.tags:
            out += ["**Tags:** " + ", ".join(f"`{t.name}`" for t in link.tags), ""]

        if link.extraction_status == "completed" and link.extracted_content:
            out += ["**Extracted content:**", "", _blockquote(link.extracted_content), ""]
        elif link.extraction_status == "pending":
            out += ["_Content extraction pending._", ""]
        elif link.extraction_status == "failed":
            out += ["_Content extraction failed._", ""]

        link_highlights = highlights_by_link.get(link.id, [])
        if link_highlights:
            out.append("**Highlights:**")
            out.append("")
            for highlight in link_highlights:
                out.append(_blockquote(highlight.selected_text))
                if highlight.annotation:
                    out.append(f"> — _{highlight.annotation}_")
                out.append("")

        out += ["---", ""]

    # Trim a trailing dangling "---" section divider, keep one final newline.
    while out and out[-1] in ("", "---"):
        out.pop()
    return "\n".join(out) + "\n"


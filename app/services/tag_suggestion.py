# filename: app/services/tag_suggestion.py
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services import tag as tag_service
from app.services.ai import (
    AIError,
    AIResponseFormatError,
    call_ai,
    parse_json_string_array,
)

_SYSTEM_PROMPT = (
    "You are an automated tag classification engine. You output valid JSON objects only."
)

_MAX_SUGGESTIONS = 3
_MAX_CONTENT_CHARS = 4000


def _build_user_prompt(
    title: str | None, content: str, content_type: str, existing_tags: list[str]
) -> str:
    title_line = f"Title: {title}\n" if title else ""
    return (
        f"Available Tags:\n{existing_tags}\n\n"
        f"Input Content:\n"
        f"Type: {content_type}\n"
        f"{title_line}"
        f"Body: {content[:_MAX_CONTENT_CHARS]}\n\n"
        "Example Output:\n"
        '{"tags": ["tag1", "tag2"]}\n\n'
        "Select up to 3 matching tags from Available Tags. Return the JSON object:"
    )


def _filter_suggestions(suggested: list[str], existing_tags: list[str]) -> list[str]:
    """Keep only suggestions that name a real tag in this project."""
    canonical = {name.strip().lower(): name for name in existing_tags}

    result: list[str] = []
    for raw in suggested:
        match = canonical.get(raw.strip().lower())
        if match is not None and match not in result:
            result.append(match)
        if len(result) == _MAX_SUGGESTIONS:
            break

    return result


async def suggest_tags(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    title: str | None = None,
    content: str,
    content_type: str,
) -> list[str]:
    """Suggest up to 3 of the project's existing tags for the given content."""
    if not content.strip() and not (title and title.strip()):
        return []

    tags = await tag_service.list_tags(db, project_id=project_id)
    existing_tags = [tag.name for tag in tags]
    if not existing_tags:
        return []

    prompt = _build_user_prompt(title, content, content_type, existing_tags)

    try:
        raw_text = await call_ai(prompt, system_prompt=_SYSTEM_PROMPT, temperature=0.0)
        suggested = parse_json_string_array(raw_text)
    except (AIError, AIResponseFormatError):
        return []

    return _filter_suggestions(suggested, existing_tags)
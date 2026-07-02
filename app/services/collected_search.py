from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.collected_search import CollectedSearchResult

_SNIPPET_LENGTH = 200

_SEARCH_SQL = text(
    """
    SELECT
        'note'                                        AS type,
        n.id::text                                    AS id,
        n.title                                       AS title,
        left(n.content, :snippet_len)                 AS snippet,
        ts_rank_cd(
            to_tsvector('english', n.title || ' ' || n.content),
            plainto_tsquery('english', :q)
        )                                             AS rank
    FROM notes n
    WHERE
        n.project_id = :project_id
        AND to_tsvector('english', n.title || ' ' || n.content)
            @@ plainto_tsquery('english', :q)

    UNION ALL

    SELECT
        'link'                                        AS type,
        sl.id::text                                   AS id,
        sl.title                                      AS title,
        left(
            coalesce(sl.snippet, '') || ' ' || coalesce(sl.extracted_content, ''),
            :snippet_len
        )                                             AS snippet,
        ts_rank_cd(
            to_tsvector(
                'english',
                coalesce(sl.title, '') || ' ' ||
                coalesce(sl.snippet, '') || ' ' ||
                coalesce(sl.extracted_content, '')
            ),
            plainto_tsquery('english', :q)
        )                                             AS rank
    FROM saved_links sl
    WHERE
        sl.project_id = :project_id
        AND to_tsvector(
                'english',
                coalesce(sl.title, '') || ' ' ||
                coalesce(sl.snippet, '') || ' ' ||
                coalesce(sl.extracted_content, '')
            )
            @@ plainto_tsquery('english', :q)

    ORDER BY rank DESC
    LIMIT 50
    """
)


async def search_collected(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    q: str,
) -> list[CollectedSearchResult]:
    """Full-text search across notes and saved links within a project."""
    if not q or not q.strip():
        return []

    result = await db.execute(
        _SEARCH_SQL,
        {"project_id": project_id, "q": q.strip(), "snippet_len": _SNIPPET_LENGTH},
    )
    rows = result.mappings().all()

    return [
        CollectedSearchResult(
            type=row["type"],
            id=row["id"],
            title=row["title"] or "",
            snippet=(row["snippet"] or "").strip(),
            rank=float(row["rank"]),
        )
        for row in rows
    ]
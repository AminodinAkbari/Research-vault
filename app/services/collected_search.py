from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.collected_search import CollectedSearchResult

_SNIPPET_LENGTH = 200

# PostgreSQL uses native full-text search.
_SEARCH_SQL_POSTGRES = text(
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

# SQLite fallback used by the default in-memory test database.
_SEARCH_SQL_SQLITE = text(
    """
    SELECT
        'note' AS type,
        n.id AS id,
        n.title AS title,
        substr(n.content, 1, :snippet_len) AS snippet,
        1.0 AS rank
    FROM notes n
    WHERE
        n.project_id = :project_id
        AND (n.title LIKE '%' || :q || '%' OR n.content LIKE '%' || :q || '%')

    UNION ALL

    SELECT
        'link' AS type,
        sl.id AS id,
        sl.title AS title,
        substr(
            coalesce(sl.snippet, '') || ' ' || coalesce(sl.extracted_content, ''),
            1,
            :snippet_len
        ) AS snippet,
        1.0 AS rank
    FROM saved_links sl
    WHERE
        sl.project_id = :project_id
        AND (
            sl.title LIKE '%' || :q || '%'
            OR sl.snippet LIKE '%' || :q || '%'
            OR sl.extracted_content LIKE '%' || :q || '%'
        )

    ORDER BY rank DESC
    LIMIT 50
    """
)


def _get_search_sql(db: AsyncSession) -> text:
    dialect = db.bind.dialect.name if db.bind else "postgresql"
    return _SEARCH_SQL_SQLITE if dialect == "sqlite" else _SEARCH_SQL_POSTGRES


async def search_collected(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    q: str,
) -> list[CollectedSearchResult]:
    """Full-text search across notes and saved links within a project."""
    if not q or not q.strip():
        return []

    params = {"project_id": project_id, "q": q.strip(), "snippet_len": _SNIPPET_LENGTH}
    if _get_search_sql(db) is _SEARCH_SQL_SQLITE:
        params["project_id"] = str(project_id)

    result = await db.execute(
        _get_search_sql(db),
        params,
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
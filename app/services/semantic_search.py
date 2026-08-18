from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.link import SavedLink
from app.models.note import Note
from app.schemas.collected_search import CollectedSearchResult, SemanticSearchResult
from app.services.ai import (
    AIError,
    AIResponseFormatError,
    call_ai,
    parse_json_array,
)
from app.services.collected_search import search_collected

_SYSTEM_PROMPT = (
    "You are a strict, automated data-processing API. You do not converse, "
    "you do not explain, and you do not answer questions. Your only job is "
    "to rank document IDs and return a raw JSON array."
)

# Reranking is one AI call over all candidates, so the candidate count and the
# text per candidate together bound the prompt size.
_MAX_CANDIDATES = 10
_LINK_CONTENT_CHARS = 500
_MAX_DOCUMENT_CHARS = 1500


def _normalize_id(value: str) -> str:
    """Canonical form for id comparison.

    The full-text query returns ids as text, whose exact spelling is
    dialect-dependent (Postgres yields a dashed UUID, SQLite the bare 32-char
    hex), and the model may echo them back re-cased or reformatted. Comparing
    on the dash-stripped lowercase form makes all of those match.
    """
    return value.strip().lower().replace("-", "")


def _as_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


async def _load_document_texts(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    candidates: list[CollectedSearchResult],
) -> dict[str, str]:
    """Build the text the model ranks on, keyed by normalized candidate id.

    The snippet from the full-text search is truncated to 200 chars, which is
    too thin to rank on, so the underlying rows are re-read: notes contribute
    title + full content, links contribute title + snippet + the start of
    their extracted content.
    """
    note_ids: list[uuid.UUID] = []
    link_ids: list[uuid.UUID] = []
    for candidate in candidates:
        parsed = _as_uuid(candidate.id)
        if parsed is None:
            continue
        if candidate.type == "note":
            note_ids.append(parsed)
        else:
            link_ids.append(parsed)

    texts: dict[str, str] = {}

    if note_ids:
        result = await db.execute(
            select(Note.id, Note.title, Note.content).where(
                Note.project_id == project_id, Note.id.in_(note_ids)
            )
        )
        for row in result:
            text = f"{row.title or ''}\n{row.content or ''}".strip()
            texts[_normalize_id(str(row.id))] = text[:_MAX_DOCUMENT_CHARS]

    if link_ids:
        result = await db.execute(
            select(
                SavedLink.id,
                SavedLink.title,
                SavedLink.snippet,
                SavedLink.extracted_content,
            ).where(SavedLink.project_id == project_id, SavedLink.id.in_(link_ids))
        )
        for row in result:
            extracted = (row.extracted_content or "")[:_LINK_CONTENT_CHARS]
            text = f"{row.title or ''}\n{row.snippet or ''}\n{extracted}".strip()
            texts[_normalize_id(str(row.id))] = text[:_MAX_DOCUMENT_CHARS]

    # Candidates whose row could not be re-read (deleted between the search and
    # this query, or a non-UUID id) still need to reach the model, otherwise
    # they'd silently drop out of the ranking. Fall back to the search snippet.
    for candidate in candidates:
        key = _normalize_id(candidate.id)
        if not texts.get(key):
            texts[key] = f"{candidate.title}\n{candidate.snippet}".strip()

    return texts


def _build_documents(
    candidates: list[CollectedSearchResult], texts: dict[str, str]
) -> list[dict[str, str]]:
    return [
        {
            "id": candidate.id,
            "type": candidate.type,
            "text": texts.get(_normalize_id(candidate.id), ""),
        }
        for candidate in candidates
    ]


def _reorder(
    candidates: list[CollectedSearchResult], ranked_ids: list[str]
) -> list[CollectedSearchResult]:
    """Apply the model's ordering to the candidates.

    Ids the model invented are ignored, and candidates it left out are kept in
    their original full-text order at the end — reranking should never drop a
    result that full-text search found.
    """
    by_id = {_normalize_id(candidate.id): candidate for candidate in candidates}

    ordered: list[CollectedSearchResult] = []
    seen: set[str] = set()
    for raw_id in ranked_ids:
        if not isinstance(raw_id, str):
            continue
        key = _normalize_id(raw_id)
        if key in by_id and key not in seen:
            seen.add(key)
            ordered.append(by_id[key])

    ordered.extend(
        candidate
        for candidate in candidates
        if _normalize_id(candidate.id) not in seen
    )
    return ordered


async def search_semantic(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    query: str,
) -> list[SemanticSearchResult]:
    """Full-text search followed by AI reranking of the top candidates.

    This is a reranking approach, not vector search: the candidate set comes
    entirely from `search_collected`, so nothing new is retrievable here that
    full-text search would not already find. The AI only reorders.

    Falls back to the full-text order whenever reranking is unavailable or
    unusable (no candidates, AI error, unparsable response). The `semantic`
    flag on each result marks the endpoint, not whether the rerank succeeded.
    """
    candidates = await search_collected(db, project_id=project_id, q=query)
    if not candidates:
        return []

    candidates = candidates[:_MAX_CANDIDATES]

    texts = await _load_document_texts(db, project_id=project_id, candidates=candidates)
    documents = _build_documents(candidates, texts)
     
    prompt = (
        f"Query to match: \"{query}\"\n\n"
        f"Candidates:\n{documents}\n\n"
        "TASK: Analyze the candidates against the query above. Do NOT answer the query. "
        "Output ONLY a raw JSON array of the candidate 'id' strings, ordered from most "
        "relevant to least relevant. Do not wrap the JSON in markdown blocks (no ```json). "
        "No conversational text, no explanations."
    )

    try:
        raw_text = await call_ai(prompt, system_prompt=_SYSTEM_PROMPT, temperature=0.0)
        print()
        print("raw text (comes from ai) : " , raw_text)
        print()
        ranked_ids = parse_json_array(raw_text)
        print("AI done . these are ranks ids :")
        print(ranked_ids)
    except (AIError, AIResponseFormatError) as e:
        print("ERROR | AI result in semantic search : " , e) 
        ranked_ids = []
        print("ranked ids are empty")

    ordered = _reorder(candidates, ranked_ids) if ranked_ids else candidates

    return [
        SemanticSearchResult(**candidate.model_dump(), semantic=True)
        for candidate in ordered
    ]

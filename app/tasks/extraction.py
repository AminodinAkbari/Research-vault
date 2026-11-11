from __future__ import annotations

import logging
import uuid

import httpx
import trafilatura

from app.db.session import SessionLocal
from app.models.link import ExtractionStatus, SavedLink
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

# Use a standard browser User-Agent so publishers don't block the request
# or serve a degraded anti-bot stub page.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


@celery_app.task(name="app.tasks.extraction.extract_link_content")
def extract_link_content(link_id: str) -> None:
    """Fetch a SavedLink URL and extract clean structured content with headings and line breaks."""
    db = SessionLocal()
    try:
        pk = link_id if isinstance(link_id, uuid.UUID) else uuid.UUID(link_id)
        link: SavedLink | None = db.get(SavedLink, pk)
        if link is None:
            logger.error("extract_link_content: link %s not found — skipping", link_id)
            return

        try:
            with httpx.Client(
                timeout=20.0,
                follow_redirects=True,
                headers=_HEADERS,
            ) as client:
                resp = client.get(link.url)
                resp.raise_for_status()
                raw_html = resp.text

            # 1. Extract metadata so manual links without a title get the real article title
            metadata = trafilatura.extract_metadata(raw_html)
            if metadata and metadata.title and (not link.title or link.title == link.url):
                link.title = metadata.title

            # 2. Extract main content with headings, paragraphs, lists, and line breaks preserved
            cleaned_content = trafilatura.extract(
                raw_html,
                url=link.url,
                output_format="markdown",
                include_formatting=True,
                include_links=False,
                include_images=False,
                include_tables=True,
                favor_recall=True,
            )

            if not cleaned_content or not cleaned_content.strip():
                logger.warning(
                    "extract_link_content: empty extraction for link %s", link_id
                )
                link.extraction_status = ExtractionStatus.failed
            else:
                link.extracted_content = cleaned_content
                link.extraction_status = ExtractionStatus.completed
                logger.info("extract_link_content: completed for link %s", link_id)

        except Exception as exc:
            logger.error(
                "extract_link_content: failed for link %s — %s: %s",
                link_id,
                type(exc).__name__,
                exc,
            )
            link.extraction_status = ExtractionStatus.failed

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()
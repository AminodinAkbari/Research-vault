from __future__ import annotations

import logging
import uuid

import httpx
from lxml.html import fromstring
from readability import Document

from app.db.session import SessionLocal
from app.models.link import ExtractionStatus, SavedLink
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

logger.info("Loading extraction module")

# TODO: should we set the header value in .env file or just hardcoded like this ?
_HEADERS = {"User-Agent": "ResearchVault/1.0"}


@celery_app.task(name="app.tasks.extraction.extract_link_content")
def extract_link_content(link_id: str) -> None:
    """Fetch the URL of a SavedLink, extract its main article text with
    readability-lxml, and persist the result.

    Sets ``extraction_status`` to ``"completed"`` on success or ``"failed"``
    on any network / parsing / DB read error. DB commit errors propagate so
    Celery can retry with its normal retry machinery.
    """
    db = SessionLocal()
    try:
        link: SavedLink | None = db.get(SavedLink, uuid.UUID(link_id))
        if link is None:
            logger.error("extract_link_content: link %s not found — skipping", link_id)
            return

        try:
            with httpx.Client(
                timeout=15.0,
                follow_redirects=True,
                headers=_HEADERS,
            ) as client:
                resp = client.get(link.url)
                resp.raise_for_status()

            doc = Document(resp.text)
            raw_html = doc.summary()
            extracted_text = fromstring(raw_html).text_content().strip()

            link.extracted_content = extracted_text or None
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
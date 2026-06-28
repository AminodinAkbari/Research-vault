from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.link import ExtractionStatus, SavedLink
from app.services.link import create_link

TEST_DATABASE_URL_SYNC = os.getenv(
    "TEST_DATABASE_URL_SYNC",
    "sqlite:///:memory:",
)


@pytest.fixture
def sync_db_session() -> Session:
    """Create a synchronous database session for testing the Celery task."""
    engine = create_engine(TEST_DATABASE_URL_SYNC)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


@pytest.fixture
def saved_link_id(sync_db_session: Session) -> uuid.UUID:
    """Create a saved link and return its ID."""
    link = SavedLink(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        url="https://example.com/article",
        title="Test Article",
        snippet="Test snippet",
        extraction_status=ExtractionStatus.pending,
    )
    sync_db_session.add(link)
    sync_db_session.commit()
    return link.id


def get_link_by_id(session: Session, link_id: uuid.UUID) -> SavedLink | None:
    return session.get(SavedLink, link_id)


class TestCreateLinkTriggersExtraction:
    @pytest_asyncio.fixture
    async def project_id(self) -> uuid.UUID:
        return uuid.uuid4()

    @patch("app.services.link.extract_link_content.delay")
    async def test_create_link_triggers_extraction_task(
        self,
        mock_delay: MagicMock,
        db_session,
        project_id: uuid.UUID,
    ) -> None:
        link = await create_link(
            db_session,
            project_id=project_id,
            url="https://example.com/article",
            title="Test Article",
            snippet="Test snippet",
        )

        mock_delay.assert_called_once_with(str(link.id))
        assert link.extraction_status == ExtractionStatus.pending


class TestExtractionTask:
    @patch("app.tasks.extraction.httpx.Client")
    @patch("app.tasks.extraction.Document")
    def test_extract_link_content_success(
        self,
        mock_document: MagicMock,
        mock_client_class: MagicMock,
        sync_db_session: Session,
        saved_link_id: uuid.UUID,
    ) -> None:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "<html><body><p>Article content</p></body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        mock_doc_instance = MagicMock()
        mock_doc_instance.summary.return_value = "<div>Article content</div>"
        mock_document.return_value = mock_doc_instance

        from app.tasks.extraction import extract_link_content
        import app.tasks.extraction as extraction_module

        original_session_local = extraction_module.SessionLocal

        try:
            extraction_module.SessionLocal = lambda: sync_db_session

            extract_link_content.run(str(saved_link_id))

            link = get_link_by_id(sync_db_session, saved_link_id)
            assert link is not None
            assert link.extraction_status == ExtractionStatus.completed
            assert link.extracted_content == "Article content"
            mock_client.get.assert_called_once_with("https://example.com/article")
            mock_document.assert_called_once_with(mock_response.text)
            mock_doc_instance.summary.assert_called_once()

        finally:
            extraction_module.SessionLocal = original_session_local

    @patch("app.tasks.extraction.httpx.Client")
    def test_extract_link_content_network_error(
        self,
        mock_client_class: MagicMock,
        sync_db_session: Session,
        saved_link_id: uuid.UUID,
    ) -> None:
        import httpx

        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_client.get.side_effect = httpx.ConnectError("Connection failed")

        from app.tasks.extraction import extract_link_content
        import app.tasks.extraction as extraction_module

        original_session_local = extraction_module.SessionLocal

        try:
            extraction_module.SessionLocal = lambda: sync_db_session

            extract_link_content.run(str(saved_link_id))

            link = get_link_by_id(sync_db_session, saved_link_id)
            assert link is not None
            assert link.extraction_status == ExtractionStatus.failed
            assert link.extracted_content is None

        finally:
            extraction_module.SessionLocal = original_session_local

    @patch("app.tasks.extraction.httpx.Client")
    @patch("app.tasks.extraction.Document")
    def test_extract_link_content_parsing_error(
        self,
        mock_document: MagicMock,
        mock_client_class: MagicMock,
        sync_db_session: Session,
        saved_link_id: uuid.UUID,
    ) -> None:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        mock_response = MagicMock()
        mock_response.text = "<html><body>Invalid</body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_response

        mock_document.side_effect = ValueError("Parsing failed")

        from app.tasks.extraction import extract_link_content
        import app.tasks.extraction as extraction_module

        original_session_local = extraction_module.SessionLocal

        try:
            extraction_module.SessionLocal = lambda: sync_db_session

            extract_link_content.run(str(saved_link_id))

            link = get_link_by_id(sync_db_session, saved_link_id)
            assert link is not None
            assert link.extraction_status == ExtractionStatus.failed

        finally:
            extraction_module.SessionLocal = original_session_local
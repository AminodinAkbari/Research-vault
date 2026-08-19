from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExtractionStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"


class SavedLink(Base):
    __tablename__ = "saved_links"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    url: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    snippet: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    search_query: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    extracted_content: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    extraction_status: Mapped[ExtractionStatus] = mapped_column(
        SAEnum(ExtractionStatus, name="extraction_status", create_constraint=True),
        nullable=False,
        default=ExtractionStatus.pending,
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="saved_links",
        lazy="select",
    )
    link_tags: Mapped[list[LinkTag]] = relationship(
        "LinkTag",
        back_populates="link",
        cascade="all, delete-orphan",
        lazy="select",
    )
    # Convenience M2M view (read-only; mutations go through LinkTag)
    tags: Mapped[list[Tag]] = relationship(
        "Tag",
        secondary="link_tags",
        viewonly=True,
        lazy="select",
    )
    highlights: Mapped[list[Highlight]] = relationship(
        "Highlight",
        back_populates="link",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<SavedLink id={self.id} url={self.url!r}>"
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="notes",
        lazy="select",
    )
    note_tags: Mapped[list[NoteTag]] = relationship(
        "NoteTag",
        back_populates="note",
        cascade="all, delete-orphan",
        lazy="select",
    )
    # Convenience M2M view (read-only; mutations go through NoteTag)
    tags: Mapped[list[Tag]] = relationship(
        "Tag",
        secondary="note_tags",
        viewonly=True,
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Note id={self.id} title={self.title!r}>"

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

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
    # Optional reference to the saved link this note was written about.
    # ON DELETE SET NULL: deleting the source link should not delete the note,
    # just detach the reference.
    source_link_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("saved_links.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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
    # Read-only convenience view onto the source link. Uses the class-name
    # string ("SavedLink") and a string foreign_keys spec so this resolves
    # purely through the declarative registry — no import of SavedLink
    # needed here, and no dependency on forward-ref annotation evaluation.
    source_link: Mapped[Optional["SavedLink"]] = relationship(
        "SavedLink",
        foreign_keys="Note.source_link_id",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Note id={self.id} title={self.title!r}>"
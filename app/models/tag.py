from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_tag_project_name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    project: Mapped[Project] = relationship(
        "Project",
        back_populates="tags",
        lazy="select",
    )
    note_tags: Mapped[list[NoteTag]] = relationship(
        "NoteTag",
        back_populates="tag",
        cascade="all, delete-orphan",
        lazy="select",
    )
    link_tags: Mapped[list[LinkTag]] = relationship(
        "LinkTag",
        back_populates="tag",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Tag id={self.id} name={self.name!r}>"


class NoteTag(Base):
    """Association table: notes ↔ tags (composite PK)."""

    __tablename__ = "note_tags"

    note_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )

    note: Mapped[Note] = relationship(
        "Note",
        back_populates="note_tags",
        lazy="select",
    )
    tag: Mapped[Tag] = relationship(
        "Tag",
        back_populates="note_tags",
        lazy="select",
    )


class LinkTag(Base):
    """Association table: saved_links ↔ tags (composite PK)."""

    __tablename__ = "link_tags"

    link_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("saved_links.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )

    link: Mapped[SavedLink] = relationship(
        "SavedLink",
        back_populates="link_tags",
        lazy="select",
    )
    tag: Mapped[Tag] = relationship(
        "Tag",
        back_populates="link_tags",
        lazy="select",
    )

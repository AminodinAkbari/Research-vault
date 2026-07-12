from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Highlight(Base):
    """A user-selected excerpt of a saved link's extracted content, with an
    optional free-text annotation. Offsets are stored as given by the client
    (plain character positions within `extracted_content`) — no server-side
    validation against the source text is performed for the MVP.
    """

    __tablename__ = "highlights"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    link_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("saved_links.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    selected_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    annotation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    start_offset: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    end_offset: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )

    link: Mapped[SavedLink] = relationship(
        "SavedLink",
        back_populates="highlights",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Highlight id={self.id} link_id={self.link_id}>"
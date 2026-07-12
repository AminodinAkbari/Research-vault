"""add note.source_link_id and highlights table

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-07-11 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notes",
        sa.Column("source_link_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_notes_source_link_id", "notes", ["source_link_id"])
    op.create_foreign_key(
        "fk_notes_source_link_id_saved_links",
        "notes",
        "saved_links",
        ["source_link_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "highlights",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "link_id",
            sa.Uuid(),
            sa.ForeignKey("saved_links.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("selected_text", sa.Text(), nullable=False),
        sa.Column("annotation", sa.Text(), nullable=True),
        sa.Column("start_offset", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("end_offset", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_highlights_link_id", "highlights", ["link_id"])


def downgrade() -> None:
    op.drop_index("ix_highlights_link_id", table_name="highlights")
    op.drop_table("highlights")
    op.drop_constraint("fk_notes_source_link_id_saved_links", "notes", type_="foreignkey")
    op.drop_index("ix_notes_source_link_id", table_name="notes")
    op.drop_column("notes", "source_link_id")

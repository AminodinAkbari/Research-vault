"""add reading-list status to saved_links

Revision ID: c3d4e5f6a7b8
Revises: add_summary_to_saved_links
Create Date: 2026-08-23 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'add_summary_to_saved_links'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "saved_links",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="to_read",
        ),
    )


def downgrade() -> None:
    op.drop_column("saved_links", "status")

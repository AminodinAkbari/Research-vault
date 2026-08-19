# filename: alembic/versions/add_summary_to_saved_links.py
"""add summary to saved_links

Revision ID: add_summary_to_saved_links
Revises: 88f968ac0f36
Create Date: 2026-08-19 16:20:14.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'add_summary_to_saved_links'
# 88f968ac0f36 is the last known migration from your directory structure
down_revision: Union[str, Sequence[str], None] = '88f968ac0f36'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "saved_links",
        sa.Column("summary", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("saved_links", "summary")
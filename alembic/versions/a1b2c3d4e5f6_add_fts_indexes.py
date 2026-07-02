"""add full-text search indexes on notes and saved_links

Revision ID: a1b2c3d4e5f6
Revises: 8e68d03e78f1
Create Date: 2026-06-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "8e68d03e78f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_notes_fts
        ON notes
        USING GIN (to_tsvector('english', title || ' ' || content));
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_saved_links_fts
        ON saved_links
        USING GIN (
            to_tsvector(
                'english',
                coalesce(title, '') || ' ' ||
                coalesce(snippet, '') || ' ' ||
                coalesce(extracted_content, '')
            )
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_notes_fts;")
    op.execute("DROP INDEX IF EXISTS ix_saved_links_fts;")

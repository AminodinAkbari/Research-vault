"""add color to highlights

Revision ID: 88f968ac0f36
Revises: b7c8d9e0f1a2
Create Date: 2026-07-12 13:13:29.571254

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88f968ac0f36'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "highlights",
        sa.Column("color", sa.String(20), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("highlights", "color")

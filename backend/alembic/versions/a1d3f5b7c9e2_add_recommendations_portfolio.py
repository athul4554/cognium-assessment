"""add recommendations portfolio

Revision ID: a1d3f5b7c9e2
Revises: 7f3b5d9c2a46
Create Date: 2026-10-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1d3f5b7c9e2'
down_revision: Union[str, Sequence[str], None] = '7f3b5d9c2a46'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing rows come back with no portfolio metrics
    op.add_column("recommendations", sa.Column("portfolio", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("recommendations", "portfolio")

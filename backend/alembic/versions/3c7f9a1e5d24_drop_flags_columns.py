"""drop flags columns

Revision ID: 3c7f9a1e5d24
Revises: 8e4a6d2b1f57
Create Date: 2026-10-19 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '3c7f9a1e5d24'
down_revision: Union[str, Sequence[str], None] = '8e4a6d2b1f57'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("assessment_results", "flags")
    op.drop_column("recommendations", "flags")


def downgrade() -> None:
    """Downgrade schema."""
    # Dropped values are not restored, old rows come back as []
    op.add_column(
        "recommendations", sa.Column("flags", postgresql.JSONB(), nullable=False, server_default="[]")
    )
    op.add_column(
        "assessment_results", sa.Column("flags", postgresql.JSONB(), nullable=False, server_default="[]")
    )

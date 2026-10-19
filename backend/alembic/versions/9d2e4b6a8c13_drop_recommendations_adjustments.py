"""drop recommendations adjustments

Revision ID: 9d2e4b6a8c13
Revises: 3c7f9a1e5d24
Create Date: 2026-10-19 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '9d2e4b6a8c13'
down_revision: Union[str, Sequence[str], None] = '3c7f9a1e5d24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("recommendations", "adjustments")


def downgrade() -> None:
    """Downgrade schema."""
    # Dropped values are not restored, old rows come back as []
    op.add_column(
        "recommendations", sa.Column("adjustments", postgresql.JSONB(), nullable=False, server_default="[]")
    )

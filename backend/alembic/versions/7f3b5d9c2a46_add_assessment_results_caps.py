"""add assessment_results caps

Revision ID: 7f3b5d9c2a46
Revises: 4a8c2e6f0b91
Create Date: 2026-10-19 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '7f3b5d9c2a46'
down_revision: Union[str, Sequence[str], None] = '4a8c2e6f0b91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing rows come back with no caps
    op.add_column(
        "assessment_results",
        sa.Column("caps", postgresql.JSONB(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("assessment_results", "caps")

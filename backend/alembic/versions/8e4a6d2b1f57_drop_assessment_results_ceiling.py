"""drop assessment_results ceiling

Revision ID: 8e4a6d2b1f57
Revises: 5b1f2c7d9e30
Create Date: 2026-10-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e4a6d2b1f57'
down_revision: Union[str, Sequence[str], None] = '5b1f2c7d9e30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_column("assessment_results", "ceiling")


def downgrade() -> None:
    """Downgrade schema."""
    # Dropped values are not restored, old rows come back as NULL
    op.add_column("assessment_results", sa.Column("ceiling", sa.Text(), nullable=True))

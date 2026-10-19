"""create recommendations table

Revision ID: 5b1f2c7d9e30
Revises: c0899e024052
Create Date: 2026-10-18 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '5b1f2c7d9e30'
down_revision: Union[str, Sequence[str], None] = 'c0899e024052'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "recommendations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "assessment_result_id", sa.UUID(), sa.ForeignKey("assessment_results.id"), nullable=False, unique=True
        ),
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column("level", sa.SmallInteger(), nullable=False),
        # Reuses the currency type created with the risk assessment tables
        sa.Column("currency", postgresql.ENUM(name="currency", create_type=False), nullable=False),
        sa.Column("invest_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("monthly_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("holdings", postgresql.JSONB(), nullable=False),
        sa.Column("adjustments", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("flags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("rules_version", sa.String(20), nullable=False),
        sa.Column("universe_as_of", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_recommendations_user_id", "recommendations", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_recommendations_user_id", table_name="recommendations")
    op.drop_table("recommendations")

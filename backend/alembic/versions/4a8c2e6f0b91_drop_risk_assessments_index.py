"""drop risk_assessments user_id created_at index

Revision ID: 4a8c2e6f0b91
Revises: 9d2e4b6a8c13
Create Date: 2026-10-19 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '4a8c2e6f0b91'
down_revision: Union[str, Sequence[str], None] = '9d2e4b6a8c13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index("ix_risk_assessments_user_id_created_at", table_name="risk_assessments")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_index(
        "ix_risk_assessments_user_id_created_at", "risk_assessments", ["user_id", "created_at"]
    )

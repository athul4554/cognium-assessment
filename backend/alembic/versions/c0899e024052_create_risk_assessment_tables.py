"""create risk assessment tables

Revision ID: c0899e024052
Revises:
Create Date: 2026-10-18 15:58:04.287403

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c0899e024052'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Values are frozen here on purpose, later changes need their own migration
ENUMS = {
    "currency": ("USD", "AED", "EUR", "GBP"),
    "horizon": ("under_2", "2_5", "5_10", "10_plus"),
    "emergency_fund": ("none", "under_3_months", "3_6_months", "6_plus_months"),
    "income": ("none", "self_employed", "variable", "salaried"),
    "share_of_wealth": ("over_50", "25_50", "10_25", "under_10"),
    "portfolio": ("A", "B", "C"),
    "drop_reaction": ("sell_all", "sell_some", "hold", "buy_more"),
    "max_loss": ("0", "5", "15", "30_plus"),
    "goal": ("capital_preservation", "income", "balanced_growth", "aggressive_growth"),
    "experience": ("none", "funds_only", "stocks_etfs", "derivatives_leverage"),
    "exclusion": ("no_crypto", "sharia_compliant", "esg_preference"),
}


def enum(name: str) -> postgresql.ENUM:
    return postgresql.ENUM(*ENUMS[name], name=name, create_type=False)


def upgrade() -> None:
    """Upgrade schema."""
    for name, values in ENUMS.items():
        postgresql.ENUM(*values, name=name).create(op.get_bind())

    op.create_table(
        "risk_assessments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column("birth_year", sa.SmallInteger(), nullable=False),
        sa.Column("currency", enum("currency"), nullable=False),
        sa.Column("invest_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("monthly_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("horizon", enum("horizon"), nullable=False),
        sa.Column("big_withdrawal", sa.Boolean(), nullable=False),
        sa.Column("emergency_fund", enum("emergency_fund"), nullable=False),
        sa.Column("income", enum("income"), nullable=False),
        sa.Column("share_of_wealth", enum("share_of_wealth"), nullable=False),
        sa.Column("portfolio", enum("portfolio"), nullable=False),
        sa.Column("drop_reaction", enum("drop_reaction"), nullable=False),
        sa.Column("max_loss", enum("max_loss"), nullable=False),
        sa.Column("goal", enum("goal"), nullable=False),
        sa.Column("experience", enum("experience"), nullable=False),
        sa.Column("exclusions", postgresql.ARRAY(enum("exclusion")), nullable=False, server_default="{}"),
        sa.Column("notes", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_risk_assessments_user_id_created_at", "risk_assessments", ["user_id", "created_at"]
    )

    op.create_table(
        "assessment_results",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("assessment_id", sa.UUID(), sa.ForeignKey("risk_assessments.id"), nullable=False, unique=True),
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column("level", sa.SmallInteger(), nullable=False),
        sa.Column("capacity_score", sa.SmallInteger(), nullable=False),
        sa.Column("capacity_level", sa.SmallInteger(), nullable=False),
        sa.Column("capacity_reasons", postgresql.JSONB(), nullable=False),
        sa.Column("tolerance_score", sa.SmallInteger(), nullable=False),
        sa.Column("tolerance_level", sa.SmallInteger(), nullable=False),
        sa.Column("tolerance_reasons", postgresql.JSONB(), nullable=False),
        sa.Column("ceiling", sa.Text(), nullable=True),
        sa.Column("flags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("questionnaire_version", sa.String(20), nullable=False),
        sa.Column("scoring_rules_version", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_assessment_results_user_id", "assessment_results", ["user_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_assessment_results_user_id", table_name="assessment_results")
    op.drop_table("assessment_results")
    op.drop_index("ix_risk_assessments_user_id_created_at", table_name="risk_assessments")
    op.drop_table("risk_assessments")
    for name in ENUMS:
        postgresql.ENUM(name=name).drop(op.get_bind())

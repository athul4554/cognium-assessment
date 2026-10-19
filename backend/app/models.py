import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from . import constants as c
from .db import Base


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(c.USER_ID_MAX_LENGTH), nullable=False)

    # capacity
    birth_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    currency: Mapped[str] = mapped_column(Enum(*c.CURRENCIES, name="currency"), nullable=False)
    invest_amount: Mapped[Decimal] = mapped_column(Numeric(c.AMOUNT_MAX_DIGITS, c.AMOUNT_DECIMAL_PLACES), nullable=False)
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(c.AMOUNT_MAX_DIGITS, c.AMOUNT_DECIMAL_PLACES), nullable=False)
    horizon: Mapped[str] = mapped_column(Enum(*c.HORIZONS, name="horizon"), nullable=False)
    big_withdrawal: Mapped[bool] = mapped_column(Boolean, nullable=False)
    emergency_fund: Mapped[str] = mapped_column(Enum(*c.EMERGENCY_FUNDS, name="emergency_fund"), nullable=False)
    income: Mapped[str] = mapped_column(Enum(*c.INCOMES, name="income"), nullable=False)
    share_of_wealth: Mapped[str] = mapped_column(Enum(*c.SHARES_OF_WEALTH, name="share_of_wealth"), nullable=False)

    # tolerance
    portfolio: Mapped[str] = mapped_column(Enum(*c.PORTFOLIOS, name="portfolio"), nullable=False)
    drop_reaction: Mapped[str] = mapped_column(Enum(*c.DROP_REACTIONS, name="drop_reaction"), nullable=False)
    max_loss: Mapped[str] = mapped_column(Enum(*c.MAX_LOSSES, name="max_loss"), nullable=False)
    goal: Mapped[str] = mapped_column(Enum(*c.GOALS, name="goal"), nullable=False)
    experience: Mapped[str] = mapped_column(Enum(*c.EXPERIENCES, name="experience"), nullable=False)

    exclusions: Mapped[list[str]] = mapped_column(
        ARRAY(Enum(*c.EXCLUSIONS, name="exclusion")), nullable=False, server_default="{}"
    )
    notes: Mapped[str | None] = mapped_column(String(c.NOTES_MAX_LENGTH), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("risk_assessments.id"), unique=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(c.USER_ID_MAX_LENGTH), nullable=False, index=True)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    capacity_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    capacity_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    capacity_reasons: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    tolerance_score: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tolerance_level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    tolerance_reasons: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    questionnaire_version: Mapped[str] = mapped_column(String(20), nullable=False)
    scoring_rules_version: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Recommendation(Base):

    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_result_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assessment_results.id"), unique=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(c.USER_ID_MAX_LENGTH), nullable=False, index=True)
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    currency: Mapped[str] = mapped_column(Enum(*c.CURRENCIES, name="currency"), nullable=False)
    invest_amount: Mapped[Decimal] = mapped_column(Numeric(c.AMOUNT_MAX_DIGITS, c.AMOUNT_DECIMAL_PLACES), nullable=False)
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(c.AMOUNT_MAX_DIGITS, c.AMOUNT_DECIMAL_PLACES), nullable=False)
    holdings: Mapped[list[dict]] = mapped_column(JSONB, nullable=False)
    rules_version: Mapped[str] = mapped_column(String(20), nullable=False)
    universe_as_of: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

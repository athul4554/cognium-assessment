import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, PlainSerializer, field_validator

from . import constants as c

# Amounts are stored as exact decimals but returned as JSON numbers
Amount = Annotated[
    Decimal,
    Field(max_digits=c.AMOUNT_MAX_DIGITS, decimal_places=c.AMOUNT_DECIMAL_PLACES),
    PlainSerializer(float, return_type=float),
]
UserId = Annotated[str, Field(min_length=1, max_length=c.USER_ID_MAX_LENGTH)]


class Capacity(BaseModel):
    birth_year: int
    currency: c.Currency
    invest_amount: Annotated[Amount, Field(gt=0)]
    monthly_amount: Annotated[Amount, Field(ge=0)]
    horizon: c.Horizon
    big_withdrawal: bool
    emergency_fund: c.EmergencyFund
    income: c.Income
    share_of_wealth: c.ShareOfWealth

    @field_validator("birth_year")
    @classmethod
    def check_birth_year(cls, value: int) -> int:
        if not c.MIN_BIRTH_YEAR <= value <= date.today().year:
            raise ValueError(f"must be between {c.MIN_BIRTH_YEAR} and {date.today().year}")
        return value


class Tolerance(BaseModel):
    portfolio: c.Portfolio
    drop: c.DropReaction
    max_loss: c.MaxLoss
    goal: c.Goal
    experience: c.Experience


class RiskAssessmentIn(BaseModel):
    user_id: UserId
    capacity: Capacity
    tolerance: Tolerance
    exclusions: list[c.Exclusion]
    notes: Annotated[str | None, Field(max_length=c.NOTES_MAX_LENGTH)] = None

    @field_validator("user_id")
    @classmethod
    def strip_user_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("exclusions")
    @classmethod
    def check_unique(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("must not contain duplicates")
        return value

    @field_validator("notes")
    @classmethod
    def blank_notes_to_none(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        return value.strip()


class RiskAssessmentOut(RiskAssessmentIn):
    id: uuid.UUID
    created_at: datetime


class AssessmentResultIn(BaseModel):
    user_id: UserId


class Score(BaseModel):
    title: str
    label: str
    score: int
    reasons: list[dict[str, Any]]


class Record(BaseModel):
    assessment: uuid.UUID
    submitted_at: datetime
    questionnaire: str
    scoring_rules: str


class AssessmentResultOut(BaseModel):
    user_id: str
    level: int
    label: str
    scores: list[Score]
    record: Record


# Recommendation

class RecommendationIn(BaseModel):
    user_id: UserId


class Metrics(BaseModel):
    last_close: float
    last_close_date: date
    return_1y_pct: float | None
    return_3y_annualised_pct: float | None
    volatility_1y_pct: float | None
    max_drawdown_3y_pct: float | None
    source: Literal["live", "snapshot"]


class Holding(BaseModel):
    sleeve: str
    sleeve_label: str
    group: str
    weight: int
    amount: float
    monthly_amount: float
    ticker: str | None
    name: str
    provider: str | None
    category: str | None
    expense_ratio_pct: float | None
    distribution_yield_pct: float | None
    inception_date: date | None
    esg: bool
    sharia_compliant: bool
    metrics: Metrics | None


class GroupWeight(BaseModel):
    group: str
    weight: int
    amount: float
    monthly_amount: float


class RecommendationRecord(BaseModel):
    assessment: uuid.UUID
    assessment_result: uuid.UUID
    recommended_at: datetime
    rules: str
    universe_as_of: date


class RecommendationOut(BaseModel):
    user_id: str
    level: int
    label: str
    currency: str
    invest_amount: Amount
    monthly_amount: Amount
    groups: list[GroupWeight]
    holdings: list[Holding]
    record: RecommendationRecord

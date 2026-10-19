import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .. import constants as c
from ..db import get_db
from ..models import AssessmentResult, RiskAssessment
from ..schemas import (
    AssessmentResultIn,
    AssessmentResultOut,
    RiskAssessmentIn,
    RiskAssessmentOut,
)
from .scoring import compute_result, profile_label

logger = logging.getLogger(__name__)

router = APIRouter(prefix=c.API_PREFIX, tags=["Risk assessment"])

UserIdQuery = Query(min_length=1, max_length=c.USER_ID_MAX_LENGTH)


def db_error(db: Session, exc: SQLAlchemyError) -> HTTPException:
    db.rollback()
    logger.exception("Database error: %s", exc)
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, c.DB_ERROR)


def latest_assessment(db: Session, user_id: str) -> RiskAssessment:
    assessment = db.scalars(
        select(RiskAssessment)
        .where(RiskAssessment.user_id == user_id.strip())
        .order_by(RiskAssessment.created_at.desc())
        .limit(1)
    ).first()
    if assessment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, c.NO_SUBMISSION)
    return assessment


def result_of(db: Session, assessment: RiskAssessment) -> AssessmentResult | None:
    return db.scalars(
        select(AssessmentResult).where(AssessmentResult.assessment_id == assessment.id)
    ).first()


def to_assessment_out(a: RiskAssessment) -> RiskAssessmentOut:
    return RiskAssessmentOut(
        id=a.id,
        user_id=a.user_id,
        capacity={
            "birth_year": a.birth_year,
            "currency": a.currency,
            "invest_amount": a.invest_amount,
            "monthly_amount": a.monthly_amount,
            "horizon": a.horizon,
            "big_withdrawal": a.big_withdrawal,
            "emergency_fund": a.emergency_fund,
            "income": a.income,
            "share_of_wealth": a.share_of_wealth,
        },
        tolerance={
            "portfolio": a.portfolio,
            "drop": a.drop_reaction,
            "max_loss": a.max_loss,
            "goal": a.goal,
            "experience": a.experience,
        },
        exclusions=a.exclusions,
        notes=a.notes,
        created_at=a.created_at,
    )


def to_result_out(r: AssessmentResult, a: RiskAssessment) -> AssessmentResultOut:
    return AssessmentResultOut(
        user_id=r.user_id,
        level=r.level,
        label=profile_label(r.level),
        caps=r.caps,
        scores=[
            {
                "title": c.CAPACITY_TITLE,
                "label": profile_label(r.capacity_level),
                "score": r.capacity_score,
                "reasons": r.capacity_reasons,
            },
            {
                "title": c.TOLERANCE_TITLE,
                "label": profile_label(r.tolerance_level),
                "score": r.tolerance_score,
                "reasons": r.tolerance_reasons,
            },
        ],
        record={
            "assessment": a.id,
            "submitted_at": a.created_at,
            "questionnaire": r.questionnaire_version,
            "scoring_rules": r.scoring_rules_version,
        },
    )


@router.post("/risk-assessment", response_model=RiskAssessmentOut, status_code=status.HTTP_201_CREATED)
def create_risk_assessment(payload: RiskAssessmentIn, db: Session = Depends(get_db)):
    assessment = RiskAssessment(
        user_id=payload.user_id,
        **payload.capacity.model_dump(),
        portfolio=payload.tolerance.portfolio,
        drop_reaction=payload.tolerance.drop,
        max_loss=payload.tolerance.max_loss,
        goal=payload.tolerance.goal,
        experience=payload.tolerance.experience,
        exclusions=payload.exclusions,
        notes=payload.notes,
    )
    try:
        db.add(assessment)
        db.commit()
        db.refresh(assessment)
    except SQLAlchemyError as exc:
        raise db_error(db, exc)
    return to_assessment_out(assessment)


@router.get("/risk-assessment", response_model=RiskAssessmentOut)
def get_risk_assessment(user_id: str = UserIdQuery, db: Session = Depends(get_db)):
    try:
        assessment = latest_assessment(db, user_id)
    except SQLAlchemyError as exc:
        raise db_error(db, exc)
    return to_assessment_out(assessment)


@router.post("/assessment-result", response_model=AssessmentResultOut, status_code=status.HTTP_201_CREATED)
def create_assessment_result(payload: AssessmentResultIn, response: Response, db: Session = Depends(get_db)):
    try:
        assessment = latest_assessment(db, payload.user_id)

        # Results are locked once computed
        existing = result_of(db, assessment)
        if existing:
            response.status_code = status.HTTP_200_OK
            return to_result_out(existing, assessment)

        result = AssessmentResult(
            assessment_id=assessment.id,
            user_id=assessment.user_id,
            **compute_result(assessment),
        )
        try:
            db.add(result)
            db.commit()
        except IntegrityError:
            # Another request stored the result first, return that one
            db.rollback()
            response.status_code = status.HTTP_200_OK
            return to_result_out(result_of(db, assessment), assessment)
        db.refresh(result)
    except SQLAlchemyError as exc:
        raise db_error(db, exc)
    return to_result_out(result, assessment)


@router.get("/assessment-result", response_model=AssessmentResultOut)
def get_assessment_result(user_id: str = UserIdQuery, db: Session = Depends(get_db)):
    try:
        assessment = latest_assessment(db, user_id)
        result = result_of(db, assessment)
    except SQLAlchemyError as exc:
        raise db_error(db, exc)
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, c.NO_RESULT)
    return to_result_out(result, assessment)

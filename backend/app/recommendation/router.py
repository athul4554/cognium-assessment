import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .. import constants as c
from ..db import get_db
from ..assessment.scoring import profile_label
from ..models import AssessmentResult, Recommendation, RiskAssessment
from ..schemas import RecommendationIn, RecommendationOut
from .builder import build_recommendation, group_weights, load_rules

logger = logging.getLogger(__name__)

router = APIRouter(prefix=c.API_PREFIX, tags=["Recommendation"])

UserIdQuery = Query(min_length=1, max_length=c.USER_ID_MAX_LENGTH)


def db_error(db: Session, exc: SQLAlchemyError) -> HTTPException:
    db.rollback()
    logger.exception("Database error: %s", exc)
    return HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, c.DB_ERROR)


def latest_result(db: Session, user_id: str) -> tuple[RiskAssessment, AssessmentResult]:

    assessment = db.scalars(
        select(RiskAssessment)
        .where(RiskAssessment.user_id == user_id.strip())
        .order_by(RiskAssessment.created_at.desc())
        .limit(1)
    ).first()
    if assessment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, c.NO_SUBMISSION)

    result: AssessmentResult | None = db.scalars(
        select(AssessmentResult).where(AssessmentResult.assessment_id == assessment.id)
    ).first()
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, c.NO_RESULT)
    return assessment, result


def recommendation_of(db: Session, result: AssessmentResult) -> Recommendation | None:
    return db.scalars(
        select(Recommendation).where(Recommendation.assessment_result_id == result.id)
    ).first()


def build(assessment: RiskAssessment, result: AssessmentResult) -> Recommendation:
    built = build_recommendation(
        level=result.level,
        exclusions=assessment.exclusions,
        invest_amount=assessment.invest_amount,
        monthly_amount=assessment.monthly_amount,
        max_loss=assessment.max_loss,
    )

    return Recommendation(
        assessment_result_id=result.id,
        user_id=assessment.user_id,
        level=result.level,
        currency=assessment.currency,
        invest_amount=assessment.invest_amount,
        monthly_amount=assessment.monthly_amount,
        holdings=built["holdings"],
        portfolio=built["portfolio"],
        rules_version=built["rules_version"],
        universe_as_of=built["universe_as_of"],
    )


def to_out(r: Recommendation, a: RiskAssessment, result: AssessmentResult) -> RecommendationOut:
    return RecommendationOut(
        user_id=r.user_id,
        level=r.level,
        label=profile_label(r.level),
        currency=r.currency,
        invest_amount=r.invest_amount,
        monthly_amount=r.monthly_amount,
        groups=group_weights(r.holdings),
        holdings=r.holdings,
        metrics=r.portfolio,
        disclaimer=c.DISCLAIMER,
        record={
            "assessment": a.id,
            "assessment_result": result.id,
            "recommended_at": r.created_at,
            "rules": r.rules_version,
            "universe_as_of": r.universe_as_of,
        },
    )


@router.post("/recommendation", response_model=RecommendationOut, status_code=status.HTTP_201_CREATED)
def create_recommendation(payload: RecommendationIn, response: Response, db: Session = Depends(get_db)):
    try:
        assessment, result = latest_result(db, payload.user_id)
        existing = recommendation_of(db, result)
        if (existing and existing.rules_version == load_rules()["version"]
                and (existing.portfolio or {}).get("reason") not in {
                    "no_data", "optimizer_failed", "cash_adjusted",
                }):
            response.status_code = status.HTTP_200_OK
            return to_out(existing, assessment, result)

        recommendation = build(assessment, result)
        if existing:
            # Rebuild stale rules in the existing JSON record; no schema change.
            for field in ("holdings", "portfolio", "rules_version", "universe_as_of"):
                setattr(existing, field, getattr(recommendation, field))
            existing.created_at = func.now()
            recommendation = existing
        try:
            db.add(recommendation)
            db.commit()
        except IntegrityError:
            # Another request stored it first, return that one
            db.rollback()
            response.status_code = status.HTTP_200_OK
            stored = recommendation_of(db, result)
            if stored is None or stored.rules_version != load_rules()["version"]:
                raise HTTPException(status.HTTP_409_CONFLICT, c.OUTDATED_RECOMMENDATION)
            return to_out(stored, assessment, result)
        db.refresh(recommendation)
    except SQLAlchemyError as exc:
        raise db_error(db, exc)
    return to_out(recommendation, assessment, result)


@router.get("/recommendation", response_model=RecommendationOut)
def get_recommendation(user_id: str = UserIdQuery, db: Session = Depends(get_db)):
    try:
        assessment, result = latest_result(db, user_id)
        recommendation = recommendation_of(db, result)
    except SQLAlchemyError as exc:
        raise db_error(db, exc)
    if recommendation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, c.NO_RECOMMENDATION)
    if recommendation.rules_version != load_rules()["version"]:
        raise HTTPException(status.HTTP_409_CONFLICT, c.OUTDATED_RECOMMENDATION)
    return to_out(recommendation, assessment, result)

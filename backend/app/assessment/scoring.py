import json
from functools import lru_cache
from typing import Any

from ..constants import SCORER_PATH
from ..models import RiskAssessment


@lru_cache
def load_scorer() -> dict[str, Any]:
    with open(SCORER_PATH, encoding="utf-8") as f:
        return json.load(f)


def profile_label(level: int) -> str:
    return next(p["label"] for p in load_scorer()["profiles"] if p["level"] == level)


def answers_of(assessment: RiskAssessment) -> dict[str, Any]:
    """Answers keyed by the scorer field names."""
    return {
        "capacity.horizon": assessment.horizon,
        "capacity.big_withdrawal": assessment.big_withdrawal,
        "capacity.emergency_fund": assessment.emergency_fund,
        "capacity.income": assessment.income,
        "capacity.share_of_wealth": assessment.share_of_wealth,
        "derived.age": assessment.created_at.year - assessment.birth_year,
        "tolerance.portfolio": assessment.portfolio,
        "tolerance.drop": assessment.drop_reaction,
        "tolerance.max_loss": assessment.max_loss,
        "tolerance.goal": assessment.goal,
        "tolerance.experience": assessment.experience,
    }


def _option_key(value: Any) -> str:
    # Scorer option keys are strings, booleans are written "true" / "false"
    return str(value).lower() if isinstance(value, bool) else str(value)


def _factor_points(factor: dict, value: Any) -> int:
    if "options" in factor:
        return factor["options"][_option_key(value)]["points"]
    return next(r["points"] for r in factor["ranges"] if r["max"] is None or value <= r["max"])


def score_section(section: dict, answers: dict[str, Any]) -> tuple[int, list[dict]]:
    score, reasons = 0, []
    for factor in section["factors"]:
        value = answers[factor["field"]]
        points = _factor_points(factor, value)
        score += points
        reasons.append({factor["field"].split(".")[1]: value, "points": points})
    return score, reasons


def band_level(score: int) -> int:
    return max(b["level"] for b in load_scorer()["bands"] if score >= b["min_score"])


def matches(when: dict, answers: dict[str, Any]) -> bool:
    if "all" in when:
        return all(matches(w, answers) for w in when["all"])
    value = answers[when["field"]]
    if "eq" in when:
        return value == when["eq"]
    raise ValueError(f"Unknown scorer condition: {when}")


def compute_result(assessment: RiskAssessment) -> dict[str, Any]:
    """Score a submission, returns the assessment_results column values."""
    scorer = load_scorer()
    answers = answers_of(assessment)

    capacity_score, capacity_reasons = score_section(scorer["capacity"], answers)
    tolerance_score, tolerance_reasons = score_section(scorer["tolerance"], answers)
    capacity_level = band_level(capacity_score)
    tolerance_level = band_level(tolerance_score)

    caps = [
        cap for cap in scorer["caps"]
        if matches(cap["when"], answers)
    ]
    level = min([capacity_level, tolerance_level] + [cap["max_level"] for cap in caps])
    # Caps that pulled the level below both scores
    binding_caps = [
        cap["id"] for cap in caps
        if cap["max_level"] == level < min(capacity_level, tolerance_level)
    ]

    return {
        "level": level,
        "caps": binding_caps,
        "capacity_score": capacity_score,
        "capacity_level": capacity_level,
        "capacity_reasons": capacity_reasons,
        "tolerance_score": tolerance_score,
        "tolerance_level": tolerance_level,
        "tolerance_reasons": tolerance_reasons,
        "questionnaire_version": scorer["released"],
        "scoring_rules_version": scorer["version"],
    }

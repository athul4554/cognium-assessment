from datetime import datetime, timezone

import pytest

from app.models import RiskAssessment
from app.assessment.scoring import answers_of, band_level, compute_result, load_scorer, matches, profile_label


def make_assessment(**overrides) -> RiskAssessment:
    fields = {
        "birth_year": 1999,
        "horizon": "10_plus",
        "big_withdrawal": False,
        "emergency_fund": "6_plus_months",
        "income": "salaried",
        "share_of_wealth": "10_25",
        "portfolio": "B",
        "drop_reaction": "hold",
        "max_loss": "15",
        "goal": "balanced_growth",
        "experience": "stocks_etfs",
        "created_at": datetime(2026, 10, 17, tzinfo=timezone.utc),
    }
    return RiskAssessment(**(fields | overrides))


# Capacity and tolerance are scored separately

def test_capacity_score_and_reasons():
    result = compute_result(make_assessment())

    assert result["capacity_reasons"] == [
        {"horizon": "10_plus", "points": 25},
        {"big_withdrawal": False, "points": 15},
        {"emergency_fund": "6_plus_months", "points": 15},
        {"income": "salaried", "points": 15},
        {"share_of_wealth": "10_25", "points": 12},
        {"age": 27, "points": 15},
    ]
    assert result["capacity_score"] == 97
    assert result["capacity_level"] == 5


def test_tolerance_score_and_reasons():
    result = compute_result(make_assessment())

    assert result["tolerance_reasons"] == [
        {"drop": "hold", "points": 14},
        {"max_loss": "15", "points": 10},
        {"portfolio": "B", "points": 10},
        {"goal": "balanced_growth", "points": 10},
        {"experience": "stocks_etfs", "points": 12},
    ]
    assert result["tolerance_score"] == 56
    assert result["tolerance_level"] == 3


@pytest.mark.parametrize(
    "age, points",
    [(34, 15), (35, 13), (49, 13), (50, 9), (59, 9), (60, 5), (69, 5), (70, 2), (95, 2)],
)
def test_age_band_edges(age, points):
    result = compute_result(make_assessment(birth_year=2026 - age))

    assert result["capacity_reasons"][-1] == {"age": age, "points": points}


def test_best_answers_give_top_profile():
    result = compute_result(make_assessment(
        share_of_wealth="under_10", drop_reaction="buy_more", max_loss="30_plus",
        portfolio="C", goal="aggressive_growth", experience="derivatives_leverage",
    ))

    assert (result["capacity_score"], result["tolerance_score"]) == (100, 100)
    assert result["level"] == 5


def test_worst_answers_give_lowest_profile():
    result = compute_result(make_assessment(
        horizon="under_2", big_withdrawal=True, emergency_fund="none", income="none",
        share_of_wealth="over_50", drop_reaction="sell_all", max_loss="0",
        portfolio="A", goal="capital_preservation", experience="none",
    ))

    # Only age (27) scores on capacity, Portfolio A is the lowest tolerance option at 3
    assert (result["capacity_score"], result["tolerance_score"]) == (15, 3)
    assert result["level"] == 1


def test_unknown_answer_raises():
    with pytest.raises(KeyError):
        compute_result(make_assessment(horizon="forever"))


# Score -> one of the five profiles

@pytest.mark.parametrize(
    "score, level",
    [(0, 1), (19, 1), (20, 2), (39, 2), (40, 3), (59, 3), (60, 4), (79, 4), (80, 5), (100, 5)],
)
def test_band_boundaries(score, level):
    assert band_level(score) == level


@pytest.mark.parametrize(
    "level, label",
    [(1, "Conservative"), (2, "Moderately conservative"), (3, "Balanced"), (4, "Growth"), (5, "Aggressive")],
)
def test_profile_labels(level, label):
    assert profile_label(level) == label


# Combining: the more cautious side wins

def test_level_is_lowest_score_level_without_cap():
    result = compute_result(make_assessment())

    assert result["level"] == 3


# Some answers constrain the outcome on their own, against a base of capacity 5 / tolerance 3

@pytest.mark.parametrize(
    "overrides, level",
    [
        ({"horizon": "under_2"}, 1),
        ({"max_loss": "0"}, 1),
        ({"big_withdrawal": True}, 2),
        ({"emergency_fund": "none"}, 2),
        ({"drop_reaction": "sell_all"}, 2),
        ({"income": "none", "share_of_wealth": "over_50"}, 2),
        ({"experience": "none"}, 3),
    ],
)
def test_each_cap_alone(overrides, level):
    result = compute_result(make_assessment(**overrides))

    assert result["level"] == level


def test_combined_cap_needs_every_condition():
    result = compute_result(make_assessment(income="none"))

    assert result["capacity_level"] == 5
    assert result["level"] == 3


def test_unknown_cap_condition_raises():
    answers = answers_of(make_assessment())

    with pytest.raises(ValueError, match="Unknown scorer condition"):
        matches({"field": "capacity.horizon", "gt": "5_10"}, answers)


def test_lowest_cap_wins():
    result = compute_result(make_assessment(horizon="under_2", drop_reaction="sell_all"))

    assert result["level"] == 1


def test_binding_caps_are_returned():
    # big_withdrawal also matches but only the under 2 year horizon sets the level
    result = compute_result(make_assessment(horizon="under_2", big_withdrawal=True))

    assert result["caps"] == ["horizon_under_2"]


def test_no_caps_when_a_score_decides():
    # experience none caps at 3, the same as the tolerance level
    result = compute_result(make_assessment(experience="none"))

    assert result["caps"] == []


def test_high_capacity_low_tolerance():
    # Stable income, long horizon, big buffer, but sells everything at -20%
    result = compute_result(make_assessment(drop_reaction="sell_all"))

    assert result["capacity_level"] == 5
    assert result["level"] == 2


# The profile follows from the inputs: a better answer never gives a lower profile

SCORED_FIELDS = {
    "capacity.horizon": "horizon",
    "capacity.big_withdrawal": "big_withdrawal",
    "capacity.emergency_fund": "emergency_fund",
    "capacity.income": "income",
    "capacity.share_of_wealth": "share_of_wealth",
    "tolerance.drop": "drop_reaction",
    "tolerance.max_loss": "max_loss",
    "tolerance.portfolio": "portfolio",
    "tolerance.goal": "goal",
    "tolerance.experience": "experience",
}


@pytest.mark.parametrize("field", SCORED_FIELDS)
def test_better_answer_never_lowers_level(field):
    factor = next(
        f for section in ("capacity", "tolerance") for f in load_scorer()[section]["factors"] if f["field"] == field
    )
    ordered = sorted(factor["options"], key=lambda code: factor["options"][code]["points"])
    value = {"true": True, "false": False}

    levels = [
        compute_result(make_assessment(**{SCORED_FIELDS[field]: value.get(code, code)}))["level"]
        for code in ordered
    ]

    assert levels == sorted(levels)


# Record integrity: re-scoring an old assessment gives the same profile

def test_same_input_same_result():
    assert compute_result(make_assessment()) == compute_result(make_assessment())


def test_age_taken_at_submission_not_today():
    old = make_assessment(birth_year=1990, created_at=datetime(2020, 3, 1, tzinfo=timezone.utc))

    assert answers_of(old)["derived.age"] == 30
    assert compute_result(old)["capacity_reasons"][-1] == {"age": 30, "points": 15}


def test_versions_from_scorer():
    result = compute_result(make_assessment())

    assert result["questionnaire_version"] == "2026-10-01"
    assert result["scoring_rules_version"] == "1.0.0"

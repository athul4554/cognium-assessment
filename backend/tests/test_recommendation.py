from datetime import date
from decimal import Decimal
from itertools import combinations

import pytest

from app.recommendation.builder import (
    _amount, build_recommendation, eligible, group_weights, load_rules, load_universe, rank,
)

EXCLUSIONS = ["no_crypto", "sharia_compliant", "esg_preference"]
EXCLUSION_SETS = [list(c) for n in range(4) for c in combinations(EXCLUSIONS, n)]
LEVELS = [1, 2, 3, 4, 5]
FUNDS = {i["ticker"]: i for i in load_universe()["instruments"]}


def build(level=3, exclusions=(), invest="10000", monthly="500"):
    return build_recommendation(level, list(exclusions), Decimal(invest), Decimal(monthly))


def weights(rec) -> dict:
    return {h["ticker"]: h["weight"] for h in rec["holdings"]}


def equity_weight(rec) -> int:
    return sum(h["weight"] for h in rec["holdings"] if h["group"] == "equity")


# Profile -> target allocation

@pytest.mark.parametrize("level", LEVELS)
def test_allocation_sums_to_100(level):
    allocation = load_rules()["allocations"][str(level)]

    assert sum(allocation.values()) == 100
    assert set(allocation) <= set(load_rules()["sleeves"])


def test_equity_rises_with_level():
    equity = [equity_weight(build(level)) for level in LEVELS]

    assert equity == sorted(equity)
    assert equity == [15, 35, 55, 75, 87]


# Sleeves -> instruments from the universe

def test_level_3_picks():
    assert weights(build(3)) == {
        "IVV": 33, "SPDW": 15, "VWO": 7, "AGG": 15, "SPTI": 5, "STIP": 5,
        "VCIT": 7, "GLDM": 5, "SCHH": 3, "ICSH": 5,
    }


def test_rank_cheapest_first():
    funds = [
        {"ticker": "AAA", "expense_ratio_pct": 0.20, "inception_date": "2015-01-01"},
        {"ticker": "BBB", "expense_ratio_pct": 0.03, "inception_date": "2015-01-01"},
    ]

    assert rank(funds)["ticker"] == "BBB"


def test_rank_tie_picks_oldest():
    funds = [
        {"ticker": "AAA", "expense_ratio_pct": 0.03, "inception_date": "2018-01-01"},
        {"ticker": "BBB", "expense_ratio_pct": 0.03, "inception_date": "2010-01-01"},
    ]

    assert rank(funds)["ticker"] == "BBB"


def test_rank_full_tie_picks_ticker_order():
    funds = [
        {"ticker": "BBB", "expense_ratio_pct": 0.03, "inception_date": "2015-01-01"},
        {"ticker": "AAA", "expense_ratio_pct": 0.03, "inception_date": "2015-01-01"},
    ]

    assert rank(funds)["ticker"] == "AAA"


def test_eligible_matches_sleeve_and_category():
    funds = eligible("us_equity", [], load_universe())

    assert funds
    assert all(f["sleeve"] == "us_equity" and f["category"] == "Large Blend" for f in funds)


def test_never_picks_excluded_tickers_or_long_bonds():
    for level in LEVELS:
        for h in build(level)["holdings"]:
            assert h["ticker"] not in load_rules()["exclude_tickers"]
            assert "Long" not in h["category"]


# Exclusions are applied, at every level x every exclusion combination

@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("exclusions", EXCLUSION_SETS, ids=lambda e: "+".join(e) or "none")
def test_constraints_hold(level, exclusions):
    rec = build(level, exclusions)
    funds = [FUNDS[h["ticker"]] for h in rec["holdings"] if h["ticker"]]

    assert sum(h["weight"] for h in rec["holdings"]) == 100
    if "no_crypto" in exclusions:
        assert not any(f["crypto"] for f in funds)
    if "sharia_compliant" in exclusions:
        assert all(f["sharia_compliant"] for f in funds)
    # Exclusions never make the portfolio riskier than the profile
    assert equity_weight(rec) <= equity_weight(build(level))


def test_no_crypto_moves_crypto_to_cash():
    rec = build(5, ["no_crypto"])

    assert "BITB" not in weights(rec)
    assert weights(rec)["ICSH"] == 4


def test_sharia_level_3():
    rec = build(3, ["sharia_compliant"])

    assert weights(rec) == {"HLAL": 33, "SPWO": 22, "SPSK": 32, None: 10, "SPRE": 3}


def test_esg_swaps_funds_keeps_weights():
    plain, esg = build(3), build(3, ["esg_preference"])

    assert [h["weight"] for h in esg["holdings"]] == [h["weight"] for h in plain["holdings"]]
    assert {"ESGV", "ESGD", "ESGE", "EAGG", "SUSB"} <= set(weights(esg))
    assert "SPTI" in weights(esg)


# Notional amounts

def test_amounts_follow_weights():
    rec = build(5, ["no_crypto"], invest="10000", monthly="500")
    ivv = next(h for h in rec["holdings"] if h["ticker"] == "IVV")

    assert (ivv["amount"], ivv["monthly_amount"]) == (4900.0, 245.0)
    assert sum(h["amount"] for h in rec["holdings"]) == 10000


def test_amount_rounds_half_cent_up():
    assert _amount(Decimal("0.10"), 5) == 0.01


def test_zero_amounts():
    rec = build(3, invest="0", monthly="0")

    assert all(h["amount"] == 0 and h["monthly_amount"] == 0 for h in rec["holdings"])


def test_uninvested_line_is_empty():
    rec = build(3, ["sharia_compliant"])
    line = next(h for h in rec["holdings"] if h["ticker"] is None)

    assert (line["provider"], line["category"]) == (None, None)
    assert (line["esg"], line["sharia_compliant"]) == (False, False)
    assert line["name"] == load_rules()["messages"]["uninvested_cash"]


# Group totals

def holding(group, weight, amount, monthly):
    return {"group": group, "weight": weight, "amount": amount, "monthly_amount": monthly}


def test_group_weights_sum_members():
    holdings = [
        holding("equity", 30, 3000.0, 150.0),
        holding("equity", 20, 2000.0, 100.0),
        holding("cash", 50, 5000.0, 250.0),
    ]

    assert group_weights(holdings) == [
        {"group": "equity", "weight": 50, "amount": 5000.0, "monthly_amount": 250.0},
        {"group": "cash", "weight": 50, "amount": 5000.0, "monthly_amount": 250.0},
    ]


def test_group_weights_follow_rules_order_and_skip_empty():
    holdings = [holding("cash", 40, 0.0, 0.0), holding("gold", 10, 0.0, 0.0), holding("equity", 50, 0.0, 0.0)]

    assert [g["group"] for g in group_weights(holdings)] == ["equity", "gold", "cash"]


# Record integrity: same inputs always build the same portfolio

@pytest.mark.parametrize("level", LEVELS)
def test_same_input_same_output(level):
    assert build(level, EXCLUSIONS) == build(level, EXCLUSIONS)


def test_versions_recorded():
    rec = build()

    assert rec["rules_version"] == "1.0.0"
    assert rec["universe_as_of"] == date(2026, 9, 16)

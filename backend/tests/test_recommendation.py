import copy
from datetime import date
from decimal import Decimal

import pandas as pd
import pytest

from app.recommendation import builder
from app.recommendation.builder import (
    _amount, build_recommendation, choose_weights, eligible, group_weights, load_rules, load_universe,
    mix_metrics, pick_funds, score,
)
from app.constants import UNINVESTED_CASH
from app.recommendation.market_data import load_snapshot

LEVELS = [1, 2, 3, 4, 5]
EXCLUSIONS = [[], ["no_crypto"], ["sharia_compliant"], ["esg_preference"], ["no_crypto", "sharia_compliant", "esg_preference"]]
FUNDS = {i["ticker"]: i for i in load_universe()["instruments"]}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    # No yfinance in tests: every mix is measured on the snapshot
    monkeypatch.setattr(builder, "get_daily_returns", lambda tickers: None)


def build(level=3, exclusions=(), invest="10000", monthly="500"):
    return build_recommendation(level, list(exclusions), Decimal(invest), Decimal(monthly))


def weights(rec) -> dict:
    return {h["ticker"]: h["weight"] for h in rec["holdings"]}


def bucket_weights(rec) -> dict:
    out = {}
    for h in rec["holdings"]:
        out[h["sleeve"]] = out.get(h["sleeve"], 0) + h["weight"]
    return out


def picks_of(level, exclusions=()) -> dict:
    return {
        b: pick_funds(eligible(b, list(exclusions), load_universe()), level, cfg["picks"])
        for b, cfg in load_rules()["buckets"].items()
    }


def returns(**series) -> pd.DataFrame:
    return pd.DataFrame(series, index=pd.bdate_range("2023-01-02", periods=len(next(iter(series.values())))))


# Rules

@pytest.mark.parametrize("level", LEVELS)
def test_ranges_can_sum_to_100(level):
    ranges = load_rules()["ranges"][str(level)]

    assert set(ranges) == set(load_rules()["buckets"])
    assert sum(lo for lo, _ in ranges.values()) <= 100 <= sum(hi for _, hi in ranges.values())


# Funds: score per level

def test_score():
    s = load_snapshot()["SPMO"]

    assert score({"ticker": "SPMO"}, 1) == s["return_3y_annualised_pct"] - 4 * abs(s["max_drawdown_3y_pct"])


def test_low_level_picks_less_drawdown_high_level_more_return():
    snap = load_snapshot()
    avg = lambda funds, key: sum(abs(snap[f["ticker"]][key]) for f in funds) / len(funds)
    l1, l5 = picks_of(1)["us_equity"], picks_of(5)["us_equity"]

    assert [f["ticker"] for f in l1] == ["HDV", "USMV"]
    assert [f["ticker"] for f in l5] == ["SPMO", "VLUE"]
    assert avg(l1, "max_drawdown_3y_pct") < avg(l5, "max_drawdown_3y_pct")
    assert avg(l1, "return_3y_annualised_pct") < avg(l5, "return_3y_annualised_pct")


@pytest.mark.parametrize("level", LEVELS)
def test_bucket_picks_have_different_categories(level):
    for funds in picks_of(level).values():
        categories = [f["category"] for f in funds]
        assert len(categories) == len(set(categories))


def test_eligible_rules():
    as_of = date.fromisoformat(load_universe()["as_of"])
    for bucket in load_rules()["buckets"]:
        for f in eligible(bucket, [], load_universe()):
            assert date.fromisoformat(f["inception_date"]) <= as_of.replace(year=as_of.year - 3)
            assert f["region"] in load_rules()["regions"]
            assert not (f["sharia_compliant"] or f["esg"])
            assert f["ticker"] not in load_rules()["exclude_tickers"]
            assert not f["crypto"] or bucket == "crypto"


def test_only_gbtc_is_eligible_crypto():
    assert [f["ticker"] for f in eligible("crypto", [], load_universe())] == ["GBTC"]


def test_young_and_single_country_funds_never_picked():
    tickers = {h["ticker"] for level in LEVELS for h in build(level)["holdings"]}

    assert not tickers & {"IBIT", "SPWO", "SPTE", "EWY", "EWT", "EWJ", "INDA"}


# Weights: highest return inside the ranges and limits

@pytest.mark.parametrize("level", LEVELS)
def test_weights_inside_ranges_and_sum_to_100(level):
    rec = build(level)
    ranges = load_rules()["ranges"][str(level)]

    assert sum(h["weight"] for h in rec["holdings"]) == 100
    for bucket, weight in bucket_weights(rec).items():
        lo, hi = ranges[bucket]
        assert lo <= weight <= hi and weight % 5 == 0


@pytest.mark.parametrize("level", LEVELS)
def test_portfolio_inside_limits(level):
    portfolio = build(level)["portfolio"]
    limit = load_rules()["limits"][str(level)]

    assert portfolio["max_drawdown_pct"] <= limit["max_drawdown"]
    assert portfolio["volatility_pct"] <= limit["max_volatility"]
    assert portfolio["source"] == "snapshot"


def test_return_rises_with_level():
    returns_ = [build(level)["portfolio"]["expected_return_pct"] for level in LEVELS]

    assert returns_ == sorted(returns_)


def test_level_3_snapshot_portfolio():
    rec = build(3)

    assert weights(rec) == {
        "SPMO": 17.5, "VLUE": 17.5, "IDV": 10, "EFAV": 10, "SPSB": 12.5, "STIP": 12.5,
        "MINT": 15, "GLDM": 2.5, "XLRE": 2.5,
    }
    assert rec["portfolio"] == {
        "expected_return_pct": 18.9, "volatility_pct": 11.7, "max_drawdown_pct": 10.0, "source": "snapshot",
    }


def test_no_mix_fits_takes_lowest_drawdown(monkeypatch):
    rules = copy.deepcopy(load_rules())
    rules["limits"]["3"] = {"max_drawdown": 0, "max_volatility": 0}
    monkeypatch.setattr(builder, "load_rules", lambda: rules)

    _, fallback = choose_weights(3, picks_of(3), None)
    rules["limits"]["3"] = {"max_drawdown": 100, "max_volatility": 100}
    _, unlimited = choose_weights(3, picks_of(3), None)

    assert fallback["max_drawdown_pct"] < unlimited["max_drawdown_pct"]


# Exclusions

@pytest.mark.parametrize("level", LEVELS)
@pytest.mark.parametrize("exclusions", EXCLUSIONS, ids=lambda e: "+".join(e) or "none")
def test_exclusions_hold(level, exclusions):
    rec = build(level, exclusions)
    funds = [FUNDS[h["ticker"]] for h in rec["holdings"] if h["ticker"]]

    assert sum(h["weight"] for h in rec["holdings"]) == 100
    assert rec["portfolio"]["volatility_pct"] <= load_rules()["limits"][str(level)]["max_volatility"]
    if "no_crypto" in exclusions:
        assert not any(f["crypto"] for f in funds)
    if "sharia_compliant" in exclusions:
        assert all(f["sharia_compliant"] for f in funds)
    else:
        assert not any(f["sharia_compliant"] for f in funds)


def test_no_crypto_at_level_5():
    assert "GBTC" not in weights(build(5, ["no_crypto"]))
    assert eligible("crypto", ["no_crypto"], load_universe()) == []


def test_esg_preference_uses_esg_funds_where_they_exist():
    picks = picks_of(3, ["esg_preference"])

    assert all(f["esg"] for b in ("us_equity", "intl_equity", "bonds") for f in picks[b])
    # No ESG cash fund, so cash keeps the normal funds
    assert picks["cash"] and not any(f["esg"] for f in picks["cash"])


def test_no_esg_funds_without_preference():
    assert not any(f["esg"] for level in LEVELS for f in sum(picks_of(level).values(), []))


def test_sharia_level_3():
    rec = build(3, ["sharia_compliant"])

    assert weights(rec) == {"SPUS": 20, "HLAL": 20, "SPRE": 15, None: 45}


def test_uninvested_line_is_empty():
    line = next(h for h in build(3, ["sharia_compliant"])["holdings"] if h["ticker"] is None)

    assert (line["name"], line["sleeve_label"], line["group"]) == (UNINVESTED_CASH, UNINVESTED_CASH, "cash")
    assert (line["provider"], line["category"], line["expense_ratio_pct"]) == (None, None, None)
    assert (line["esg"], line["sharia_compliant"]) == (False, False)


def test_uninvested_weight_adds_no_return_or_risk():
    # SPMO 40%, the other 60% has no fund
    s = load_snapshot()["SPMO"]

    ret, vol, dd = mix_metrics({"SPMO": 40}, None)

    assert (ret, vol, dd) == pytest.approx(
        (0.4 * s["return_3y_annualised_pct"], 0.4 * s["volatility_1y_pct"], 0.4 * abs(s["max_drawdown_3y_pct"]))
    )


# Measuring a mix on daily prices

def test_opposite_funds_cancel_out():
    up_down = [0.01, -0.01] * 200
    r = returns(AAA=up_down, BBB=[-x for x in up_down])

    ret, vol, dd = mix_metrics({"AAA": 50, "BBB": 50}, r)

    assert (round(ret, 6), round(vol, 6), round(dd, 6)) == (0, 0, 0)
    assert mix_metrics({"AAA": 100}, r)[1] > 10


def test_mix_drawdown_and_return():
    # Falls 50%, then doubles back to where it started
    r = returns(AAA=[0.0] * 100 + [-0.5] + [0.0] * 100 + [1.0] + [0.0] * 50)

    ret, _, dd = mix_metrics({"AAA": 100}, r)

    assert round(dd, 6) == 50
    assert round(ret, 6) == 0


def test_live_prices_mark_source_live():
    tickers = [f["ticker"] for funds in picks_of(3).values() for f in funds]
    r = returns(**{t: [0.001] * 300 for t in tickers})

    _, portfolio = choose_weights(3, picks_of(3), r)

    assert portfolio["source"] == "live"


# Notional amounts

def test_amounts_follow_weights():
    rec = build(3, invest="10000", monthly="500")
    spmo = next(h for h in rec["holdings"] if h["ticker"] == "SPMO")

    assert (spmo["amount"], spmo["monthly_amount"]) == (1750.0, 87.5)
    assert sum(h["amount"] for h in rec["holdings"]) == 10000


def test_amount_rounds_half_cent_up():
    assert _amount(Decimal("0.10"), 5) == 0.01
    assert _amount(Decimal("0.10"), 2.5) == 0.0


def test_zero_amounts():
    rec = build(3, invest="0", monthly="0")

    assert all(h["amount"] == 0 and h["monthly_amount"] == 0 for h in rec["holdings"])


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


def test_holding_keeps_sleeve_group():
    groups = {h["ticker"]: h["group"] for h in build(3)["holdings"]}

    assert (groups["GLDM"], groups["XLRE"]) == ("gold", "real_estate")


# Record integrity: same inputs always build the same portfolio

@pytest.mark.parametrize("level", LEVELS)
def test_same_input_same_output(level):
    assert build(level) == build(level)


def test_versions_recorded():
    rec = build()

    assert rec["rules_version"] == "1.2.0"
    assert rec["universe_as_of"] == date(2026, 9, 16)

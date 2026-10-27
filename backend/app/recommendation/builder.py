import json
from datetime import date
from decimal import ROUND_FLOOR, ROUND_HALF_UP, Decimal
from functools import lru_cache
from typing import Any

from ..constants import CASH_TICKER, RECOMMENDER_PATH, UNINVESTED_CASH, UNIVERSE_PATH
from .market_data import get_metrics, get_price_history
from .search import cash_result, choose_weights

@lru_cache
def load_rules() -> dict[str, Any]:
    with open(RECOMMENDER_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_universe() -> dict[str, Any]:
    with open(UNIVERSE_PATH, encoding="utf-8") as f:
        return json.load(f)


def eligible(bucket: str, exclusions: list[str], universe: dict) -> list[dict]:
    rules = load_rules()
    as_of = date.fromisoformat(universe["as_of"])
    oldest = as_of.replace(year=as_of.year - rules["min_age_years"])
    cfg = rules["buckets"][bucket]
    sharia = "sharia_compliant" in exclusions
    esg = "esg_preference" in exclusions
    crypto = cfg.get("crypto", False) and "no_crypto" not in exclusions

    funds = [
        i for i in universe["instruments"]
        if i["sleeve"] in cfg["sleeves"]
        and i["ticker"] not in rules["exclude_tickers"]
        and date.fromisoformat(i["inception_date"]) <= oldest
        and i["currency"] == rules["history"]["currency"]
        and i["region"] in rules["regions"]
        # Sharia funds only for sharia clients, and only sharia funds for them
        and i["sharia_compliant"] == sharia
        and (not i["esg"] or esg)
        and (not i["crypto"] or crypto)
    ]

    # ESG is a preference: keep only ESG funds when the bucket has any
    if esg:
        return [i for i in funds if i["esg"]] or funds
    return funds


def allocate_amounts(holdings, total, field):
    """Distribute remaining cents so displayed amounts sum to the input total."""
    exact = [total * Decimal(str(h['weight'])) for h in holdings]  # cents
    cents = [int(value.to_integral_value(rounding=ROUND_FLOOR)) for value in exact]
    remainder = int((total * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)) - sum(cents)
    for i in sorted(range(len(holdings)), key=lambda i: exact[i] - cents[i], reverse=True)[:remainder]:
        cents[i] += 1
    for h, value in zip(holdings, cents):
        h[field] = float(Decimal(value) / 100)


def build_recommendation(
    level: int,
    exclusions: list[str],
    invest_amount: Decimal,
    monthly_amount: Decimal,
    max_loss: str | None = None,
) -> dict[str, Any]:

    rules = load_rules()
    universe = load_universe()

    candidates = {
        bucket: eligible(bucket, exclusions, universe)
        for bucket in rules["buckets"]
    }
    tickers = sorted({f["ticker"] for funds in candidates.values() for f in funds})
    prices = None
    history = rules["history"]
    if max_loss == "0":
        weights, portfolio = cash_result(level, rules, "zero_loss")
    elif not tickers:
        weights, portfolio = cash_result(level, rules, "no_funds")
    else:
        prices = get_price_history(tickers, min_days=history["min_days"])
        returns = prices.pct_change(fill_method=None).iloc[1:] if prices is not None else None
        weights, portfolio = choose_weights(level, candidates, returns, rules)
        portfolio["excluded_tickers"] = sorted(set(tickers) - (set(returns.columns) if returns is not None else set()))

    selected = [t for t in weights if t != CASH_TICKER]
    metrics = get_metrics(prices[selected] if prices is not None else None)
    holdings = []
    for bucket, funds in candidates.items():
        for fund in funds:
            weight = weights.get(fund["ticker"], 0)
            if not weight:
                continue
            holdings.append({
                "sleeve": bucket,
                "sleeve_label": rules["buckets"][bucket]["label"],
                "group": rules["sleeve_groups"][fund["sleeve"]],
                "weight": weight,
                "metrics": metrics.get(fund["ticker"]),
                **{key: fund[key] for key in (
                    "ticker", "name", "provider", "category", "expense_ratio_pct",
                    "distribution_yield_pct", "inception_date", "esg", "sharia_compliant",
                )},
            })

    if weights.get(CASH_TICKER, 0) > 0:
        holdings.append({
            "sleeve": "cash", "sleeve_label": UNINVESTED_CASH, "group": "cash",
            "weight": weights[CASH_TICKER], "ticker": None, "name": UNINVESTED_CASH,
            "provider": None, "category": None, "expense_ratio_pct": None,
            "distribution_yield_pct": None, "inception_date": None,
            "esg": False, "sharia_compliant": False, "metrics": None,
        })
    allocate_amounts(holdings, invest_amount, "amount")
    allocate_amounts(holdings, monthly_amount, "monthly_amount")

    return {
        "holdings": holdings,
        "portfolio": portfolio,
        "rules_version": rules["version"],
        "universe_as_of": date.fromisoformat(universe["as_of"]),
    }


def group_weights(holdings: list[dict]) -> list[dict]:
    groups = []
    for group in load_rules()["groups"]:
        members = [h for h in holdings if h["group"] == group]
        if members:
            groups.append({
                "group": group,
                "weight": sum(h["weight"] for h in members),
                "amount": round(sum(h["amount"] for h in members), 2),
                "monthly_amount": round(sum(h["monthly_amount"] for h in members), 2),
            })
    return groups

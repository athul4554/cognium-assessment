import json
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from typing import Any

from ..constants import RECOMMENDER_PATH, UNIVERSE_PATH

CENT = Decimal("0.01")
UNINVESTED = "uninvested"


@lru_cache
def load_rules() -> dict[str, Any]:
    with open(RECOMMENDER_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_universe() -> dict[str, Any]:
    with open(UNIVERSE_PATH, encoding="utf-8") as f:
        return json.load(f)


def eligible(sleeve: str, exclusions: list[str], universe: dict) -> list[dict]:
    rules = load_rules()
    categories = rules["sleeves"][sleeve]["categories"]

    funds = [
        i for i in universe["instruments"]
        if i["sleeve"] == sleeve
        and i["category"] in categories
        and i["ticker"] not in rules["exclude_tickers"]
    ]

    if "no_crypto" in exclusions:
        funds = [i for i in funds if not i["crypto"]]
    if "sharia_compliant" in exclusions:
        funds = [i for i in funds if i["sharia_compliant"]]
    return funds


def rank(funds: list[dict]) -> dict:
    return min(funds, key=lambda i: (i["expense_ratio_pct"], i["inception_date"], i["ticker"]))


def _resolve(sleeve: str, exclusions: list[str], universe: dict) -> tuple[str, list[dict]]:
    rules = load_rules()["sleeves"]
    funds = eligible(sleeve, exclusions, universe)
    if funds:
        return sleeve, funds

    fallback = rules[sleeve].get("fallback")
    if fallback:
        funds = eligible(fallback, exclusions, universe)
        if funds:
            return fallback, funds
    funds = eligible("cash", exclusions, universe)
    return "cash", funds


def _amount(total: Decimal, weight: int) -> float:
    return float((total * weight / 100).quantize(CENT, rounding=ROUND_HALF_UP))


def build_recommendation(
    level: int,
    exclusions: list[str],
    invest_amount: Decimal,
    monthly_amount: Decimal,
) -> dict[str, Any]:

    rules = load_rules()
    universe = load_universe()
    sleeves = rules["sleeves"]
    messages = rules["messages"]

    lines: dict[str, dict] = {}

    for sleeve, weight in rules["allocations"][str(level)].items():
        target, funds = _resolve(sleeve, exclusions, universe)

        if "esg_preference" in exclusions and funds:
            esg_funds = [i for i in funds if i["esg"]]
            if esg_funds:
                funds = esg_funds

        fund = rank(funds) if funds else None
        key = fund["ticker"] if fund else UNINVESTED

        if key in lines:
            lines[key]["weight"] += weight
            continue

        lines[key] = {
            "sleeve": target,
            "sleeve_label": sleeves[target]["label"] if fund else messages["uninvested_cash"],
            "group": sleeves[target]["group"],
            "weight": weight,
            "ticker": fund["ticker"] if fund else None,
            "name": fund["name"] if fund else messages["uninvested_cash"],
            "provider": fund["provider"] if fund else None,
            "category": fund["category"] if fund else None,
            "expense_ratio_pct": fund["expense_ratio_pct"] if fund else None,
            "distribution_yield_pct": fund["distribution_yield_pct"] if fund else None,
            "inception_date": fund["inception_date"] if fund else None,
            "esg": fund["esg"] if fund else False,
            "sharia_compliant": fund["sharia_compliant"] if fund else False,
        }

    holdings = list(lines.values())
    for h in holdings:
        h["amount"] = _amount(invest_amount, h["weight"])
        h["monthly_amount"] = _amount(monthly_amount, h["weight"])

    return {
        "holdings": holdings,
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

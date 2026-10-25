import json
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from itertools import product
from typing import Any

import numpy as np

from ..constants import RECOMMENDER_PATH, TRADING_DAYS_PER_YEAR, UNINVESTED_CASH, UNIVERSE_PATH
from .market_data import get_daily_returns, load_snapshot

CENT = Decimal("0.01")


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
    snapshot = load_snapshot()
    cfg = rules["buckets"][bucket]
    sharia = "sharia_compliant" in exclusions
    esg = "esg_preference" in exclusions
    crypto = cfg.get("crypto", False) and "no_crypto" not in exclusions

    funds = [
        i for i in universe["instruments"]
        if i["sleeve"] in cfg["sleeves"]
        and i["ticker"] not in rules["exclude_tickers"]
        and date.fromisoformat(i["inception_date"]) <= oldest
        and snapshot.get(i["ticker"], {}).get("return_3y_annualised_pct") is not None
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


def score(fund: dict, level: int) -> float:
    s = load_snapshot()[fund["ticker"]]
    penalty = load_rules()["drawdown_penalty"][str(level)]
    return s["return_3y_annualised_pct"] - penalty * abs(s["max_drawdown_3y_pct"])


def pick_funds(funds: list[dict], level: int, n: int) -> list[dict]:
    picks, seen = [], set()
    for f in sorted(funds, key=lambda f: -score(f, level)):
        if f["category"] in seen:
            continue
        picks.append(f)
        seen.add(f["category"])
        if len(picks) == n:
            break
    return picks


def mix_metrics(weights: dict[str, float], returns) -> tuple[float, float, float]:
    """Return, volatility and |max drawdown| of the mix in %. Snapshot weighted average without prices."""
    if returns is None:
        s = load_snapshot()
        return (
            sum(w / 100 * s[t]["return_3y_annualised_pct"] for t, w in weights.items()),
            sum(w / 100 * s[t]["volatility_1y_pct"] for t, w in weights.items()),
            sum(w / 100 * abs(s[t]["max_drawdown_3y_pct"]) for t, w in weights.items()),
        )

    days = TRADING_DAYS_PER_YEAR
    port = returns[list(weights)].to_numpy() @ np.array(list(weights.values())) / 100
    nav = np.cumprod(1 + port)
    ret = nav[-1] ** (days / len(port)) - 1
    vol = port[-days:].std() * np.sqrt(days)
    dd = abs((nav / np.maximum.accumulate(nav) - 1).min())
    return ret * 100, vol * 100, dd * 100


def choose_weights(level: int, picks: dict[str, list[dict]], returns) -> tuple[dict[str, int], dict[str, Any]]:
    """Highest-return bucket weights inside the level's ranges and risk limits."""
    rules = load_rules()
    ranges, limit, step = rules["ranges"][str(level)], rules["limits"][str(level)], rules["weight_step"]
    # A bucket with no picks is held as uninvested cash, its weight adds 0 return and 0 risk
    buckets = list(ranges)

    best = safest = None
    for w in product(*(range(ranges[b][0], ranges[b][1] + 1, step) for b in buckets)):
        if sum(w) != 100:
            continue
        funds = {f["ticker"]: wb / len(picks[b]) for wb, b in zip(w, buckets) for f in picks[b]}
        ret, vol, dd = mix_metrics(funds, returns)
        if safest is None or dd < safest[2]:
            safest = (ret, vol, dd, w)
        if dd <= limit["max_drawdown"] and vol <= limit["max_volatility"] and (best is None or ret > best[0]):
            best = (ret, vol, dd, w)

    # No mix fits the limits: fall back to the lowest-drawdown mix
    ret, vol, dd, w = best or safest
    return dict(zip(buckets, w)), {
        "expected_return_pct": round(float(ret), 1),
        "volatility_pct": round(float(vol), 1),
        "max_drawdown_pct": round(float(dd), 1),
        "source": "snapshot" if returns is None else "live",
    }


def _amount(total: Decimal, weight: float) -> float:
    return float((total * Decimal(str(weight)) / 100).quantize(CENT, rounding=ROUND_HALF_UP))


def build_recommendation(
    level: int,
    exclusions: list[str],
    invest_amount: Decimal,
    monthly_amount: Decimal,
) -> dict[str, Any]:

    rules = load_rules()
    universe = load_universe()

    picks = {
        bucket: pick_funds(eligible(bucket, exclusions, universe), level, cfg["picks"])
        for bucket, cfg in rules["buckets"].items()
    }
    returns = get_daily_returns([f["ticker"] for funds in picks.values() for f in funds])
    weights, portfolio = choose_weights(level, picks, returns)

    holdings = []
    uninvested = 0
    for bucket, weight in weights.items():
        if not weight:
            continue
        cfg = rules["buckets"][bucket]
        if not picks[bucket]:
            uninvested += weight
            continue

        for fund in picks[bucket]:
            holdings.append({
                "sleeve": bucket,
                "sleeve_label": cfg["label"],
                "group": rules["sleeve_groups"][fund["sleeve"]],
                "weight": weight / len(picks[bucket]),
                "ticker": fund["ticker"],
                "name": fund["name"],
                "provider": fund["provider"],
                "category": fund["category"],
                "expense_ratio_pct": fund["expense_ratio_pct"],
                "distribution_yield_pct": fund["distribution_yield_pct"],
                "inception_date": fund["inception_date"],
                "esg": fund["esg"],
                "sharia_compliant": fund["sharia_compliant"],
            })

    if uninvested:
        holdings.append({
            "sleeve": "cash",
            "sleeve_label": UNINVESTED_CASH,
            "group": "cash",
            "weight": uninvested,
            "ticker": None,
            "name": UNINVESTED_CASH,
            "provider": None,
            "category": None,
            "expense_ratio_pct": None,
            "distribution_yield_pct": None,
            "inception_date": None,
            "esg": False,
            "sharia_compliant": False,
        })

    for h in holdings:
        h["amount"] = _amount(invest_amount, h["weight"])
        h["monthly_amount"] = _amount(monthly_amount, h["weight"])

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

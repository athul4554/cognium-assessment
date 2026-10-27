#### Portfolio Recommendation - API

Historical design for v1.2.0. See [ARCHITECTURE.md](ARCHITECTURE.md) for the current allocation and market-data flow.

- builds on the locked result from [assessment plan](../assessment/plan.md). Scoring gives us a level, this turns it into real funds with amounts and market data
- code lives in [router.py](router.py), [builder.py](builder.py) and [market_data.py](market_data.py)
- rules in [rules/v1.2.0.json](rules/v1.2.0.json), funds in [universe.json](universe.json), fund metrics in [snapshot.json](snapshot.json)
  - v1.0.0 and v1.1.0 stay so older recommendations still point to a real rules file

### Libraries used

- fastapi
- pydantic (validation)
- sqlalchemy + postgres
- alembic (migrations)
- yfinance (live prices)
- numpy (portfolio maths)

## Problem

- maximise return within the client's risk limits (drawdown, volatility)
- balanced comes from combining high-risk stocks with low-risk bonds, not from middle-of-the-road funds
- choices are driven by Yahoo Finance data (returns, drawdown, volatility)

## What it uses

- level (1 to 5) from the saved result - picks the funds, the risk limits and the weight ranges
  - only the level, never the raw answers. The scorer already took the lowest of capacity, tolerance and caps, reading the answers again could undo a cap
- invest_amount, monthly_amount - turned into an amount per fund
- currency - copied onto the recommendation, every fund is priced in USD anyway
- exclusions - decide which funds are allowed (see Exclusions), they don't change the score, limits or ranges
- notes, max_loss - not used

## Flow

1. pick funds per bucket - score rule, on [snapshot.json](snapshot.json)
2. download 3y of daily prices for the picks from yfinance (one call)
3. try every bucket weight mix in 5% steps inside the level's ranges, summing to 100
4. measure each mix on the combined daily series (correlation included)
5. drop mixes over the level's max drawdown or max volatility
6. keep the highest return
7. no mix fits - take the lowest-drawdown mix

## Buckets

| bucket               | sleeves                                                                |
| -------------------- | ---------------------------------------------------------------------- |
| US equity            | `us_equity`                                                            |
| International equity | `intl_developed_equity`, `em_equity`                                   |
| Bonds                | `aggregate_bonds`, `treasuries`, `corporate_bonds`, `inflation_linked` |
| Cash                 | `cash`                                                                 |
| Gold / real assets   | `gold`, `real_estate`                                                  |
| Crypto               | `crypto` (level 5 only)                                                |

- not used - `sector_equity`, `global_equity`, `high_yield`, `municipal_bonds`, `em_bonds`, `commodities`, `multi_asset`, `alternatives`, `sukuk`
- each holding keeps its sleeve's group (equity, fixed_income, real_estate, gold, crypto, cash) for the donut / bars

## Fund eligibility

- at least 3 years old - `as_of − inception_date ≥ 3 years` (checked on the date, some younger funds still have a 3y return)
- `return_3y_annualised_pct` is not null
- not single-country - `region` is one of `us`, `developed_ex_us`, `europe`, `asia_pacific`, `emerging`, `global_ex_us`, `global`
- `sharia_compliant` is false (true for sharia clients, see Exclusions)
- `esg` is false, unless the client prefers ESG
- `crypto` is false, except in the Crypto bucket (and never with `no_crypto`)
- not in `exclude_tickers`
  - BITO - bitcoin futures fund, the "yield" is futures roll, not income
  - BLOK - blockchain company shares, not crypto
- so the Crypto bucket only has GBTC - the spot bitcoin ETFs (IBIT, FBTC, ARKB, BITB) launched in Jan 2024 and are under 3 years old, ETHA has no 3y return

## Exclusions

- applied in eligibility, before the score. The score, risk limits, ranges and optimiser are unchanged
- `no_crypto` - no crypto funds, the Crypto bucket is empty
- `sharia_compliant` - only sharia funds. Eligible ones are SPUS, HLAL (US equity) and SPRE (property), International, Bonds, Cash and Crypto have none
- `esg_preference` - ESG funds are allowed, and a bucket keeps only its ESG funds when it has any (US equity, International, Bonds). Cash and Gold / real assets have none, so they keep the normal funds. It's a preference, not a filter
- no exclusions - sharia and ESG funds are left out, same funds as before
- a bucket with no eligible fund still takes part in the weight search, its weight is held as uninvested cash
  - counts as 0 return and 0 risk when measuring a mix
  - shows as one `Cash (held uninvested)` line, `ticker: null`, `metrics: null`, group `cash`
  - sharia L3 - SPUS 20, HLAL 20, SPRE 15, uninvested cash 45
  - `no_crypto` at L5 - the crypto slot (0–5%) can become uninvested cash, since it's calmer than GBTC

## Picking funds - score per level

```
score = return_3y_annualised_pct − drawdown_penalty[level] × |max_drawdown_3y_pct|
```

- the penalty is how much return 1% of drawdown is worth to the level
- whole bucket ranked by score, top 2 with different `category` (1 for Cash and Crypto), so near-identical funds (VOO + IVV) aren't picked together
- low levels - big penalty, best-returning low-drawdown funds
- high levels - tiny penalty, highest return wins, drawdown only breaks close calls
- a lower penalty never picks a lower-return fund, so a higher level never gets less return in a bucket
- levels can share funds (a fund with high return and moderate drawdown wins at several levels) - balance comes from the bucket weights
- only compared inside one bucket, a bond fund never competes with a stock fund

| level | drawdown_penalty |
| ----- | ---------------- |
| 1     | 4                |
| 2     | 2.5              |
| 3     | 1.5              |
| 4     | 0.75             |
| 5     | 0.1              |

- calibrated on the snapshot - below ~2, L1 picks the same high-return funds as L5 (SPMO, VLUE). At 4 it gets HDV + USMV (~14% return, ~10% drawdown). Above ~6 it drifts to the safest funds (SPLV, 8.5% return) for almost no extra safety
- example (US equity)
  - SPMO - 35.5% return, 20.1% drawdown → L1 35.5 − 4 × 20.1 = −45.0, L5 35.5 − 0.1 × 20.1 = 33.5
  - HDV - 16.4% return, 10.5% drawdown → L1 16.4 − 4 × 10.5 = −25.6, L5 16.4 − 0.1 × 10.5 = 15.3
  - L1 gets HDV (fell half as much), L5 gets SPMO (returned twice as much)

## Risk limits per level (hard)

| level | max drawdown | max volatility |
| ----- | ------------ | -------------- |
| 1     | 10%          | 6%             |
| 2     | 15%          | 9%             |
| 3     | 22%          | 12%            |
| 4     | 28%          | 15%            |
| 5     | 35%          | 18%            |

## Bucket weight ranges (%)

| bucket               | L1    | L2    | L3    | L4    | L5    |
| -------------------- | ----- | ----- | ----- | ----- | ----- |
| US equity            | 5–20  | 10–30 | 20–40 | 30–50 | 40–60 |
| International equity | 0–10  | 5–15  | 5–20  | 10–25 | 15–30 |
| Bonds                | 30–70 | 25–60 | 20–45 | 10–35 | 0–20  |
| Cash                 | 10–40 | 5–25  | 0–15  | 0–10  | 0–5   |
| Gold / real assets   | 0–10  | 0–10  | 5–15  | 5–15  | 5–15  |
| Crypto               | 0     | 0     | 0     | 0     | 0–5   |

- step 5%, weights sum to 100
- a bucket's weight is split equally between its picks (weights can be decimals, e.g. 17.5)
- why ranges - without them the optimiser exploits the numbers (L3 went 100% international equity, L1 had no bonds). Ranges force a real mix and keep each level true to its label
- crypto at L5 only goes in if the mix still fits the limits (GBTC volatility is ~45%)

## Measuring a mix

- daily portfolio return = Σ weight_i × daily return_i (rebalanced to target every day)
- return - annualised growth over the 3 years
- volatility - std of the last year's daily returns × √252
- max drawdown - worst fall from a peak over the 3 years
- stocks and bonds don't fall on the same days, so the combined risk is lower than the weighted average of each fund's risk (L3 mix - 9.2% vol / 7.3% drawdown combined vs 11.7% / 10.0% averaged)
- yfinance fails (or a pick has a year or less of prices) - each mix is measured as the weighted average of the snapshot numbers instead, `source: "snapshot"`

## Result per level (live prices, 2026-10-24)

| level | mix (US / Intl / Bonds / Cash / Gold & real / Crypto) | return | volatility | max drawdown |
| ----- | ----------------------------------------------------- | ------ | ---------- | ------------ |
| 1     | 20 / 10 / 50 / 10 / 10 / 0                            | 10.0%  | 3.9%       | 3.8%         |
| 2     | 30 / 15 / 40 / 5 / 10 / 0                             | 12.2%  | 5.0%       | 5.2%         |
| 3     | 40 / 20 / 25 / 0 / 15 / 0                             | 22.8%  | 11.2%      | 8.8%         |
| 4     | 50 / 20 / 20 / 0 / 10 / 0                             | 26.0%  | 14.9%      | 11.5%        |
| 5     | 60 / 15 / 5 / 0 / 15 / 5                              | 31.2%  | 17.7%      | 14.3%        |

| bucket               | L1         | L2         | L3         | L4         | L5         |
| -------------------- | ---------- | ---------- | ---------- | ---------- | ---------- |
| US equity            | HDV, USMV  | HDV, USMV  | SPMO, VLUE | SPMO, VLUE | SPMO, VLUE |
| International equity | EFAV, IDV  | IDV, EFAV  | IDV, EFAV  | IDV, EMXC  | EMXC, IDV  |
| Bonds                | SPSB, STIP | SPSB, STIP | SPSB, STIP | SPSB, STIP | IGIB, IGSB |
| Cash                 | ICSH       | MINT       | —          | —          | —          |
| Gold / real assets   | XLRE, VNQI | XLRE, VNQI | GLDM, XLRE | GLDM, USRT | GLDM, USRT |
| Crypto               | —          | —          | —          | —          | GBTC       |

- the volatility limit is the one that binds, every level sits just under it
- weights move a little with live prices, picks don't

## Market data

- yfinance is called twice when a recommendation is built, both only for the picked tickers
  - `get_daily_returns` - 3y of daily prices to measure the mixes
  - `get_metrics` - per-holding metrics shown in the table
- one batched `yf.download` call each, 3 years of prices, 10s timeout
- per-holding metrics fall back to `snapshot.json` per ticker if the call fails or a ticker has a year or less of prices
- every holding says where its numbers came from - `source: "live"` or `"snapshot"`
- per-holding metrics
  - last_close, last_close_date
  - return_1y_pct - last close vs ~252 trading days ago
  - return_3y_annualised_pct - over the history we have (up to 3 years)
  - volatility_1y_pct - std of daily returns over a year × √252
  - max_drawdown_3y_pct - worst fall from a peak
- everything is saved with the recommendation, so opening it later shows the numbers the customer saw
- prices are only fetched when a recommendation is built. GET never calls yfinance

## Build the recommendation

- POST `/api/v1/recommendation`
- builds the recommendation for the result of the user's latest submission and saves it
- locked. If one already exists for that result, the saved one is returned (200), nothing is rebuilt and no prices are fetched
- if two requests race, the second one gets what the first one saved

```
curl -X 'POST' \
  'http://localhost:8000/api/v1/recommendation' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": "athul4554"
}'
```

```
response (201 when built, 200 when already saved)

{
  "user_id": "athul4554",
  "level": 3,
  "label": "Balanced",
  "currency": "USD",
  "invest_amount": 10000.0,
  "monthly_amount": 500.0,
  "groups": [
    { "group": "equity", "weight": 60.0, "amount": 6000.0, "monthly_amount": 300.0 },
    { "group": "fixed_income", "weight": 25.0, "amount": 2500.0, "monthly_amount": 125.0 },
    { "group": "real_estate", "weight": 7.5, "amount": 750.0, "monthly_amount": 37.5 },
    { "group": "gold", "weight": 7.5, "amount": 750.0, "monthly_amount": 37.5 }
  ],
  "holdings": [
    {
      "sleeve": "us_equity",
      "sleeve_label": "US equity",
      "group": "equity",
      "weight": 20.0,
      "amount": 2000.0,
      "monthly_amount": 100.0,
      "ticker": "SPMO",
      "name": "Invesco S&P 500 Momentum ETF",
      "provider": "Invesco",
      "category": "Large Blend",
      "expense_ratio_pct": 0.13,
      "distribution_yield_pct": 0.71,
      "inception_date": "2015-10-09",
      "esg": false,
      "sharia_compliant": false,
      "metrics": {
        "last_close": 143.69,
        "last_close_date": "2026-09-15",
        "return_1y_pct": 19.62,
        "return_3y_annualised_pct": 35.48,
        "volatility_1y_pct": 24.59,
        "max_drawdown_3y_pct": -20.13,
        "source": "snapshot"
      }
    },
    ...
  ],
  "metrics": {
    "expected_return_pct": 22.8,
    "volatility_pct": 11.2,
    "max_drawdown_pct": 8.8,
    "source": "live"
  },
  "disclaimer": "Based on past performance; not a guarantee of future returns.",
  "record": {
    "assessment": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "assessment_result": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "recommended_at": "2026-10-24T10:00:00Z",
    "rules": "1.2.0",
    "universe_as_of": "2026-09-16"
  }
}
```

- `metrics` - the chosen mix's return, volatility and drawdown, `null` for recommendations built before v1.2.0
- errors
  - 404 - no submission for this user
  - 404 - the latest submission has no result yet
  - 422 - user_id missing or too long
  - 500 - database error

## Get the saved recommendation

- GET `/api/v1/recommendation?user_id=`
- returns the saved recommendation, never builds one and never fetches prices

```
curl -X 'GET' \
  'http://localhost:8000/api/v1/recommendation?user_id=athul4554' \
  -H 'accept: application/json'
```

- response (200) - same shape as the POST response
- errors
  - 404 - no submission, no result yet, or no recommendation yet
  - 422 - user_id missing or too long
  - 500 - database error

## Table

#### recommendations - one locked recommendation per result

- id - uuid, primary key
- assessment_result_id - uuid, FK to `assessment_results.id`, unique
- user_id - varchar(100), indexed, copied
- level - smallint, copied from the result
- currency - `currency` enum, copied from the submission
- invest_amount, monthly_amount - numeric(14,2), copied
- holdings - jsonb, the full holdings list including metrics
- portfolio - jsonb, nullable - the chosen mix's `{expected_return_pct, volatility_pct, max_drawdown_pct, source}`, null before rules v1.2.0
- rules_version - varchar(20), rules `version`
- universe_as_of - date, `universe.json` `as_of`
- created_at - timestamptz, defaults to `now()`
- all columns except portfolio are NOT NULL
- label and groups aren't stored, they're worked out from level and holdings on every response
- `portfolio` added by migration `a1d3f5b7c9e2`, run with `docker compose exec backend alembic upgrade head`

## Tests

- [test_recommendation.py](../../tests/test_recommendation.py) - eligibility, score rule, weights inside ranges and limits, return rising with level, fallback, exclusions at every level, uninvested cash, mix maths (opposite funds cancel out), amounts, groups. yfinance always mocked, mixes measured on the snapshot
- [test_market_data.py](../../tests/test_market_data.py) - metric maths, snapshot fallback and daily returns, no network

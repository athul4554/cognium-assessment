#### Portfolio Recommendation - API

- builds on the locked result from [assessment plan](../assessment/plan.md). Scoring gives us a level, this turns it into real funds with amounts and market data
- code lives in [router.py](router.py), [builder.py](builder.py) and [market_data.py](market_data.py)
- rules in [rules/v1.0.0.json](rules/v1.0.0.json), funds in [universe.json](universe.json), fallback prices in [snapshot.json](snapshot.json)
- more on how each level and constraint plays out in [notes.md](notes.md)

### Libraries used

- fastapi
- pydantic (validation)
- sqlalchemy + postgres
- alembic (migrations)
- yfinance (live prices)

## What it uses

- level (1 to 5) from the saved result - picks the allocation
    - only the level, never the raw answers. The scorer already took the lowest of capacity, tolerance and caps, reading the answers again could undo a cap
- exclusions - picks which funds are allowed
- invest_amount, monthly_amount - turned into an amount per fund
- currency - copied onto the recommendation, every fund is priced in USD anyway
- notes, max_loss - not used

## Allocation per level

- each level is a fixed set of sleeve weights that add up to 100
- equity share by level is 15 / 35 / 55 / 75 / 87, roughly lines up with portfolios A (20/80), B (60/40) and C (90/10)

    - level 1 - US shares 10, International 5, Core bonds 20, US govt bonds 20, Inflation-linked 10, Cash 35
    - level 2 - US shares 22, International 10, Emerging 3, Core bonds 20, US govt bonds 10, Inflation-linked 10, Corporate bonds 5, Gold 5, Cash 15
    - level 3 - US shares 33, International 15, Emerging 7, Core bonds 15, US govt bonds 5, Inflation-linked 5, Corporate bonds 7, Gold 5, Property 3, Cash 5
    - level 4 - US shares 44, International 20, Emerging 11, Core bonds 8, Inflation-linked 2, Corporate bonds 5, Gold 5, Property 3, Cash 2
    - level 5 - US shares 49, International 24, Emerging 14, Core bonds 3, Gold 3, Property 3, Crypto 3, Cash 1

- no gold at level 1, it's too volatile (~29% a year) for a conservative profile
- crypto only shows up at level 5
- groups (for the donut / bars) - equity, fixed_income, real_estate, gold, crypto, cash

## How a fund is picked

- one fund per sleeve
- for every sleeve in the level's allocation
    - take the funds in that sleeve whose category is in the sleeve's allowed categories
    - drop the tickers in `exclude_tickers`
    - `no_crypto` - drop crypto funds
    - `sharia_compliant` - keep only sharia funds
    - nothing left? try the sleeve's `fallback` (regional shares → global shares, any bond sleeve → sukuk)
    - still nothing? move the weight to cash
    - cash itself has nothing (happens with sharia)? it becomes an uninvested cash line with `ticker: null`
    - `esg_preference` - if any ESG fund is left, keep only those. If not, keep all (it's a preference, not a filter)
    - pick the cheapest by expense ratio, then oldest inception date, then ticker A→Z
- if two sleeves land on the same fund (sharia: international + emerging both fall back to `SPWO`), their weights are added together
- amount = invest_amount × weight / 100, same for monthly, rounded to 2 decimals
- no market data is used to pick funds, so the same inputs always give the same funds
- not ranked on fund size (not comparable across providers) or on past returns (that's performance chasing)

## Tickers left out on purpose

- BITO - bitcoin futures fund, the 38% "yield" is futures roll, not income
- BLOK - blockchain company shares, not crypto
- NEAR - short-term bond fund sitting in the cash sleeve
- FLOT, FLRN - floating-rate corporate credit, not cash
- long government bonds are left out through the treasuries category list (fell over 20% in the snapshot window)

## Market data

- only the picked tickers are fetched, never the whole universe
- one batched `yf.download` call, 3 years of prices, 10s timeout
- if the call fails, or a ticker has a year or less of prices, that ticker falls back to `snapshot.json`
- every holding says where its numbers came from - `source: "live"` or `"snapshot"`
- uninvested cash has `metrics: null`
- metrics
    - last_close, last_close_date
    - return_1y_pct - last close vs ~252 trading days ago
    - return_3y_annualised_pct - over the history we have (up to 3 years)
    - volatility_1y_pct - std of daily returns over a year × √252
    - max_drawdown_3y_pct - worst fall from a peak
- metrics are saved with the recommendation, so opening it later shows the numbers the customer saw
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
    { "group": "equity", "weight": 55, "amount": 5500.0, "monthly_amount": 275.0 },
    { "group": "fixed_income", "weight": 32, "amount": 3200.0, "monthly_amount": 160.0 },
    { "group": "real_estate", "weight": 3, "amount": 300.0, "monthly_amount": 15.0 },
    { "group": "gold", "weight": 5, "amount": 500.0, "monthly_amount": 25.0 },
    { "group": "cash", "weight": 5, "amount": 500.0, "monthly_amount": 25.0 }
  ],
  "holdings": [
    {
      "sleeve": "us_equity",
      "sleeve_label": "US shares",
      "group": "equity",
      "weight": 33,
      "amount": 3300.0,
      "monthly_amount": 165.0,
      "ticker": "IVV",
      "name": "iShares Core S&P 500 ETF",
      "provider": "iShares",
      "category": "Large Blend",
      "expense_ratio_pct": 0.03,
      "distribution_yield_pct": 1.06,
      "inception_date": "2000-05-15",
      "esg": false,
      "sharia_compliant": false,
      "metrics": {
        "last_close": 758.88,
        "last_close_date": "2026-09-15",
        "return_1y_pct": 15.96,
        "return_3y_annualised_pct": 20.97,
        "volatility_1y_pct": 12.85,
        "max_drawdown_3y_pct": -18.75,
        "source": "snapshot"
      }
    },
    ...
  ],
  "record": {
    "assessment": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "assessment_result": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "recommended_at": "2026-10-18T10:00:00Z",
    "rules": "1.0.0",
    "universe_as_of": "2026-09-16"
  }
}
```

- uninvested cash line (sharia only) looks like this

```
{
  "sleeve": "cash",
  "sleeve_label": "Cash (held uninvested)",
  "group": "cash",
  "weight": 10,
  "ticker": null,
  "name": "Cash (held uninvested)",
  "provider": null,
  "category": null,
  "expense_ratio_pct": null,
  "distribution_yield_pct": null,
  "inception_date": null,
  "esg": false,
  "sharia_compliant": false,
  "metrics": null,
  ...amounts
}
```

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

## What a level 3 customer gets

- no exclusions - IVV, SPDW, VWO, AGG, SPTI, STIP, VCIT, GLDM, SCHH, ICSH
- sharia - HLAL 33, SPWO 22 (international + emerging), SPSK 32 (all bonds), SPRE 3, uninvested cash 10 (cash + gold, gold ETFs aren't flagged sharia)

## Table

#### recommendations - one locked recommendation per result

- id - uuid, primary key
- assessment_result_id - uuid, FK to `assessment_results.id`, unique
- user_id - varchar(100), indexed, copied
- level - smallint, copied from the result
- currency - `currency` enum, copied from the submission
- invest_amount, monthly_amount - numeric(14,2), copied
- holdings - jsonb, the full holdings list including metrics
- rules_version - varchar(20), rules `version`
- universe_as_of - date, `universe.json` `as_of`
- created_at - timestamptz, defaults to `now()`
- all columns are NOT NULL
- label and groups aren't stored, they're worked out from level and holdings on every response

## Tests

- [test_recommendation.py](../../tests/test_recommendation.py) - selection rules
- [test_market_data.py](../../tests/test_market_data.py) - metric maths and snapshot fallback, no network

## Not in scope right now

- flags (FX exposure, max loss mismatch, single sukuk fund), the column was removed in a migration
- adjustments (which sleeve fell back to what, missing ESG notes), the column was removed in a migration
- minimum fund history filter
- portfolio-level totals like weighted expense ratio
- caching market data between requests

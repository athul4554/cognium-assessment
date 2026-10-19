#### Risk Assessment - API

- use [@/design/cognium-design.html for reference ](../../../frontend/app/design/cognium-design.html) to see where each field comes from
- code lives in [router.py](router.py) and [scoring.py](scoring.py), schemas in [schemas.py](../schemas.py), tables in [models.py](../models.py)

### Libraries used

- fastapi
- pydantic (validation)
- sqlalchemy + postgres
- alembic (migrations, tables are not created on startup)

## Answer codes

- the API only takes option codes, never the labels shown on screen. The frontend maps its labels to these codes
- codes must match the option keys in the scorer config [v1.0.0](rules/v1.0.0.json)

    - currency - `USD`, `AED`, `EUR`, `GBP`
    - horizon - `under_2`, `2_5`, `5_10`, `10_plus`
    - big_withdrawal - `true` / `false`
    - emergency_fund - `none`, `under_3_months`, `3_6_months`, `6_plus_months`
    - income - `none`, `self_employed`, `variable`, `salaried`
    - share_of_wealth - `over_50`, `25_50`, `10_25`, `under_10`
    - portfolio - `A`, `B`, `C`
    - drop - `sell_all`, `sell_some`, `hold`, `buy_more`
    - max_loss - `0`, `5`, `15`, `30_plus`
    - goal - `capital_preservation`, `income`, `balanced_growth`, `aggressive_growth`
    - experience - `none`, `funds_only`, `stocks_etfs`, `derivatives_leverage`
    - exclusions - list of `no_crypto`, `sharia_compliant`, `esg_preference` (`[]` means no restrictions)

## Validation

- user_id - 1 to 100 chars, trimmed, blank is rejected
- birth_year - between 1920 and the current year
- invest_amount - more than 0, max 2 decimal places
- monthly_amount - 0 or more, max 2 decimal places
- one currency is used for both amounts
- exclusions - no duplicates
- notes - optional, max 1000 chars, trimmed, blank is saved as `null`
- anything invalid returns 422

## Save the questionnaire

- POST `/api/v1/risk-assessment`
- every submit creates a new row, nothing is updated. The latest row is the one that counts

```
curl -X 'POST' \
  'http://localhost:8000/api/v1/risk-assessment' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": "athul4554",
  "capacity": {
    "birth_year": 1999,
    "currency": "USD",
    "invest_amount": 2048.34,
    "monthly_amount": 650.20,
    "horizon": "10_plus",
    "big_withdrawal": false,
    "emergency_fund": "3_6_months",
    "income": "salaried",
    "share_of_wealth": "10_25"
  },
  "tolerance": {
    "portfolio": "B",
    "drop": "hold",
    "max_loss": "15",
    "goal": "balanced_growth",
    "experience": "stocks_etfs"
  },
  "exclusions": ["no_crypto"],
  "notes": "Buying a house in 2028"
}'
```

```
response (201)

{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "user_id": "athul4554",
  "capacity": { ...same as request },
  "tolerance": { ...same as request },
  "exclusions": ["no_crypto"],
  "notes": "Buying a house in 2028",
  "created_at": "2026-10-17T15:20:00Z"
}
```

- errors
    - 422 - missing field, wrong code, number out of range, duplicate exclusion, notes too long
    - 500 - database error

## Get the latest questionnaire

- GET `/api/v1/risk-assessment?user_id=`
- returns the user's latest submission, used to prefill the form

```
curl -X 'GET' \
  'http://localhost:8000/api/v1/risk-assessment?user_id=athul4554' \
  -H 'accept: application/json'
```

- response (200) - same shape as the POST response
- errors
    - 404 - no submission for this user
    - 422 - user_id missing or too long

## Compute the result

- POST `/api/v1/assessment-result`
- scores the user's latest submission and saves the result
- results are locked. If the latest submission already has a result, the saved one is returned (200) and nothing is recomputed
- if two requests race, the second one gets the result the first one saved

```
curl -X 'POST' \
  'http://localhost:8000/api/v1/assessment-result' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": "athul4554"
}'
```

```
response (201 when computed, 200 when already saved)

{
  "user_id": "athul4554",
  "level": 3,
  "label": "Balanced",
  "scores": [
    {
      "title": "What you can afford · capacity",
      "label": "Aggressive",
      "score": 94,
      "reasons": [
        { "horizon": "10_plus", "points": 25 },
        { "big_withdrawal": false, "points": 15 },
        { "emergency_fund": "3_6_months", "points": 12 },
        { "income": "salaried", "points": 15 },
        { "share_of_wealth": "10_25", "points": 12 },
        { "age": 27, "points": 15 }
      ]
    },
    {
      "title": "How you feel about it · tolerance",
      "label": "Balanced",
      "score": 56,
      "reasons": [
        { "drop": "hold", "points": 14 },
        { "max_loss": "15", "points": 10 },
        { "portfolio": "B", "points": 10 },
        { "goal": "balanced_growth", "points": 10 },
        { "experience": "stocks_etfs", "points": 12 }
      ]
    }
  ],
  "record": {
    "assessment": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "submitted_at": "2026-10-17T15:20:00Z",
    "questionnaire": "2026-10-01",
    "scoring_rules": "1.0.0"
  }
}
```

- errors
    - 404 - no submission for this user
    - 422 - user_id missing or too long
    - 500 - database error

## Get the saved result

- GET `/api/v1/assessment-result?user_id=`
- returns the saved result for the latest submission, never computes one

```
curl -X 'GET' \
  'http://localhost:8000/api/v1/assessment-result?user_id=athul4554' \
  -H 'accept: application/json'
```

- response (200) - same shape as the POST response
- errors
    - 404 - no submission for this user, or the latest submission has no result yet
    - 422 - user_id missing or too long

## Scoring

- all rules come from [v1.0.0](rules/v1.0.0.json)
- capacity and tolerance are scored separately, each out of 100
- each factor adds points based on the answer, and each one shows up in `reasons` in the order the scorer lists them
- age = year the questionnaire was submitted − birth_year, so the result never drifts over time
- the score maps to a level with the bands
    - 0+ → 1 Conservative
    - 20+ → 2 Moderately conservative
    - 40+ → 3 Balanced
    - 60+ → 4 Growth
    - 80+ → 5 Aggressive
- final level = the lowest of capacity level, tolerance level and the `max_level` of every cap that matches
- caps
    - horizon under 2 years → max 1
    - big withdrawal in the next 3 years → max 2
    - no emergency fund → max 2
    - no income and over 50% of wealth → max 2
    - would sell everything after a 20% drop → max 2
    - can't accept any loss → max 1
    - no investing experience → max 3
- labels come from the scorer profiles, score titles are constants. Neither is stored
- invest_amount and monthly_amount are not scored

## Tables

#### risk_assessments - one row per submission

- id - uuid, primary key
- user_id - varchar(100)
- birth_year - smallint
- currency, horizon, emergency_fund, income, share_of_wealth - postgres enums
- invest_amount, monthly_amount - numeric(14,2)
- big_withdrawal - boolean
- portfolio, max_loss, goal, experience - postgres enums
- drop_reaction - postgres enum, it's `drop` in the API (`drop` is a reserved SQL word)
- exclusions - array of the `exclusion` enum, defaults to `{}`
- notes - varchar(1000), nullable
- created_at - timestamptz, defaults to `now()`
- all columns are NOT NULL except notes

#### assessment_results - one locked result per submission

- id - uuid, primary key
- assessment_id - uuid, FK to `risk_assessments.id`, unique
- user_id - varchar(100), indexed, copied from the submission
- level - smallint, 1 to 5
- capacity_score, tolerance_score - smallint, 0 to 100
- capacity_level, tolerance_level - smallint, 1 to 5
- capacity_reasons, tolerance_reasons - jsonb, the same lists returned in `reasons`
- questionnaire_version - varchar(20), scorer `released`
- scoring_rules_version - varchar(20), scorer `version`
- created_at - timestamptz, defaults to `now()`

## Not in scope right now

- flags (like "your chosen portfolio has fallen more than you'd accept") were dropped, the column was removed in a migration
- AI summary endpoint (`/api/v1/ai_assessment`)

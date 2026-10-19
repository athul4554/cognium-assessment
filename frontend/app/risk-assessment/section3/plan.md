#### Section C Constraints

- use [@/design/cognium-design.html for reference ](../../design/cognium-design.html), fourth page - section C

### Libraries to use

- shadcn
- tailwind
- zod (validation)
- react forms

### Questions to Ask

- Exclusions
- Disclaimer/Warning for sharia-compliant
- Optional Field

### Not to ask

- Base currency , its already handled

## Actions

- add back button and Submit button
- submit button should point to scoring page

## API Integration

on Continue

```
curl -X 'POST' \
  'http://localhost:8000/api/v1/risk-assessment' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": "string",
  "capacity": {
    "birth_year": 0,
    "currency": "USD",
    "invest_amount": 1,
    "monthly_amount": 0,
    "horizon": "under_2",
    "big_withdrawal": true,
    "emergency_fund": "none",
    "income": "none",
    "share_of_wealth": "over_50"
  },
  "tolerance": {
    "portfolio": "A",
    "drop": "sell_all",
    "max_loss": "0",
    "goal": "capital_preservation",
    "experience": "none"
  },
  "exclusions": [
    "no_crypto"
  ],
  "notes": "string"
}'

```

then execute this before moving to assessemnt score page

```
curl -X 'POST' \
  'http://localhost:8000/api/v1/assessment-result' \
  -H 'accept: */*' \
  -H 'Content-Type: application/json' \
  -d '{
  "user_id": "string"
}'
```

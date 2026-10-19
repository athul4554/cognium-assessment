#### User Capacity Form - RISK CAPACITY

- use [@/design/cognium-design.html for reference ](../../design/cognium-design.html), second page - section A

### Libraries to use

- shadcn
- tailwind
- zod (validation)
- react forms

### Fields required in the Form

    - Time and Money

        - Year of Birth
        - Investing Now - (Currency can also be selected by the user (USD,AED,EUR,GBP))
        - Monthly Investment Amount - (Currency can also be selected by the user (USD,AED,EUR,GBP)) .

        ```(Show a toast message if they select any of the currecny other than USD
        (All the funds we choose from are priced in US dollars. With AED, EUR or GBP, exchange rates also move what your money is worth to you. The dirham is pegged to the dollar, so that effect is small for AED.))```

        - Investing Now and Monthly Investment Amount share one currency — changing the currency in either field automatically updates the other.

        - When might you need this money?
        - Will you take out more than a quarter of it in the next 3 years?


    - Your Safety Net
        - If your income stopped, how long could savings cover your expenses?
        - Income source
        - Roughly what share of your savings and investments is this?
    - add corresponding options and fields as per the design

## Actions

- add back button and continue button
- on continue, if validation succeeds, move to Section B (/risk-assessment/section2)

## API integration

`curl -X 'POST' \
 'http://localhost:8000/api/v1/risk-assessment' \
 -H 'accept: _/_' \
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
}`

curl -X 'GET' \
 'http://localhost:8000/api/v1/risk-assessment?user*id=athul4554' \
 -H 'accept: */\_'

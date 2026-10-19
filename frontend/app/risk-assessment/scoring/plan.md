#### Scoring - assessment results

- use [@/design/cognium-design.html for reference ](../../design/cognium-design.html), fifth page - Assessemnt result

### Libraries to use

- shadcn
- tailwind

### Results to show

- Final Result
- What you can afford - capacity
- How you feel about it - tolerance
- What decided it
- Locked record and details

### Not to show

- What this means in money
- A big gap between the two

## Actions

- start new assessement - move to section1
- see my portfolio - move to recommendation page

## API Integration

```
curl -X 'GET' \
  'http://localhost:8000/api/v1/assessment-result?user_id=athul4554' \
  -H 'accept: */*'

```

```
response

{
  "user_id": "string",
  "level": 0,
  "label": "string",
  "scores": [
    {
      "title": "string",
      "label": "string",
      "score": 0,
      "reasons": [
        {
          "additionalProp1": {}
        }
      ]
    }
  ],
  "ceiling": "string",
  "flags": [
    {
      "id": "string",
      "message": "string"
    }
  ],
  "record": {
    "assessment": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "submitted_at": "2026-10-18T14:31:17.861Z",
    "questionnaire": "string",
    "scoring_rules": "string"
  }
}
```

# Cognium Risk Assessment — Next.js + FastAPI + Postgres

## Setup (one command)

Only requirement: **Docker Desktop** (or Docker Engine + Compose).

Run Your **DOCKER DESKTOP** ,

```bash
git clone https://github.com/athul4554/cognium-assessment.git

cd cognium-assessment

make up
```

## What is missing , Why?

- Fixed coupon notes (since its optional)
- LLM usage (LLM is not needed in this usecase , adding it in logic create unpredictable response for users)

## What to do next?

- Though LLM cannot be used in buisness logic part, It can be used as a layer to conlude the result to the user at the end of exercise.

## Service and PORTS

| Service  | URL (default ports)        |
| -------- | -------------------------- |
| Frontend | http://localhost:3000      |
| API      | http://localhost:8000/api  |
| API docs | http://localhost:8000/docs |
| Postgres | localhost:5432             |

## Running backend tests

Tests use the dev dependencies, which aren't installed in the image, so run them locally:

```bash
cd backend
uv run pytest
```

## Common commands

```bash
make logs      # follow logs
make db        # psql shell
make down      # stop everything
make reset     # stop and wipe the database volume
```

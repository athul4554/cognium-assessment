# Cognium Risk Assessment — Next.js + FastAPI + Postgres

## Setup (one command)

Only requirement: **Docker Desktop** (or Docker Engine + Compose).

```bash
git clone https://github.com/athul4554/cognium-assessment.git

then

cd cognium-assessment

then

make up
```

`make up` copies `.env.example` → `.env` (if missing) and runs `docker compose up --build`.
Without make: `cp .env.example .env && docker compose up --build`. Every value in `.env` has a
default in `docker-compose.yml`, so even a plain `docker compose up --build` works.

On startup the backend applies database migrations (`alembic upgrade head`), so a fresh
database gets its tables automatically.

| Service  | URL (default ports)        |
| -------- | -------------------------- |
| Frontend | http://localhost:3000      |
| API      | http://localhost:8000/api  |
| API docs | http://localhost:8000/docs |
| Postgres | localhost:5432             |

Code changes hot-reload in both frontend and backend — no rebuild needed.
Rebuild (`docker compose up --build`) only after changing `package.json` or `pyproject.toml`.

## Configuration (`.env`)

| Key                 | Default                | Purpose                    |
| ------------------- | ---------------------- | -------------------------- |
| `POSTGRES_USER`     | `postgres`             | Database user              |
| `POSTGRES_PASSWORD` | `postgres`             | Database password          |
| `POSTGRES_DB`       | `user-risk-assessment` | Database name              |
| `FRONTEND_PORT`     | `3000`                 | Host port for the frontend |
| `BACKEND_PORT`      | `8000`                 | Host port for the API      |
| `DB_PORT`           | `5432`                 | Host port for Postgres     |

Change a port if something on your machine already uses it. Ports only affect your machine;
inside Docker the services always talk on `backend:8000` and `db:5432`.

Changing the Postgres credentials after the first run needs a fresh volume (`make reset`),
because Postgres only reads them when it creates the database.

## Structure

```
.
├── docker-compose.yml   # wires all 3 services together
├── .env.example         # credentials and ports (copy to .env)
├── Makefile             # shortcuts: up / down / logs / reset / db
├── frontend/            # Next.js (React) — app/ router
│   └── next.config.mjs  # proxies /api/* → FastAPI
└── backend/             # FastAPI + SQLAlchemy
    ├── alembic/         # database migrations
    └── app/
        ├── main.py      # app + routers
        ├── db.py        # engine/session
        └── models.py    # tables
```

## How the pieces talk

- Browser → `localhost:3000/api/...` → Next.js rewrites it → `backend:8000/api/...`
- FastAPI → Postgres via `DATABASE_URL` (host `db`, the compose service name)
- Recommendations fetch live prices from yfinance (needs internet) and fall back to
  `backend/app/recommendation/snapshot.json` when that fails

## Editor support (optional)

Docker runs the app, but VS Code needs a local Python env for autocomplete.
Install [uv](https://docs.astral.sh/uv/) once, then:

```bash
cd backend
uv sync          # downloads Python 3.12 if needed, creates backend/.venv
```

In VS Code: Ctrl+Shift+P → **Python: Select Interpreter** → `backend/.venv`.

## Adding a Python package

```bash
cd backend
uv add <package>             # updates pyproject.toml + uv.lock + local .venv
docker compose up --build    # rebuild the backend image with it
```

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

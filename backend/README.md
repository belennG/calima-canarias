# calima-api

FastAPI backend for [Calima Canarias](../CLAUDE.md): stations, measurements, episodes
and CAMS forecast data, served over PostgreSQL + PostGIS.

## Run it

From the repository root, with Docker Compose (this starts both `db` and `api`):

```bash
docker compose up -d
```

The API is then at http://localhost:8000, with a health check at `/health`.

## Local development without Docker

Needs a Postgres + PostGIS instance reachable (see `docker-compose.yml` for the expected
user/password/database, in `.env`).

```bash
uv sync
uv run uvicorn calima_api.main:app --reload
```

## Layout

```
src/calima_api/
  main.py    FastAPI app and routes
  models.py  SQLAlchemy models — one class per table in docs/decisions.md
```

Dependencies are managed with `uv` (`pyproject.toml` / `uv.lock`). Database schema
changes go through Alembic migrations (not added yet).

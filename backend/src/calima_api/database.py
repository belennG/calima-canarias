"""Database connection string, shared between the FastAPI app and Alembic.

DB_HOST defaults to localhost because Alembic and uvicorn --reload normally run
directly on the host (against the port docker-compose forwards to 5432). Inside
the api container, docker-compose.yml sets DB_HOST=db instead.
"""

import os

from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.environ.get("DB_HOST", "localhost")

DATABASE_URL = (
    f"postgresql+psycopg://{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
    f"@{DB_HOST}:5432/{os.environ['POSTGRES_DB']}"
)

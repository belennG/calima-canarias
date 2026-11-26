FROM python:3.12-slim

# No .pyc files in the image, and logs go straight to the container's output
# instead of sitting in a buffer.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first, in their own layer: Docker caches this step and
# only re-runs it when pyproject.toml/uv.lock change, not on every code edit.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen

# Do not run as root. --create-home matters: uv writes its cache under the
# user's home directory, so the user needs one to write to.
RUN useradd --create-home --uid 10001 app \
    && chown -R app:app /app
USER app

EXPOSE 8000

# Reports healthy once /health answers (no database needed for this check).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

CMD ["uv", "run", "uvicorn", "calima_api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

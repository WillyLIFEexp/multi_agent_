# syntax=docker/dockerfile:1
# Build context is the project root. From app/core/infra/docker-compose.yml the
# context is set to ../../.. so the paths below resolve from the repo root.

# ---------- Build stage ----------
# Installs dependencies and the project into /app/.venv using uv.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

# Install dependencies first (cached layer) without the project code.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Install the project itself.
COPY README.md ./
COPY app ./app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---------- Deploy stage ----------
# Slim runtime image: just the built venv + app code, no uv or build caches.
# Same Debian/CPython base as the builder so the venv's interpreter path is valid.
FROM python:3.13-slim-bookworm AS deploy

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

COPY --from=builder /app/.venv /app/.venv
COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.13 /uv /bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencies first so this layer is cached until the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .

# Run as an unprivileged user. Caches go to /tmp so a read-only or bind-mounted /app still works.
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app
ENV RUFF_CACHE_DIR=/tmp/.ruff_cache \
    PYTEST_ADDOPTS="-o cache_dir=/tmp/.pytest_cache"
USER app

CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000"]

# syntax=docker/dockerfile:1.7-labs

FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl git && \
        rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
  --mount=type=secret,id=github_token \
  if [ -f /run/secrets/github_token ]; then \
    git config --global url."https://oauth2:$(cat /run/secrets/github_token)@github.com/".insteadOf "https://github.com/"; \
  fi && \
  uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
COPY app .
ENV PORT=1701
EXPOSE 1701
# Pre-install DuckDB extensions
RUN uv run python - <<'PY'
import duckdb
con = duckdb.connect()
con.execute("INSTALL httpfs;")
con.close()
PY

# One worker so each instance keeps a single set of per-visitor rate-limit counts (dash_app/rate_limit.py);
# the AI callbacks mostly wait on Gemini, so threads cover concurrency (matches Cloud Run's 16 per instance).
# Each AI request is a single Gemini call (~10s); Cloud Run's request timeout matches.
CMD exec gunicorn app:server -b 0.0.0.0:${PORT} --workers 1 --threads 16 --timeout 120
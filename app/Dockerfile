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
COPY . .
ENV PORT=1701
EXPOSE 1701
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:1701/healthz || exit 1
# Pre-install DuckDB extensions
RUN uv run python - <<'PY'
import duckdb
con = duckdb.connect()
con.execute("INSTALL httpfs;")
con.close()
PY

CMD ["uv", "run", "gunicorn", "app:server", "-b", "0.0.0.0:1701", "--workers", "2", "--threads", "4", "--timeout", "180"]
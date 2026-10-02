FROM ghcr.io/astral-sh/uv:python3.13-trixie-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml uv.lock* ./
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"
COPY app .
ENV PORT=1701
EXPOSE 1701

# One worker so each instance keeps a single set of per-visitor rate-limit counts (dash_app/rate_limit.py);
# the AI callbacks mostly wait on Gemini, so threads cover concurrency (matches Cloud Run's 16 per instance).
# Each AI request is a single Gemini call (~10s); Cloud Run's request timeout matches.
CMD exec gunicorn app:server -b 0.0.0.0:${PORT} --workers 1 --threads 16 --timeout 120

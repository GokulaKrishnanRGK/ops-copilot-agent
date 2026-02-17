FROM python:3.13-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY packages/observability /app/packages/observability
COPY packages/db /app/packages/db
COPY packages/llm-gateway /app/packages/llm-gateway
COPY packages/rag /app/packages/rag
COPY packages/agent-runtime /app/packages/agent-runtime
COPY apps/api /app/apps/api

RUN pip install --prefix=/install \
    /app/packages/observability \
    /app/packages/db \
    /app/packages/llm-gateway \
    /app/packages/rag \
    /app/packages/agent-runtime \
    /app/apps/api

FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY packages/db/alembic /app/migrations/alembic
COPY packages/db/alembic.ini /app/migrations/alembic.ini
COPY packages/llm-gateway/src/opscopilot_llm_gateway/costs.json /app/config/costs.json

EXPOSE 8000

CMD ["uvicorn", "opscopilot_api.main:app", "--host", "0.0.0.0", "--port", "8000"]

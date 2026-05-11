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
COPY packages/eval /app/packages/eval
COPY apps/api /app/apps/api

RUN pip install --prefix=/install \
    /app/packages/observability \
    /app/packages/db \
    /app/packages/llm-gateway \
    /app/packages/rag \
    /app/packages/agent-runtime \
    /app/packages/eval \
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
COPY prompts /app/prompts
COPY packages/eval/datasets /app/datasets
COPY apps/api/entrypoint.sh /app/entrypoint.sh

RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

CMD ["/app/entrypoint.sh"]

.PHONY: build test lint format format-check check test-web test-api test-tool test-db test-llm test-tools test-rag test-agent test-agent-integration test-unit test-integration install install-web install-observability install-api install-tool install-llm install-rag install-agent install-db opensearch-up opensearch-down observability-up observability-down rag-ingest run-api run-tool-server run-local

build:
	cd apps/web && npm run build

test-web:
	cd apps/web && npm test

test-api:
	cd apps/api && pytest

test-db:
	cd packages/db && pytest

test-tool:
	cd apps/tool-server && go test ./...

test-llm:
	cd packages/llm-gateway && pytest

test-rag:
	cd packages/rag && pytest

test-agent:
	cd packages/agent-runtime && pytest

test-agent-integration:
	./scripts/run-agent-integration.sh

test-unit:
	cd apps/web && npm test
	cd apps/api && pytest -m "not integration"
	cd apps/tool-server && go test ./...
	cd packages/db && pytest -m "not integration"
	cd packages/llm-gateway && pytest -m "not integration"
	cd packages/rag && pytest -m "not integration"
	cd packages/agent-runtime && pytest -m "not integration" -k "not mcp_integration"
	cd packages/tools && pytest -m "not integration"

test-integration:
	@echo "Required env: OPENSEARCH_URL OPENSEARCH_USERNAME OPENSEARCH_PASSWORD KUBECONFIG_PATH"
	./scripts/run-integration.sh

test-tools:
	cd packages/tools && pytest

test: test-web test-api test-tool test-db test-llm test-rag test-agent test-tools

lint:
	cd apps/web && npm run lint

format:
	cd apps/web && npm run format

format-check:
	cd apps/web && npm run format:check

check: build lint format-check test

install-web:
	cd apps/web && npm install

install-observability:
	cd packages/observability && pip install -e .

install-api:
	cd apps/api && pip install -e .

install-tool:
	cd apps/tool-server && go mod download

install-db:
	cd packages/db && pip install -e .

install-llm:
	cd packages/llm-gateway && pip install -e .

install-rag:
	cd packages/rag && pip install -e .

install-agent:
	cd packages/agent-runtime && pip install -e .

install: install-web install-observability install-api install-tool install-db install-llm install-rag install-agent

opensearch-up:
	docker compose --env-file .env -f deploy/compose/opensearch.yml up -d

opensearch-down:
	docker compose --env-file .env -f deploy/compose/opensearch.yml down

observability-up:
	docker compose --env-file .env -f deploy/compose/observability.yml up -d

observability-down:
	docker compose --env-file .env -f deploy/compose/observability.yml down

rag-ingest:
	opscopilot-rag-ingest --root packages/rag/sample_docs --extensions .md,.txt

run-api:
	cd apps/api && uvicorn opscopilot_api.main:app --host 0.0.0.0 --port $${API_PORT:-8000} --reload

run-tool-server:
	cd apps/tool-server && TOOL_SERVER_ADDR=":$${TOOL_SERVER_PORT:-8080}" go run ./cmd/tool-server

run-local:
	@set -e; \
	docker compose --env-file .env -f deploy/compose/opensearch.yml -f deploy/compose/observability.yml up -d; \
	export OTEL_EXPORTER_OTLP_ENDPOINT="$${OTEL_EXPORTER_OTLP_ENDPOINT:-http://localhost:4318}"; \
	export OTEL_EXPORTER_OTLP_PROTOCOL="$${OTEL_EXPORTER_OTLP_PROTOCOL:-http/protobuf}"; \
	( cd apps/api && OTEL_SERVICE_NAME="$${OTEL_SERVICE_NAME_API:-ops-copilot-api}" uvicorn opscopilot_api.main:app --host 0.0.0.0 --port $${API_PORT:-8000} --reload ) & \
	api_pid=$$!; \
	( cd apps/tool-server && OTEL_SERVICE_NAME="$${OTEL_SERVICE_NAME_TOOL_SERVER:-ops-copilot-tool-server}" TOOL_SERVER_ADDR=":$${TOOL_SERVER_PORT:-8080}" go run ./cmd/tool-server ) & \
	tool_pid=$$!; \
	trap 'kill $$tool_pid $$api_pid 2>/dev/null || true' INT TERM EXIT; \
	wait $$tool_pid $$api_pid

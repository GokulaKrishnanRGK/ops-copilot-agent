.PHONY: build test lint format format-check check test-web test-api test-tool test-db test-llm test-tools test-rag install install-web install-api install-tool install-llm install-rag opensearch-up opensearch-down

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

test-tools:
	cd packages/tools && pytest

test: test-web test-api test-tool test-db test-llm test-rag test-tools

lint:
	cd apps/web && npm run lint

format:
	cd apps/web && npm run format

format-check:
	cd apps/web && npm run format:check

check: build lint format-check test

install-web:
	cd apps/web && npm install

install-api:
	cd apps/api && pip install -e .

install-tool:
	cd apps/tool-server && go mod download

install-llm:
	cd packages/llm-gateway && pip install -e .

install-rag:
	cd packages/rag && pip install -e .

install: install-web install-api install-tool install-llm install-rag

opensearch-up:
	docker compose --env-file .env -f deploy/compose/opensearch.yml up -d

opensearch-down:
	docker compose --env-file .env -f deploy/compose/opensearch.yml down

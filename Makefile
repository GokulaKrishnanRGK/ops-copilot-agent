.PHONY: build test lint format format-check check test-web test-api test-tool install install-web install-api install-tool

build:
	cd apps/web && npm run build

test-web:
	cd apps/web && npm test

test-api:
	cd apps/api && pytest

test-tool:
	cd apps/tool-server && go test ./...

test: test-web test-api test-tool

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

install: install-web install-api install-tool

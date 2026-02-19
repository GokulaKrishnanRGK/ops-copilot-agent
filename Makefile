.PHONY: build test lint format format-check check test-web test-api test-tool test-db test-llm test-tools test-rag test-agent test-agent-integration test-unit test-integration install install-web install-observability install-api install-tool install-llm install-rag install-agent install-db opensearch-up opensearch-down observability-up observability-down helm-observability-up helm-observability-down rag-ingest run-api run-tool-server run-local run-local-down run-local-helm run-local-helm-down smoke-local kind-up kind-down kind-kubeconfig kind-seed docker-build-api docker-build-web docker-build-tool-server docker-build-images python-packages-build python-packages-publish tf-init tf-plan tf-apply tf-destroy tf-output tf-fmt tf-validate

IMAGE_TAG ?= dev
API_IMAGE_REPOSITORY ?= ops-copilot/api
WEB_IMAGE_REPOSITORY ?= ops-copilot/web
TOOL_SERVER_IMAGE_REPOSITORY ?= ops-copilot/tool-server
LOCAL_POSTGRES ?= 1
LOCAL_OPENSEARCH ?= 1
LOCAL_OTEL ?= 1
KIND_BOOTSTRAP ?= 1
KIND_SEED_WORKLOADS ?= 1
KIND_CLUSTER_NAME ?= opscopilot-local
KUBECONFIG_HANDOFF_PATH ?= /tmp/opscopilot-kind-kubeconfig
TF_ENV ?= dev
TF_VARS_FILE ?= deploy/terraform/environments/$(TF_ENV).tfvars
TF_STATE_KEY ?= ops-copilot/$(TF_ENV)/terraform.tfstate
TF_AUTO_APPROVE ?= 0

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

helm-observability-up:
	helm upgrade --install $${HELM_OBSERVABILITY_RELEASE_NAME:-opscopilot-observability} deploy/helm/observability -n $${HELM_LOCAL_NAMESPACE:-opscopilot-local} --create-namespace

helm-observability-down:
	helm uninstall $${HELM_OBSERVABILITY_RELEASE_NAME:-opscopilot-observability} -n $${HELM_LOCAL_NAMESPACE:-opscopilot-local} || true

rag-ingest:
	opscopilot-rag-ingest --root packages/rag/sample_docs --extensions .md,.txt

run-api:
	cd apps/api && uvicorn opscopilot_api.main:app --host 0.0.0.0 --port $${API_PORT:-8000} --reload

run-tool-server:
	cd apps/tool-server && TOOL_SERVER_ADDR=":$${TOOL_SERVER_PORT:-8080}" go run ./cmd/tool-server

kind-up:
	KIND_CLUSTER_NAME="$(KIND_CLUSTER_NAME)" bash scripts/create-kind.sh

kind-down:
	KIND_CLUSTER_NAME="$(KIND_CLUSTER_NAME)" bash scripts/delete-kind.sh

kind-kubeconfig:
	KIND_CLUSTER_NAME="$(KIND_CLUSTER_NAME)" KUBECONFIG_HANDOFF_PATH="$(KUBECONFIG_HANDOFF_PATH)" bash scripts/render-kind-kubeconfig.sh

kind-seed:
	KIND_CLUSTER_NAME="$(KIND_CLUSTER_NAME)" bash scripts/seed-kind-workloads.sh

docker-build-api:
	docker build -f apps/api/Dockerfile -t $(API_IMAGE_REPOSITORY):$(IMAGE_TAG) .

docker-build-web:
	docker build -f apps/web/Dockerfile -t $(WEB_IMAGE_REPOSITORY):$(IMAGE_TAG) .

docker-build-tool-server:
	docker build -f apps/tool-server/Dockerfile -t $(TOOL_SERVER_IMAGE_REPOSITORY):$(IMAGE_TAG) apps/tool-server

docker-build-images: docker-build-api docker-build-web docker-build-tool-server

python-packages-build:
	bash scripts/publish-python-packages.sh build

python-packages-publish:
	bash scripts/publish-python-packages.sh publish

run-local:
	LOCAL_POSTGRES="$(LOCAL_POSTGRES)" LOCAL_OPENSEARCH="$(LOCAL_OPENSEARCH)" LOCAL_OTEL="$(LOCAL_OTEL)" KIND_BOOTSTRAP="$(KIND_BOOTSTRAP)" KIND_SEED_WORKLOADS="$(KIND_SEED_WORKLOADS)" KIND_CLUSTER_NAME="$(KIND_CLUSTER_NAME)" KUBECONFIG_HANDOFF_PATH="$(KUBECONFIG_HANDOFF_PATH)" bash scripts/run-local.sh

run-local-down:
	LOCAL_POSTGRES="$(LOCAL_POSTGRES)" LOCAL_OPENSEARCH="$(LOCAL_OPENSEARCH)" LOCAL_OTEL="$(LOCAL_OTEL)" bash scripts/run-local-down.sh

run-local-helm:
	LOCAL_POSTGRES="$(LOCAL_POSTGRES)" LOCAL_OPENSEARCH="$(LOCAL_OPENSEARCH)" LOCAL_OTEL="$(LOCAL_OTEL)" KIND_BOOTSTRAP="$(KIND_BOOTSTRAP)" KIND_SEED_WORKLOADS="$(KIND_SEED_WORKLOADS)" KIND_CLUSTER_NAME="$(KIND_CLUSTER_NAME)" IMAGE_TAG="$(IMAGE_TAG)" API_IMAGE_REPOSITORY="$(API_IMAGE_REPOSITORY)" WEB_IMAGE_REPOSITORY="$(WEB_IMAGE_REPOSITORY)" TOOL_SERVER_IMAGE_REPOSITORY="$(TOOL_SERVER_IMAGE_REPOSITORY)" bash scripts/run-local-helm.sh

run-local-helm-down:
	LOCAL_POSTGRES="$(LOCAL_POSTGRES)" LOCAL_OPENSEARCH="$(LOCAL_OPENSEARCH)" LOCAL_OTEL="$(LOCAL_OTEL)" bash scripts/run-local-helm-down.sh

smoke-local:
	SMOKE_API_BASE_URL="$${SMOKE_API_BASE_URL:-http://localhost:8000/api}" SMOKE_PROMPT="$${SMOKE_PROMPT:-List the Kubernetes pods in namespace default and report their status.}" bash scripts/smoke-local.sh

tf-init:
	TF_ENV="$(TF_ENV)" TF_VARS_FILE="$(TF_VARS_FILE)" TF_STATE_KEY="$(TF_STATE_KEY)" bash scripts/terraform.sh init

tf-plan:
	TF_ENV="$(TF_ENV)" TF_VARS_FILE="$(TF_VARS_FILE)" TF_STATE_KEY="$(TF_STATE_KEY)" bash scripts/terraform.sh plan

tf-apply:
	TF_ENV="$(TF_ENV)" TF_VARS_FILE="$(TF_VARS_FILE)" TF_STATE_KEY="$(TF_STATE_KEY)" TF_AUTO_APPROVE="$(TF_AUTO_APPROVE)" bash scripts/terraform.sh apply

tf-destroy:
	TF_ENV="$(TF_ENV)" TF_VARS_FILE="$(TF_VARS_FILE)" TF_STATE_KEY="$(TF_STATE_KEY)" TF_AUTO_APPROVE="$(TF_AUTO_APPROVE)" bash scripts/terraform.sh destroy

tf-output:
	TF_ENV="$(TF_ENV)" TF_VARS_FILE="$(TF_VARS_FILE)" TF_STATE_KEY="$(TF_STATE_KEY)" bash scripts/terraform.sh output

tf-fmt:
	TF_ENV="$(TF_ENV)" TF_VARS_FILE="$(TF_VARS_FILE)" TF_STATE_KEY="$(TF_STATE_KEY)" bash scripts/terraform.sh fmt

tf-validate:
	TF_ENV="$(TF_ENV)" TF_VARS_FILE="$(TF_VARS_FILE)" TF_STATE_KEY="$(TF_STATE_KEY)" bash scripts/terraform.sh validate

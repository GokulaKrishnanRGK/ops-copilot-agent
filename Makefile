.PHONY: build test lint format format-check check test-web test-api test-tool test-db test-llm test-tools test-rag test-agent test-eval test-agent-integration test-unit test-integration install install-web install-observability install-api install-tool install-llm install-rag install-agent install-eval install-db opensearch-up opensearch-down observability-up observability-down helm-app-values-generate eks-secrets-sync helm-app-up helm-app-down helm-observability-up helm-observability-down helm-controller-values-generate helm-externaldns-up helm-externaldns-down helm-awslbc-up helm-awslbc-down rag-ingest prompts-push eval-dataset-push eval-langfuse-run run-api run-tool-server run-local run-local-down run-local-helm run-local-helm-down smoke-local kind-up kind-down kind-kubeconfig kind-seed eks-kubeconfig ecr-login ecr-build-push docker-build-api docker-build-web docker-build-tool-server docker-build-images python-packages-build python-packages-publish tf-init tf-plan tf-apply tf-destroy tf-output tf-fmt tf-validate

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

test-eval:
	cd packages/eval && pytest

test-agent-integration:
	./scripts/run-agent-integration.sh

test-unit:
	cd apps/web && npm test
	cd apps/api && pytest -m "not integration"
	cd apps/tool-server && go test -short ./...
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

install-eval:
	cd packages/eval && pip install -e .

install: install-web install-observability install-api install-tool install-db install-llm install-rag install-agent install-eval

opensearch-up:
	docker compose --env-file .env -f deploy/compose/opensearch.yml up -d

opensearch-down:
	docker compose --env-file .env -f deploy/compose/opensearch.yml down

observability-up:
	docker compose --env-file .env -f deploy/compose/observability.yml up -d

observability-down:
	docker compose --env-file .env -f deploy/compose/observability.yml down

helm-app-values-generate:
	TF_ENV="$(TF_ENV)" TF_VARS_FILE="$(TF_VARS_FILE)" TF_STATE_KEY="$(TF_STATE_KEY)" IMAGE_TAG="$(IMAGE_TAG)" LOG_LEVEL="$${LOG_LEVEL:-INFO}" K8S_ALLOWED_NAMESPACES="$${K8S_ALLOWED_NAMESPACES:-default}" HELM_APP_VALUES_OUT="$${HELM_APP_VALUES_OUT:-}" bash scripts/render-app-values.sh

eks-secrets-sync:
	TF_ENV="$(TF_ENV)" TF_VARS_FILE="$(TF_VARS_FILE)" TF_STATE_KEY="$(TF_STATE_KEY)" HELM_APP_NAMESPACE="$${HELM_APP_NAMESPACE:-opscopilot}" AWS_REGION="$${AWS_REGION:-}" AWS_PROFILE="$${AWS_PROFILE:-}" bash scripts/sync-eks-secrets.sh

helm-app-up:
	@if [ -z "$${HELM_APP_VALUES_FILE:-}" ]; then $(MAKE) helm-app-values-generate; fi
	@if [ "$${HELM_SKIP_SECRET_SYNC:-0}" != "1" ]; then $(MAKE) eks-secrets-sync; fi
	helm upgrade --install $${HELM_APP_RELEASE_NAME:-opscopilot} $${HELM_APP_CHART_PATH:-deploy/helm/opscopilot} -n $${HELM_APP_NAMESPACE:-opscopilot} --create-namespace --timeout $${HELM_APP_TIMEOUT:-20m} -f $${HELM_APP_VALUES_FILE:-deploy/helm/opscopilot/values-eks.generated.yaml}

helm-app-down:
	helm uninstall $${HELM_APP_RELEASE_NAME:-opscopilot} -n $${HELM_APP_NAMESPACE:-opscopilot} || true

helm-observability-up:
	helm upgrade --install $${HELM_OBSERVABILITY_RELEASE_NAME:-opscopilot-observability} deploy/helm/observability -n $${HELM_LOCAL_NAMESPACE:-opscopilot-local} --create-namespace

helm-observability-down:
	helm uninstall $${HELM_OBSERVABILITY_RELEASE_NAME:-opscopilot-observability} -n $${HELM_LOCAL_NAMESPACE:-opscopilot-local} || true

helm-controller-values-generate:
	TF_ENV="$(TF_ENV)" TF_VARS_FILE="$(TF_VARS_FILE)" TF_STATE_KEY="$(TF_STATE_KEY)" HELM_AWSLBC_CLUSTER_NAME="$${HELM_AWSLBC_CLUSTER_NAME:-}" HELM_EXTERNALDNS_TXT_OWNER_ID="$${HELM_EXTERNALDNS_TXT_OWNER_ID:-}" bash scripts/render-controller-values.sh

helm-externaldns-up:
	@if [ -z "$${HELM_EXTERNALDNS_VALUES_FILE:-}" ]; then $(MAKE) helm-controller-values-generate; fi
	helm upgrade --install $${HELM_EXTERNALDNS_RELEASE_NAME:-opscopilot-external-dns} deploy/helm/external-dns -n $${HELM_EXTERNALDNS_NAMESPACE:-external-dns} --create-namespace -f $${HELM_EXTERNALDNS_VALUES_FILE:-deploy/helm/external-dns/values-eks.generated.yaml}

helm-externaldns-down:
	helm uninstall $${HELM_EXTERNALDNS_RELEASE_NAME:-opscopilot-external-dns} -n $${HELM_EXTERNALDNS_NAMESPACE:-external-dns} || true

helm-awslbc-up:
	helm repo add eks https://aws.github.io/eks-charts || true
	helm repo update
	@if [ -z "$${HELM_AWSLBC_VALUES_FILE:-}" ]; then $(MAKE) helm-controller-values-generate; fi
	helm upgrade --install $${HELM_AWSLBC_RELEASE_NAME:-aws-load-balancer-controller} eks/aws-load-balancer-controller -n $${HELM_AWSLBC_NAMESPACE:-kube-system} --create-namespace -f $${HELM_AWSLBC_VALUES_FILE:-deploy/helm/aws-load-balancer-controller/values-eks.generated.yaml}

helm-awslbc-down:
	helm uninstall $${HELM_AWSLBC_RELEASE_NAME:-aws-load-balancer-controller} -n $${HELM_AWSLBC_NAMESPACE:-kube-system} || true

rag-ingest:
	opscopilot-rag-ingest --root packages/rag/sample_docs --extensions .md,.txt

prompts-push:
	@if [ -x .venv/bin/python ]; then PYTHON_BIN=".venv/bin/python"; else PYTHON_BIN="python"; fi; \
	set -a; [ ! -f .env ] || . ./.env; set +a; \
	PYTHONPATH=packages/agent-runtime/src $$PYTHON_BIN -m opscopilot_agent_runtime.cli.prompts --prompts-dir prompts

eval-dataset-push:
	@if [ -x .venv/bin/python ]; then PYTHON_BIN=".venv/bin/python"; else PYTHON_BIN="python"; fi; \
	set -a; [ ! -f .env ] || . ./.env; set +a; \
	PYTHONPATH=packages/eval/src $$PYTHON_BIN -m opscopilot_eval.cli push-dataset --dataset $${EVAL_DATASET_NAME:-ops-copilot-v1} --datasets-dir $${EVAL_DATASETS_DIR:-packages/eval/datasets}

eval-langfuse-run:
	@if [ -x .venv/bin/python ]; then PYTHON_BIN=".venv/bin/python"; else PYTHON_BIN="python"; fi; \
	set -a; [ ! -f .env ] || . ./.env; set +a; \
	PYTHONPATH=packages/eval/src $$PYTHON_BIN -m opscopilot_eval.cli run-langfuse --dataset $${EVAL_DATASET_NAME:-ops-copilot-v1} --prompt-version $${LANGFUSE_PROMPT_VERSION:-local} --model $${EVAL_MODEL_ID:-$${LLM_MODEL_ID:-local}}

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

eks-kubeconfig:
	TF_ENV="$(TF_ENV)" TF_VARS_FILE="$(TF_VARS_FILE)" TF_STATE_KEY="$(TF_STATE_KEY)" EKS_CLUSTER_NAME="$${EKS_CLUSTER_NAME:-}" EKS_AWS_REGION="$${EKS_AWS_REGION:-}" AWS_REGION="$${AWS_REGION:-}" AWS_PROFILE="$${AWS_PROFILE:-}" KUBECONFIG_PATH="$${KUBECONFIG_PATH:-}" bash scripts/eks-kubeconfig.sh

ecr-login:
	@if [ -z "$${AWS_REGION:-}" ]; then echo "AWS_REGION is required"; exit 1; fi
	@acct=$$(aws $${AWS_PROFILE:+--profile "$${AWS_PROFILE}"} sts get-caller-identity --query Account --output text) && \
	aws ecr get-login-password --region "$${AWS_REGION}" $${AWS_PROFILE:+--profile "$${AWS_PROFILE}"} | docker login --username AWS --password-stdin "$${acct}.dkr.ecr.$${AWS_REGION}.amazonaws.com"

ecr-build-push:
	TF_ENV="$(TF_ENV)" TF_VARS_FILE="$(TF_VARS_FILE)" TF_STATE_KEY="$(TF_STATE_KEY)" IMAGE_TAG="$(IMAGE_TAG)" AWS_REGION="$${AWS_REGION:-}" AWS_PROFILE="$${AWS_PROFILE:-}" bash scripts/push-ecr-images.sh

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

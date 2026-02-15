#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "integration: kubectl is required" >&2
  exit 1
fi
if ! command -v kind >/dev/null 2>&1; then
  echo "integration: kind is required" >&2
  exit 1
fi

if [ -z "${OPENSEARCH_PASSWORD:-}" ]; then
  echo "integration: OPENSEARCH_PASSWORD is required for integration tests" >&2
  exit 1
fi
if [ -z "${OPENSEARCH_USERNAME:-}" ]; then
  echo "integration: OPENSEARCH_USERNAME is required for integration tests" >&2
  exit 1
fi
if [ -z "${OPENSEARCH_URL:-}" ]; then
  echo "integration: OPENSEARCH_URL is required for integration tests" >&2
  exit 1
fi
if [ -z "${LOGS_HOST_PATH:-}" ]; then
  echo "integration: LOGS_HOST_PATH is required for integration tests" >&2
  exit 1
fi
if [ -z "${TOOL_SERVER_LOG_FILE:-}" ]; then
  echo "integration: TOOL_SERVER_LOG_FILE is required for integration tests" >&2
  exit 1
fi
if [ -z "${API_LOG_FILE:-}" ]; then
  echo "integration: API_LOG_FILE is required for integration tests" >&2
  exit 1
fi

cluster_name="opscopilot-test"
if ! kind get clusters | grep -q "^${cluster_name}$"; then
  kind create cluster --name "${cluster_name}"
fi
kubectl config use-context "kind-${cluster_name}" >/dev/null
for _ in {1..30}; do
  if kubectl get serviceaccount default >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
if ! kubectl get serviceaccount default >/dev/null 2>&1; then
  echo "integration: default serviceaccount not ready" >&2
  exit 1
fi
if ! kubectl get pod hello >/dev/null 2>&1; then
  kubectl run hello --image=nginx --restart=Never >/dev/null
  kubectl wait --for=condition=Ready pod/hello --timeout=120s >/dev/null
fi

host_kube="${KUBECONFIG_PATH:-$HOME/.kube/config}"
kube_tmp="$(mktemp)"
cleanup() {
  if [ "${INTEGRATION_VERBOSE:-0}" = "1" ]; then
    docker compose -f "$repo_root/deploy/compose/opensearch.yml" -f "$repo_root/deploy/compose/integration.yml" logs --no-color tool-server
  fi
  docker compose -f "$repo_root/deploy/compose/opensearch.yml" -f "$repo_root/deploy/compose/integration.yml" down
  rm -f "$kube_tmp"
#  if kind get clusters | grep -q "^${cluster_name}$"; then
#    kind delete cluster --name "${cluster_name}"
#  fi
}
trap cleanup EXIT

kubectl config view --raw > "$kube_tmp"
if [ ! -s "$kube_tmp" ]; then
  echo "integration: failed to render kubeconfig" >&2
  exit 1
fi
if grep -q "server: https://127.0.0.1" "$kube_tmp"; then
  sed -i '' 's#server: https://127.0.0.1#server: https://host.docker.internal#g' "$kube_tmp"
fi
if grep -q "server: https://localhost" "$kube_tmp"; then
  sed -i '' 's#server: https://localhost#server: https://host.docker.internal#g' "$kube_tmp"
fi
if grep -q "server: https://0.0.0.0" "$kube_tmp"; then
  sed -i '' 's#server: https://0.0.0.0#server: https://host.docker.internal#g' "$kube_tmp"
fi

export K8S_ALLOWED_NAMESPACES="${K8S_ALLOWED_NAMESPACES:-default}"
export MCP_BASE_URL="${MCP_BASE_URL:-http://localhost:8080/mcp}"
export OPENSEARCH_URL="${OPENSEARCH_URL:-https://localhost:9200}"
export DATABASE_URL="${DATABASE_URL:-postgresql+psycopg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-root}@localhost:5432/${POSTGRES_DB:-opscopilot}}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"
export RUN_MCP_INTEGRATION="1"
export MCP_NAMESPACE="${MCP_NAMESPACE:-default}"
export MCP_LABEL_SELECTOR="${MCP_LABEL_SELECTOR:-}"
mkdir -p "${LOGS_HOST_PATH}" "$(dirname "${API_LOG_FILE}")"
export TEST_LOG_ROOT="${TEST_LOG_ROOT:-/Volumes/Work/Projects/logs/opscopilot/tests}"
TEST_RUN_DIR="$(TEST_LOG_ROOT="${TEST_LOG_ROOT}" bash "$repo_root/scripts/new-test-run-dir.sh")"
export TEST_RUN_DIR
echo "integration: test logs dir ${TEST_RUN_DIR}"
if [ -n "${OPENAI_API_KEY:-}" ]; then
  export LLM_EMBEDDING_PROVIDER="${LLM_EMBEDDING_PROVIDER:-openai}"
fi

KUBECONFIG_PATH="$kube_tmp" \
  docker compose -f "$repo_root/deploy/compose/opensearch.yml" -f "$repo_root/deploy/compose/integration.yml" up -d --build

for _ in {1..20}; do
  if curl -sf "http://localhost:8080/health" >/dev/null; then
    break
  fi
  sleep 1
done

if ! curl -sf "http://localhost:8080/health" >/dev/null; then
  echo "tool-server failed health check" >&2
  if [ "${INTEGRATION_VERBOSE:-0}" = "1" ]; then
    docker compose -f "$repo_root/deploy/compose/opensearch.yml" -f "$repo_root/deploy/compose/integration.yml" logs --no-color tool-server
  fi
  exit 1
fi


for _ in {1..30}; do
  if docker exec compose-postgres-1 pg_isready -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-opscopilot}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! docker exec compose-postgres-1 pg_isready -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-opscopilot}" >/dev/null 2>&1; then
  echo "postgres failed health check" >&2
  if [ "${INTEGRATION_VERBOSE:-0}" = "1" ]; then
    docker compose -f "$repo_root/deploy/compose/opensearch.yml" -f "$repo_root/deploy/compose/integration.yml" logs --no-color tool-server
  fi
  exit 1
fi

for _ in {1..60}; do
  if curl -skf -u "${OPENSEARCH_USERNAME}:${OPENSEARCH_PASSWORD}" "${OPENSEARCH_URL}" >/dev/null; then
    break
  fi
  sleep 1
done

if ! curl -skf -u "${OPENSEARCH_USERNAME}:${OPENSEARCH_PASSWORD}" "${OPENSEARCH_URL}" >/dev/null; then
  echo "opensearch failed health check at ${OPENSEARCH_URL} with user ${OPENSEARCH_USERNAME}" >&2
  if [ "${INTEGRATION_VERBOSE:-0}" = "1" ]; then
    docker compose -f "$repo_root/deploy/compose/opensearch.yml" -f "$repo_root/deploy/compose/integration.yml" logs --no-color tool-server
  fi
  exit 1
fi


summary=()
set +e
cd packages/agent-runtime
export KUBECONFIG_PATH="$host_kube"
pytest_args=()
if [ "${INTEGRATION_VERBOSE:-0}" = "1" ]; then
  pytest_args+=("--log-cli-level=INFO")
fi
TEST_LOG_ROOT="${TEST_LOG_ROOT}" TEST_RUN_DIR="${TEST_RUN_DIR}" MCP_NAMESPACE="$MCP_NAMESPACE" MCP_LABEL_SELECTOR="$MCP_LABEL_SELECTOR" \
  bash "$repo_root/scripts/run-test-logged.sh" agent-runtime-integration -- pytest "${pytest_args[@]}" tests/integration
status=$?
summary+=("agent-runtime:integration=$status")
set -e

if [ $status -eq 0 ]; then
  cd "$repo_root/apps/api"
  TEST_LOG_ROOT="${TEST_LOG_ROOT}" TEST_RUN_DIR="${TEST_RUN_DIR}" \
    bash "$repo_root/scripts/run-test-logged.sh" api-integration -- pytest "${pytest_args[@]}" -m integration
  status=$?
  summary+=("api:integration=$status")
fi

if [ $status -eq 0 ]; then
  cd "$repo_root/packages/rag"
  TEST_LOG_ROOT="${TEST_LOG_ROOT}" TEST_RUN_DIR="${TEST_RUN_DIR}" \
    bash "$repo_root/scripts/run-test-logged.sh" rag-integration -- pytest "${pytest_args[@]}" -m integration
  status=$?
  summary+=("rag:integration=$status")
fi

if [ $status -eq 0 ]; then
  cd "$repo_root/packages/llm-gateway"
  TEST_LOG_ROOT="${TEST_LOG_ROOT}" TEST_RUN_DIR="${TEST_RUN_DIR}" \
    bash "$repo_root/scripts/run-test-logged.sh" llm-gateway-integration -- pytest "${pytest_args[@]}"
  status=$?
  summary+=("llm-gateway=$status")
fi

if [ $status -eq 0 ]; then
  cd "$repo_root/packages/db"
  TEST_LOG_ROOT="${TEST_LOG_ROOT}" TEST_RUN_DIR="${TEST_RUN_DIR}" \
    bash "$repo_root/scripts/run-test-logged.sh" db-integration -- pytest "${pytest_args[@]}"
  status=$?
  summary+=("db=$status")
fi

if [ $status -eq 0 ]; then
  cd "$repo_root/apps/tool-server"
  TEST_LOG_ROOT="${TEST_LOG_ROOT}" TEST_RUN_DIR="${TEST_RUN_DIR}" \
    bash "$repo_root/scripts/run-test-logged.sh" tool-server-integration -- go test ./...
  status=$?
  summary+=("tool-server=$status")
fi

if [ $status -eq 0 ]; then
  cd "$repo_root/packages/tools"
  TEST_LOG_ROOT="${TEST_LOG_ROOT}" TEST_RUN_DIR="${TEST_RUN_DIR}" \
    bash "$repo_root/scripts/run-test-logged.sh" tools-integration -- pytest "${pytest_args[@]}"
  status=$?
  summary+=("tools=$status")
fi

if [ "${INTEGRATION_VERBOSE:-0}" = "1" ]; then
  docker compose -f "$repo_root/deploy/compose/opensearch.yml" -f "$repo_root/deploy/compose/integration.yml" logs --no-color tool-server
fi
echo "integration summary: ${summary[*]}"
exit $status

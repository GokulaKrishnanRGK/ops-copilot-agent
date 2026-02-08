#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "integration: kubectl is required" >&2
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

host_kube="${KUBECONFIG_PATH:-$HOME/.kube/config}"
kube_tmp="$(mktemp)"
cleanup() {
  if [ "${INTEGRATION_VERBOSE:-0}" = "1" ]; then
    docker compose -f "$repo_root/deploy/compose/integration.yml" logs --no-color
  fi
  docker compose -f "$repo_root/deploy/compose/integration.yml" down
  rm -f "$kube_tmp"
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
export RUN_MCP_INTEGRATION="1"
if [ -n "${OPENAI_API_KEY:-}" ]; then
  export LLM_EMBEDDING_PROVIDER="${LLM_EMBEDDING_PROVIDER:-openai}"
fi

KUBECONFIG_PATH="$kube_tmp" \
  docker compose -f "$repo_root/deploy/compose/integration.yml" up -d --build

for _ in {1..20}; do
  if curl -sf "http://localhost:8080/health" >/dev/null; then
    break
  fi
  sleep 1
done

if ! curl -sf "http://localhost:8080/health" >/dev/null; then
  echo "tool-server failed health check" >&2
  if [ "${INTEGRATION_VERBOSE:-0}" = "1" ]; then
    docker compose -f "$repo_root/deploy/compose/integration.yml" logs --no-color
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
    docker compose -f "$repo_root/deploy/compose/integration.yml" logs --no-color
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
    docker compose -f "$repo_root/deploy/compose/integration.yml" logs --no-color
  fi
  exit 1
fi

summary=()
set +e
cd packages/agent-runtime
export KUBECONFIG_PATH="$host_kube"
pytest -k mcp_integration -q
status=$?
summary+=("agent-runtime:mcp_integration=$status")
set -e

if [ $status -eq 0 ]; then
  cd "$repo_root/packages/rag"
  pytest -m integration -q
  status=$?
  summary+=("rag:integration=$status")
fi

if [ $status -eq 0 ]; then
  cd "$repo_root/packages/llm-gateway"
  pytest -q
  status=$?
  summary+=("llm-gateway=$status")
fi

if [ $status -eq 0 ]; then
  cd "$repo_root/packages/db"
  pytest -q
  status=$?
  summary+=("db=$status")
fi

if [ $status -eq 0 ]; then
  cd "$repo_root/apps/tool-server"
  go test ./...
  status=$?
  summary+=("tool-server=$status")
fi

if [ $status -eq 0 ]; then
  cd "$repo_root/packages/tools"
  pytest -q
  status=$?
  summary+=("tools=$status")
fi

if [ "${INTEGRATION_VERBOSE:-0}" = "1" ]; then
  docker compose -f "$repo_root/deploy/compose/integration.yml" logs --no-color
fi
echo "integration summary: ${summary[*]}"
exit $status

#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" >&2
  exit 1
fi

local_postgres="${LOCAL_POSTGRES:-1}"
local_opensearch="${LOCAL_OPENSEARCH:-1}"
local_otel="${LOCAL_OTEL:-1}"
kind_bootstrap="${KIND_BOOTSTRAP:-1}"
kind_seed_workloads="${KIND_SEED_WORKLOADS:-1}"
kind_cluster_name="${KIND_CLUSTER_NAME:-opscopilot-local}"
kubeconfig_handoff_path="${KUBECONFIG_HANDOFF_PATH:-/tmp/opscopilot-kind-kubeconfig}"

compose_files=(
  "deploy/compose/app.yml"
  "deploy/compose/tool-server.yml"
)
if [ "$local_postgres" = "1" ]; then
  compose_files+=("deploy/compose/postgres.yml")
fi
if [ "$local_opensearch" = "1" ]; then
  compose_files+=("deploy/compose/opensearch.yml")
fi
if [ "$local_otel" = "1" ]; then
  compose_files+=("deploy/compose/observability.yml")
fi

compose_cmd=(docker compose --env-file .env)
for file in "${compose_files[@]}"; do
  compose_cmd+=(-f "$file")
done

if [ "$kind_bootstrap" = "1" ]; then
  KIND_CLUSTER_NAME="$kind_cluster_name" bash scripts/create-kind.sh
  if [ "$kind_seed_workloads" = "1" ]; then
    KIND_CLUSTER_NAME="$kind_cluster_name" bash scripts/seed-kind-workloads.sh
  fi
  KIND_CLUSTER_NAME="$kind_cluster_name" KUBECONFIG_HANDOFF_PATH="$kubeconfig_handoff_path" bash scripts/render-kind-kubeconfig.sh >/dev/null
  export KUBECONFIG_PATH="$kubeconfig_handoff_path"
fi

"${compose_cmd[@]}" up -d

wait_http() {
  local name="$1"
  local url="$2"
  local timeout_seconds="$3"
  local elapsed=0
  while [ "$elapsed" -lt "$timeout_seconds" ]; do
    if curl -sf "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  echo "readiness check failed: ${name} (${url})" >&2
  return 1
}

wait_opensearch() {
  local timeout_seconds="$1"
  local url="${OPENSEARCH_URL:-https://localhost:9200}"
  local user="${OPENSEARCH_USERNAME:-admin}"
  local pass="${OPENSEARCH_PASSWORD:-}"
  local elapsed=0
  while [ "$elapsed" -lt "$timeout_seconds" ]; do
    if curl -skf -u "${user}:${pass}" "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  echo "readiness check failed: opensearch (${url})" >&2
  return 1
}

wait_postgres() {
  local timeout_seconds="$1"
  local elapsed=0
  local pg_user="${POSTGRES_USER:-postgres}"
  local pg_db="${POSTGRES_DB:-opscopilot}"
  while [ "$elapsed" -lt "$timeout_seconds" ]; do
    if "${compose_cmd[@]}" exec -T postgres pg_isready -U "$pg_user" -d "$pg_db" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  echo "readiness check failed: postgres" >&2
  return 1
}

if [ "$local_otel" = "1" ]; then
  wait_http "otel-collector" "http://localhost:13133/" 120
fi
if [ "$local_postgres" = "1" ]; then
  wait_postgres 120
fi
if [ "$local_opensearch" = "1" ]; then
  wait_opensearch 180
fi

wait_http "tool-server" "http://localhost:8080/health" 120
wait_http "api" "http://localhost:8000/health" 120
wait_http "web" "http://localhost:5173/" 60

echo "run-local ready"
echo "web:  http://localhost:5173"
echo "api:  http://localhost:8000/health"
echo "tool: http://localhost:8080/health"

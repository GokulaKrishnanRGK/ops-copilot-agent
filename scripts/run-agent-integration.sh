#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required" >&2
  exit 1
fi

kube_tmp="$(mktemp)"
cleanup() {
  docker compose -f deploy/compose/tool-server.yml down
  rm -f "$kube_tmp"
}
trap cleanup EXIT

kubectl config view --raw > "$kube_tmp"
if grep -q "server: https://127.0.0.1" "$kube_tmp"; then
  sed -i '' 's#server: https://127.0.0.1#server: https://host.docker.internal#g' "$kube_tmp"
fi
if grep -q "server: https://localhost" "$kube_tmp"; then
  sed -i '' 's#server: https://localhost#server: https://host.docker.internal#g' "$kube_tmp"
fi

export KUBECONFIG_PATH="$kube_tmp"
export K8S_ALLOWED_NAMESPACES="${K8S_ALLOWED_NAMESPACES:-default}"
export MCP_BASE_URL="${MCP_BASE_URL:-http://localhost:8080/mcp}"
export RUN_MCP_INTEGRATION="1"

KUBECONFIG_PATH="$KUBECONFIG_PATH" \
  docker compose -f deploy/compose/tool-server.yml up -d --build

for _ in {1..15}; do
  if curl -sf "http://localhost:8080/health" >/dev/null; then
    break
  fi
  sleep 1
done

if ! curl -sf "http://localhost:8080/health" >/dev/null; then
  echo "tool-server failed health check" >&2
  docker compose -f deploy/compose/tool-server.yml logs --no-color
  exit 1
fi

set +e
cd packages/agent-runtime
pytest -k mcp_integration -q
status=$?
set -e

docker compose -f deploy/compose/tool-server.yml logs --no-color
exit $status

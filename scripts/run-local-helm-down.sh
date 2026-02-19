#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

source scripts/load-env.sh "${repo_root}/.env"

local_postgres="${LOCAL_POSTGRES:-1}"
local_opensearch="${LOCAL_OPENSEARCH:-1}"
local_otel="${LOCAL_OTEL:-1}"
helm_namespace="${HELM_LOCAL_NAMESPACE:-opscopilot-local}"
helm_release="${HELM_RELEASE_NAME:-opscopilot}"
observability_release="${HELM_OBSERVABILITY_RELEASE_NAME:-opscopilot-observability}"
state_dir="${HELM_LOCAL_STATE_DIR:-/tmp/opscopilot-local-helm}"

stop_port_forward() {
  local name="$1"
  local pid_file="${state_dir}/port-forward-${name}.pid"
  if [ ! -f "${pid_file}" ]; then
    return 0
  fi
  pid="$(cat "${pid_file}")"
  if [ -n "${pid}" ] && kill -0 "${pid}" >/dev/null 2>&1; then
    kill "${pid}" >/dev/null 2>&1 || true
  fi
  rm -f "${pid_file}"
}

if command -v helm >/dev/null 2>&1; then
  helm uninstall "${helm_release}" -n "${helm_namespace}" >/dev/null 2>&1 || true
  if [ "${local_otel}" = "1" ]; then
    helm uninstall "${observability_release}" -n "${helm_namespace}" >/dev/null 2>&1 || true
  fi
fi

stop_port_forward "web"
stop_port_forward "grafana"

kubectl -n "${helm_namespace}" delete secret opscopilot-api-secrets >/dev/null 2>&1 || true

compose_files=()
if [ "${local_postgres}" = "1" ]; then
  compose_files+=("deploy/compose/postgres.yml")
fi
if [ "${local_opensearch}" = "1" ]; then
  compose_files+=("deploy/compose/opensearch.yml")
fi

if [ "${#compose_files[@]}" -gt 0 ]; then
  compose_cmd=(docker compose --env-file .env)
  for file in "${compose_files[@]}"; do
    compose_cmd+=(-f "${file}")
  done
  "${compose_cmd[@]}" down
fi

rm -f "${state_dir}/port-forward-web.log" "${state_dir}/port-forward-grafana.log" 2>/dev/null || true

echo "run-local-helm-down complete"

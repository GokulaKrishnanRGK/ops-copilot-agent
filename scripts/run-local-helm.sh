#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

for cmd in docker kubectl helm; do
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "${cmd} is required" >&2
    exit 1
  fi
done

source scripts/load-env.sh "${repo_root}/.env"

local_postgres="${LOCAL_POSTGRES:-1}"
local_opensearch="${LOCAL_OPENSEARCH:-1}"
local_otel="${LOCAL_OTEL:-1}"
kind_bootstrap="${KIND_BOOTSTRAP:-1}"
kind_seed_workloads="${KIND_SEED_WORKLOADS:-1}"
kind_cluster_name="${KIND_CLUSTER_NAME:-opscopilot-local}"

helm_namespace="${HELM_LOCAL_NAMESPACE:-opscopilot-local}"
helm_release="${HELM_RELEASE_NAME:-opscopilot}"
helm_chart="${HELM_CHART_PATH:-deploy/helm/opscopilot}"
observability_release="${HELM_OBSERVABILITY_RELEASE_NAME:-opscopilot-observability}"
observability_chart="${HELM_OBSERVABILITY_CHART_PATH:-deploy/helm/observability}"
web_local_port="${HELM_LOCAL_WEB_PORT:-5173}"
grafana_local_port="${HELM_LOCAL_GRAFANA_PORT:-3000}"
state_dir="${HELM_LOCAL_STATE_DIR:-/tmp/opscopilot-local-helm}"

image_tag="${IMAGE_TAG:-dev}"
api_image_repo="${API_IMAGE_REPOSITORY:-ops-copilot/api}"
web_image_repo="${WEB_IMAGE_REPOSITORY:-ops-copilot/web}"
tool_image_repo="${TOOL_SERVER_IMAGE_REPOSITORY:-ops-copilot/tool-server}"
build_images="${HELM_LOCAL_BUILD_IMAGES:-1}"

database_url_local="${DATABASE_URL_HELM_LOCAL:-postgresql+psycopg://postgres:root@host.docker.internal:5432/opscopilot}"
opensearch_url_local="${OPENSEARCH_URL_HELM_LOCAL:-https://host.docker.internal:9200}"
otel_endpoint_local="${OTEL_EXPORTER_OTLP_ENDPOINT_HELM_LOCAL:-http://otel-collector:4318}"
log_level="${LOG_LEVEL:-INFO}"
k8s_allowed_namespaces="${K8S_ALLOWED_NAMESPACES:-default,observability}"
rbac_allowed_namespaces_yaml=""
IFS=',' read -r -a k8s_namespace_array <<< "${k8s_allowed_namespaces}"
for ns in "${k8s_namespace_array[@]}"; do
  trimmed="$(echo "${ns}" | xargs)"
  if [ -n "${trimmed}" ]; then
    rbac_allowed_namespaces_yaml="${rbac_allowed_namespaces_yaml}      - ${trimmed}\n"
  fi
done
if [ -z "${rbac_allowed_namespaces_yaml}" ]; then
  rbac_allowed_namespaces_yaml="      - default\n      - observability\n"
fi

mkdir -p "${state_dir}"

ensure_port_free() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1 && lsof -tiTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "local port ${port} is already in use; set HELM_LOCAL_WEB_PORT to override" >&2
    exit 1
  fi
}

start_port_forward() {
  local name="$1"
  local namespace="$2"
  local service="$3"
  local local_port="$4"
  local remote_port="$5"
  local pid_file="${state_dir}/port-forward-${name}.pid"
  local log_file="${state_dir}/port-forward-${name}.log"

  if [ -f "${pid_file}" ]; then
    old_pid="$(cat "${pid_file}")"
    if [ -n "${old_pid}" ] && kill -0 "${old_pid}" >/dev/null 2>&1; then
      kill "${old_pid}" >/dev/null 2>&1 || true
    fi
    rm -f "${pid_file}"
  fi

  nohup kubectl -n "${namespace}" port-forward "svc/${service}" "${local_port}:${remote_port}" >"${log_file}" 2>&1 &
  pf_pid=$!
  echo "${pf_pid}" > "${pid_file}"

  attempts=30
  while [ "${attempts}" -gt 0 ]; do
    if ! kill -0 "${pf_pid}" >/dev/null 2>&1; then
      echo "port-forward failed for ${name}; check ${log_file}" >&2
      exit 1
    fi
    if command -v nc >/dev/null 2>&1 && nc -z 127.0.0.1 "${local_port}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    attempts=$((attempts - 1))
  done

  echo "timed out waiting for ${name} port-forward on localhost:${local_port}; check ${log_file}" >&2
  exit 1
}

ensure_port_free "${web_local_port}"
if [ "${local_otel}" = "1" ]; then
  ensure_port_free "${grafana_local_port}"
fi

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
  "${compose_cmd[@]}" up -d
fi

if [ "${kind_bootstrap}" = "1" ]; then
  if ! command -v kind >/dev/null 2>&1; then
    echo "kind is required when KIND_BOOTSTRAP=1" >&2
    exit 1
  fi
  KIND_CLUSTER_NAME="${kind_cluster_name}" bash scripts/create-kind.sh
  if [ "${kind_seed_workloads}" = "1" ]; then
    KIND_CLUSTER_NAME="${kind_cluster_name}" bash scripts/seed-kind-workloads.sh
  fi
fi

if [ "${build_images}" = "1" ]; then
  docker build -f apps/api/Dockerfile -t "${api_image_repo}:${image_tag}" .
  docker build -f apps/web/Dockerfile -t "${web_image_repo}:${image_tag}" .
  docker build -f apps/tool-server/Dockerfile -t "${tool_image_repo}:${image_tag}" apps/tool-server
fi

if command -v kind >/dev/null 2>&1; then
  kind load docker-image "${api_image_repo}:${image_tag}" --name "${kind_cluster_name}"
  kind load docker-image "${web_image_repo}:${image_tag}" --name "${kind_cluster_name}"
  kind load docker-image "${tool_image_repo}:${image_tag}" --name "${kind_cluster_name}"
fi

kubectl get namespace "${helm_namespace}" >/dev/null 2>&1 || kubectl create namespace "${helm_namespace}"

kubectl -n "${helm_namespace}" create secret generic opscopilot-api-secrets \
  --from-literal=DATABASE_URL="${database_url_local}" \
  --from-literal=OPENSEARCH_USERNAME="${OPENSEARCH_USERNAME:-admin}" \
  --from-literal=OPENSEARCH_PASSWORD="${OPENSEARCH_PASSWORD:-}" \
  --from-literal=AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}" \
  --from-literal=AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}" \
  --from-literal=AWS_SESSION_TOKEN="${AWS_SESSION_TOKEN:-}" \
  --from-literal=OPENAI_API_KEY="${OPENAI_API_KEY:-}" \
  --dry-run=client -o yaml | kubectl apply -f -

tmp_values="$(mktemp /tmp/opscopilot-helm-local-values-XXXXXX)"
tmp_values_yaml="${tmp_values}.yaml"
mv "${tmp_values}" "${tmp_values_yaml}"
tmp_values="${tmp_values_yaml}"
trap 'rm -f "${tmp_values}"' EXIT
cat > "${tmp_values}" <<EOF
global:
  imageTag: "${image_tag}"
  logLevel: "${log_level}"
images:
  apiRepository: "${api_image_repo}"
  webRepository: "${web_image_repo}"
  toolServerRepository: "${tool_image_repo}"
api:
  serviceAlias:
    enabled: true
    name: "api"
  env:
    API_LOG_FILE: "${API_LOG_FILE:-/tmp/opscopilot-api.log}"
    OPENSEARCH_URL: "${opensearch_url_local}"
    OPENSEARCH_VERIFY_CERTS: "${OPENSEARCH_VERIFY_CERTS:-false}"
    OPENSEARCH_INDEX: "${OPENSEARCH_INDEX:-opscopilot-docs}"
    LLM_MODEL_ID: "${LLM_MODEL_ID:-}"
    LLM_COST_TABLE_PATH: "${LLM_COST_TABLE_PATH_HELM_LOCAL:-/app/config/costs.json}"
    LLM_EMBEDDING_PROVIDER: "${LLM_EMBEDDING_PROVIDER:-openai}"
    OPENAI_EMBEDDING_MODEL: "${OPENAI_EMBEDDING_MODEL:-text-embedding-3-small}"
    BEDROCK_EMBEDDING_MODEL_ID: "${BEDROCK_EMBEDDING_MODEL_ID:-}"
    BEDROCK_REGION: "${BEDROCK_REGION:-${AWS_REGION:-}}"
    AWS_REGION: "${AWS_REGION:-}"
    OTEL_EXPORTER_OTLP_ENDPOINT: "${otel_endpoint_local}"
    OTEL_EXPORTER_OTLP_PROTOCOL: "${OTEL_EXPORTER_OTLP_PROTOCOL:-http/protobuf}"
    OTEL_SERVICE_NAME: "${OTEL_SERVICE_NAME_API:-ops-copilot-api}"
  secretEnv:
    DATABASE_URL:
      secretName: "opscopilot-api-secrets"
      secretKey: "DATABASE_URL"
    OPENSEARCH_USERNAME:
      secretName: "opscopilot-api-secrets"
      secretKey: "OPENSEARCH_USERNAME"
    OPENSEARCH_PASSWORD:
      secretName: "opscopilot-api-secrets"
      secretKey: "OPENSEARCH_PASSWORD"
    AWS_ACCESS_KEY_ID:
      secretName: "opscopilot-api-secrets"
      secretKey: "AWS_ACCESS_KEY_ID"
    AWS_SECRET_ACCESS_KEY:
      secretName: "opscopilot-api-secrets"
      secretKey: "AWS_SECRET_ACCESS_KEY"
    AWS_SESSION_TOKEN:
      secretName: "opscopilot-api-secrets"
      secretKey: "AWS_SESSION_TOKEN"
    OPENAI_API_KEY:
      secretName: "opscopilot-api-secrets"
      secretKey: "OPENAI_API_KEY"
web:
  env:
    WEB_API_BASE_URL: "/api"
toolServer:
  rbac:
    allowedNamespaces:
$(printf "${rbac_allowed_namespaces_yaml}")
  env:
    TOOL_SERVER_LOG_FILE: "${TOOL_SERVER_LOG_FILE:-/tmp/opscopilot-tool-server.log}"
    K8S_ALLOWED_NAMESPACES: "${k8s_allowed_namespaces}"
    OTEL_EXPORTER_OTLP_ENDPOINT: "${otel_endpoint_local}"
    OTEL_SERVICE_NAME: "${OTEL_SERVICE_NAME_TOOL_SERVER:-ops-copilot-tool-server}"
migrations:
  enabled: true
  database:
    useTerraformDatabaseSecret: false
    secretName: "opscopilot-api-secrets"
    secretKey: "DATABASE_URL"
ingress:
  enabled: false
observability:
  otelCollector:
    enabled: false
EOF

helm upgrade --install "${helm_release}" "${helm_chart}" \
  --namespace "${helm_namespace}" \
  --create-namespace \
  -f "${tmp_values}"

if [ "${local_otel}" = "1" ]; then
  helm upgrade --install "${observability_release}" "${observability_chart}" \
    --namespace "${helm_namespace}" \
    --create-namespace \
    -f "${observability_chart}/values-local-kind.yaml"
  kubectl -n "${helm_namespace}" rollout status deployment/otel-collector --timeout=180s
  kubectl -n "${helm_namespace}" rollout status deployment/grafana --timeout=180s
fi

kubectl -n "${helm_namespace}" rollout status deployment/"${helm_release}"-opscopilot-tool-server --timeout=180s
kubectl -n "${helm_namespace}" rollout status deployment/"${helm_release}"-opscopilot-api --timeout=180s
kubectl -n "${helm_namespace}" rollout status deployment/"${helm_release}"-opscopilot-web --timeout=180s

job_name="$(kubectl -n "${helm_namespace}" get jobs -l app.kubernetes.io/component=db-migrate -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
if [ -n "${job_name}" ]; then
  kubectl -n "${helm_namespace}" wait --for=condition=complete "job/${job_name}" --timeout=180s
fi

web_svc="$(kubectl -n "${helm_namespace}" get svc -l app.kubernetes.io/component=web -o jsonpath='{.items[0].metadata.name}')"
start_port_forward "web" "${helm_namespace}" "${web_svc}" "${web_local_port}" 80
if [ "${local_otel}" = "1" ]; then
  start_port_forward "grafana" "${helm_namespace}" "grafana" "${grafana_local_port}" 3000
fi

echo "run-local-helm ready"
echo "web: http://localhost:${web_local_port}"
if [ "${local_otel}" = "1" ]; then
  echo "observability: http://localhost:${grafana_local_port}"
fi

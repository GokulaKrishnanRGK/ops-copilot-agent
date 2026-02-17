#!/usr/bin/env bash
set -euo pipefail

if ! command -v kind >/dev/null 2>&1; then
  echo "kind is required" >&2
  exit 1
fi
if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required" >&2
  exit 1
fi

cluster_name="${KIND_CLUSTER_NAME:-opscopilot-local}"
context_name="kind-${cluster_name}"
output_path="${KUBECONFIG_HANDOFF_PATH:-/tmp/opscopilot-kind-kubeconfig}"

if ! kind get clusters | grep -q "^${cluster_name}$"; then
  echo "kind cluster not found: ${cluster_name}" >&2
  exit 1
fi

tmp_file="$(mktemp)"
cleanup() {
  rm -f "${tmp_file}"
}
trap cleanup EXIT

kubectl config view --raw --context "${context_name}" > "${tmp_file}"
if [ ! -s "${tmp_file}" ]; then
  echo "failed to render kubeconfig for context ${context_name}" >&2
  exit 1
fi

sed -E 's#server: https://(127\.0\.0\.1|localhost|0\.0\.0\.0)#server: https://host.docker.internal#g' "${tmp_file}" > "${output_path}"
chmod 600 "${output_path}"
echo "${output_path}"

#!/usr/bin/env bash
set -euo pipefail

if ! command -v kubectl >/dev/null 2>&1; then
  echo "kubectl is required" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cluster_name="${KIND_CLUSTER_NAME:-opscopilot-local}"
context_name="kind-${cluster_name}"
manifest_path="${repo_root}/deploy/kind/local-workloads.yaml"

kubectl --context "${context_name}" apply -f "${manifest_path}" >/dev/null

kubectl --context "${context_name}" -n opscopilot-demo wait \
  --for=condition=Available deployment/demo-nginx \
  --timeout=120s >/dev/null

kubectl --context "${context_name}" -n opscopilot-demo wait \
  --for=condition=Available deployment/demo-multi \
  --timeout=120s >/dev/null

echo "kind workloads ready in namespace opscopilot-demo"
kubectl --context "${context_name}" -n opscopilot-demo get pods

#!/usr/bin/env bash
set -euo pipefail

if ! command -v kind >/dev/null 2>&1; then
  echo "kind is required" >&2
  exit 1
fi

cluster_name="${KIND_CLUSTER_NAME:-opscopilot-local}"

if kind get clusters | grep -q "^${cluster_name}$"; then
  kind delete cluster --name "${cluster_name}"
fi

echo "kind cluster removed: ${cluster_name}"

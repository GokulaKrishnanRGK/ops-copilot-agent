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

if ! kind get clusters | grep -q "^${cluster_name}$"; then
  kind create cluster --name "${cluster_name}"
fi

kubectl config use-context "${context_name}" >/dev/null

for _ in {1..30}; do
  if kubectl --context "${context_name}" get serviceaccount default >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if ! kubectl --context "${context_name}" get serviceaccount default >/dev/null 2>&1; then
  echo "kind cluster default serviceaccount not ready for context ${context_name}" >&2
  exit 1
fi

echo "kind cluster ready: ${cluster_name}"

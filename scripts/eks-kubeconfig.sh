#!/usr/bin/env bash
set -euo pipefail

if ! command -v aws >/dev/null 2>&1; then
  echo "aws CLI is required" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

tf_env="${TF_ENV:-dev}"
tf_vars_file="${TF_VARS_FILE:-deploy/terraform/environments/${tf_env}.tfvars}"
tf_state_key="${TF_STATE_KEY:-ops-copilot/${tf_env}/terraform.tfstate}"

cluster_name="${EKS_CLUSTER_NAME:-}"

if [ -z "${cluster_name}" ]; then
  tf_output_json="$(
    TF_ENV="${tf_env}" \
    TF_VARS_FILE="${tf_vars_file}" \
    TF_STATE_KEY="${tf_state_key}" \
    bash "${repo_root}/scripts/terraform.sh" output
  )"
  if ! printf "%s" "${tf_output_json}" | jq -e . >/dev/null 2>&1; then
    echo "terraform output did not return valid JSON; run 'make tf-output' and resolve errors first." >&2
    exit 1
  fi
  cluster_name="$(printf "%s" "${tf_output_json}" | jq -r '.eks.value.cluster_name // empty')"
fi

if [ -z "${cluster_name}" ]; then
  echo "EKS cluster name is required. Set EKS_CLUSTER_NAME or apply Terraform to populate output.eks.cluster_name." >&2
  exit 1
fi

region="${EKS_AWS_REGION:-${AWS_REGION:-}}"
if [ -z "${region}" ]; then
  region="$(printf "%s" "${tf_output_json:-}" | jq -r '.helm_values.value.global.awsRegion // empty')"
fi
if [ -z "${region}" ]; then
  echo "AWS region is required. Set EKS_AWS_REGION or AWS_REGION." >&2
  exit 1
fi

args=(eks update-kubeconfig --name "${cluster_name}" --region "${region}")

if [ -n "${AWS_PROFILE:-}" ]; then
  args+=(--profile "${AWS_PROFILE}")
fi

if [ -n "${KUBECONFIG_PATH:-}" ]; then
  args+=(--kubeconfig "${KUBECONFIG_PATH}")
fi

aws "${args[@]}"

echo "kubeconfig updated for cluster=${cluster_name} region=${region}"
if command -v kubectl >/dev/null 2>&1; then
  echo "current context: $(kubectl config current-context 2>/dev/null || echo '<unavailable>')"
fi

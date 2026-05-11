#!/usr/bin/env bash
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

obs_values_out="${HELM_OBSERVABILITY_VALUES_OUT:-${repo_root}/deploy/helm/observability/values-eks.generated.yaml}"
mkdir -p "$(dirname "${obs_values_out}")"

tf_output_json="$({
  TF_ENV="${TF_ENV:-dev}" \
  TF_VARS_FILE="${TF_VARS_FILE:-deploy/terraform/environments/${TF_ENV:-dev}.tfvars}" \
  TF_STATE_KEY="${TF_STATE_KEY:-ops-copilot/${TF_ENV:-dev}/terraform.tfstate}" \
  bash "${repo_root}/scripts/terraform.sh" output
})"

if ! printf "%s" "${tf_output_json}" | jq -e . >/dev/null 2>&1; then
  echo "terraform output did not return valid JSON; run 'make tf-output' and resolve errors first." >&2
  exit 1
fi

json_get() {
  local expr="$1"
  printf "%s" "${tf_output_json}" | jq -r "${expr} // empty"
}

grafana_domain="$(json_get '.dns_contract.value.observability_domain_name')"
langfuse_domain="$(json_get '.dns_contract.value.langfuse_domain_name')"
langfuse_secret_name="$(json_get '.helm_secret_refs.value.api.langfuse.secretName')"

if [ -z "${grafana_domain}" ]; then
  echo "missing observability_domain_name from Terraform dns_contract output" >&2
  exit 1
fi

{
  echo "terraform:"
  echo "  helmValues:"
  echo "    observability:"
  echo "      grafana:"
  echo "        domainName: \"${grafana_domain}\""
  if [ -n "${langfuse_domain}" ]; then
    echo "    langfuse:"
    echo "      domainName: \"${langfuse_domain}\""
  fi
  echo "  dnsContract:"
  echo "    observability_domain_name: \"${grafana_domain}\""
  if [ -n "${langfuse_domain}" ]; then
    echo "    langfuse_domain_name: \"${langfuse_domain}\""
  fi
  if [ -n "${langfuse_secret_name}" ]; then
    echo "langfuse:"
    echo "  app:"
    echo "    nextauthUrl: \"https://${langfuse_domain}\""
    echo "  secretRefs:"
    echo "    publicKeySecret: \"${langfuse_secret_name}\""
    echo "    secretKeySecret: \"${langfuse_secret_name}\""
  fi
} >"${obs_values_out}"

echo "generated ${obs_values_out}"

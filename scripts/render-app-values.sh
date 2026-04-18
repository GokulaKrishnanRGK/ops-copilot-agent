#!/usr/bin/env bash
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "jq is required" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

app_values_out="${HELM_APP_VALUES_OUT:-${repo_root}/deploy/helm/opscopilot/values-eks.generated.yaml}"
mkdir -p "$(dirname "${app_values_out}")"

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

contract_version="$(json_get '.terraform_output_contract_version.value')"
if [ -z "${contract_version}" ]; then
  contract_version="v1"
fi

aws_region="$(json_get '.helm_values.value.global.awsRegion')"
api_repo="$(json_get '.helm_values.value.images.apiRepository')"
web_repo="$(json_get '.helm_values.value.images.webRepository')"
tool_repo="$(json_get '.helm_values.value.images.toolServerRepository')"
opensearch_url="$(json_get '.helm_values.value.api.env.opensearchUrl')"
opensearch_index="$(json_get '.helm_values.value.api.env.opensearchIndex')"
python_registry_url="$(json_get '.helm_values.value.artifacts.pythonPackageRegistryUrl')"
ingress_domain="$(json_get '.dns_contract.value.ingress_domain_name')"
observability_domain="$(json_get '.dns_contract.value.observability_domain_name')"
route53_zone_id="$(json_get '.dns_contract.value.route53_hosted_zone_id')"
acm_cert_arn="$(json_get '.dns_contract.value.acm_certificate_arn')"
db_secret_name="$(json_get '.helm_secret_refs.value.api.database.secretName')"
os_user_secret="$(json_get '.helm_secret_refs.value.api.opensearch.usernameSecretName')"
os_pass_secret="$(json_get '.helm_secret_refs.value.api.opensearch.passwordSecretName')"
api_irsa_role_arn="$(json_get '.helm_values.value.controllers.api.roleArn')"
api_sa_name="$(json_get '.controllers.value.api.service_account_name')"

if [ -z "${aws_region}" ] || [ -z "${api_repo}" ] || [ -z "${web_repo}" ] || [ -z "${tool_repo}" ]; then
  echo "missing required Terraform outputs for app chart values" >&2
  exit 1
fi

image_tag="${IMAGE_TAG:-dev}"
log_level="${LOG_LEVEL:-INFO}"
allowed_namespaces_csv="${K8S_ALLOWED_NAMESPACES:-default}"
api_log_file="/tmp/opscopilot-api.log"
tool_server_log_file="/tmp/opscopilot-tool-server.log"
llm_model_id="${LLM_MODEL_ID:-}"
bedrock_embedding_model_id="${BEDROCK_EMBEDDING_MODEL_ID:-}"
bedrock_region="${BEDROCK_REGION:-${aws_region}}"
runtime_secret_name="${RUNTIME_SECRET_NAME:-opscopilot-runtime-secrets}"
otel_endpoint="${OTEL_EXPORTER_OTLP_ENDPOINT:-http://otel-collector.observability.svc.cluster.local:4318}"
otel_protocol="${OTEL_EXPORTER_OTLP_PROTOCOL:-http/protobuf}"
api_otel_service_name="${OTEL_SERVICE_NAME_API:-ops-copilot-api}"
tool_otel_service_name="${OTEL_SERVICE_NAME_TOOL_SERVER:-ops-copilot-tool-server}"

if [ -z "${llm_model_id}" ]; then
  echo "LLM_MODEL_ID is required (export it before running helm-app-values-generate/helm-app-up)." >&2
  exit 1
fi
if [ -z "${bedrock_embedding_model_id}" ]; then
  echo "BEDROCK_EMBEDDING_MODEL_ID is required." >&2
  exit 1
fi
if [ -z "${bedrock_region}" ]; then
  echo "BEDROCK_REGION (or AWS region) is required." >&2
  exit 1
fi

if [ -n "${python_registry_url}" ] && [ "${python_registry_url}" != "null" ]; then
  python_registry_enabled="true"
else
  python_registry_enabled="false"
  python_registry_url=""
fi

if [ -n "${ingress_domain}" ] && [ "${ingress_domain}" != "null" ]; then
  ingress_enabled="true"
else
  ingress_enabled="false"
  ingress_domain=""
fi

{
  echo "global:"
  echo "  imageTag: \"${image_tag}\""
  echo "  logLevel: \"${log_level}\""
  echo
  echo "ingress:"
  echo "  enabled: ${ingress_enabled}"
  echo
  echo "toolServer:"
  echo "  env:"
  echo "    TOOL_SERVER_LOG_FILE: \"${tool_server_log_file}\""
  echo "    K8S_ALLOWED_NAMESPACES: \"${allowed_namespaces_csv}\""
  echo "    OTEL_EXPORTER_OTLP_ENDPOINT: \"${otel_endpoint}\""
  echo "    OTEL_EXPORTER_OTLP_PROTOCOL: \"${otel_protocol}\""
  echo "    OTEL_SERVICE_NAME: \"${tool_otel_service_name}\""
  echo "  rbac:"
  echo "    allowedNamespaces:"
  IFS=',' read -r -a allowed_ns_array <<< "${allowed_namespaces_csv}"
  any_ns=0
  for ns in "${allowed_ns_array[@]}"; do
    trimmed="$(echo "${ns}" | xargs)"
    if [ -n "${trimmed}" ]; then
      any_ns=1
      echo "      - \"${trimmed}\""
    fi
  done
  if [ "${any_ns}" -eq 0 ]; then
    echo "      - \"default\""
  fi
  echo
  echo "artifacts:"
  echo "  pythonPackageRegistry:"
  echo "    enabled: ${python_registry_enabled}"
  if [ "${python_registry_enabled}" = "true" ]; then
    echo "    indexUrl: \"${python_registry_url}\""
  fi
  echo
  echo "terraform:"
  echo "  outputContractVersion: \"${contract_version}\""
  echo "  helmValues:"
  echo "    global:"
  echo "      awsRegion: \"${aws_region}\""
  echo "    images:"
  echo "      apiRepository: \"${api_repo}\""
  echo "      webRepository: \"${web_repo}\""
  echo "      toolServerRepository: \"${tool_repo}\""
  echo "    api:"
  echo "      env:"
  echo "        opensearchUrl: \"${opensearch_url}\""
  echo "        opensearchIndex: \"${opensearch_index}\""
  echo "    artifacts:"
  if [ "${python_registry_enabled}" = "true" ]; then
    echo "      pythonPackageRegistryUrl: \"${python_registry_url}\""
  else
    echo "      pythonPackageRegistryUrl: \"\""
  fi
  echo "    ingress:"
  echo "      domainName: \"${ingress_domain}\""
  echo "      tls:"
  echo "        certificateArn: \"${acm_cert_arn}\""
  echo "    observability:"
  echo "      grafana:"
  echo "        domainName: \"${observability_domain}\""
  echo "        tls:"
  echo "          certificateArn: \"${acm_cert_arn}\""
  echo "  helmSecretRefs:"
  echo "    api:"
  echo "      database:"
  echo "        secretName: \"${db_secret_name}\""
  echo "      opensearch:"
  echo "        usernameSecretName: \"${os_user_secret}\""
  echo "        passwordSecretName: \"${os_pass_secret}\""
  echo "  dnsContract:"
  echo "    ingress_domain_name: \"${ingress_domain}\""
  echo "    observability_domain_name: \"${observability_domain}\""
  echo "    route53_hosted_zone_id: \"${route53_zone_id}\""
  echo "    acm_certificate_arn: \"${acm_cert_arn}\""
  echo
  echo "api:"
  echo "  serviceAccount:"
  echo "    create: true"
  if [ -n "${api_sa_name}" ] && [ "${api_sa_name}" != "null" ]; then
    echo "    name: \"${api_sa_name}\""
  else
    echo "    name: \"api\""
  fi
  if [ -n "${api_irsa_role_arn}" ] && [ "${api_irsa_role_arn}" != "null" ]; then
    echo "    annotations:"
    echo "      eks.amazonaws.com/role-arn: \"${api_irsa_role_arn}\""
  else
    echo "    annotations: {}"
  fi
  echo "  serviceAlias:"
  echo "    enabled: true"
  echo "    name: \"api\""
  echo "  env:"
  echo "    API_LOG_FILE: \"${api_log_file}\""
  echo "    OTEL_EXPORTER_OTLP_ENDPOINT: \"${otel_endpoint}\""
  echo "    OTEL_EXPORTER_OTLP_PROTOCOL: \"${otel_protocol}\""
  echo "    OTEL_SERVICE_NAME: \"${api_otel_service_name}\""
  echo "    LLM_MODEL_ID: \"${llm_model_id}\""
  echo "    BEDROCK_EMBEDDING_MODEL_ID: \"${bedrock_embedding_model_id}\""
  echo "    BEDROCK_REGION: \"${bedrock_region}\""
} >"${app_values_out}"

echo "generated ${app_values_out}"

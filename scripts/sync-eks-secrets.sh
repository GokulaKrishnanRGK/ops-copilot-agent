#!/usr/bin/env bash
set -euo pipefail

for cmd in aws jq kubectl; do
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "${cmd} is required" >&2
    exit 1
  fi
done

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="${ENV_FILE:-${repo_root}/.env}"

tf_env="${TF_ENV:-dev}"
tf_vars_file="${TF_VARS_FILE:-deploy/terraform/environments/${tf_env}.tfvars}"
tf_state_key="${TF_STATE_KEY:-ops-copilot/${tf_env}/terraform.tfstate}"
namespace="${HELM_APP_NAMESPACE:-opscopilot}"

aws_args=()
if [ -n "${AWS_REGION:-}" ]; then
  aws_args+=(--region "${AWS_REGION}")
fi
if [ -n "${AWS_PROFILE:-}" ]; then
  aws_args+=(--profile "${AWS_PROFILE}")
fi

if [ -f "${env_file}" ]; then
  # shellcheck disable=SC1090
  source "${repo_root}/scripts/load-env.sh" "${env_file}"
fi

tf_output_json="$({
  TF_ENV="${tf_env}" \
  TF_VARS_FILE="${tf_vars_file}" \
  TF_STATE_KEY="${tf_state_key}" \
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

db_secret_name="$(json_get '.helm_secret_refs.value.api.database.secretName')"
db_secret_arn="$(json_get '.helm_secret_refs.value.api.database.secretArn')"
os_user_secret_name="$(json_get '.helm_secret_refs.value.api.opensearch.usernameSecretName')"
os_pass_secret_name="$(json_get '.helm_secret_refs.value.api.opensearch.passwordSecretName')"
langfuse_secret_name="$(json_get '.helm_secret_refs.value.api.langfuse.secretName')"

if [ -z "${db_secret_name}" ] || [ -z "${os_user_secret_name}" ] || [ -z "${os_pass_secret_name}" ]; then
  echo "missing required Terraform secret reference outputs" >&2
  exit 1
fi

rds_db_name="$(json_get '.rds.value.database_name')"
rds_endpoint="$(json_get '.rds.value.endpoint')"
rds_port="$(json_get '.rds.value.port')"
rds_username_default="$(json_get '.rds.value.username')"

kubectl get namespace "${namespace}" >/dev/null 2>&1 || kubectl create namespace "${namespace}" >/dev/null

# DB: Terraform/RDS managed secret is JSON. Convert it into DATABASE_URL key for app chart.
db_source_secret_id="${db_secret_name}"
if [ -n "${db_secret_arn}" ]; then
  db_source_secret_id="${db_secret_arn}"
fi
db_secret_string="$(aws "${aws_args[@]}" secretsmanager get-secret-value --secret-id "${db_source_secret_id}" --query SecretString --output text)"

db_username="$(printf "%s" "${db_secret_string}" | jq -r '.username // empty')"
db_password="$(printf "%s" "${db_secret_string}" | jq -r '.password // empty')"
db_host="$(printf "%s" "${db_secret_string}" | jq -r '.host // empty')"
db_port="$(printf "%s" "${db_secret_string}" | jq -r '.port // empty')"
db_name="$(printf "%s" "${db_secret_string}" | jq -r '.dbname // empty')"

if [ -z "${db_username}" ]; then db_username="${rds_username_default}"; fi
if [ -z "${db_host}" ]; then db_host="${rds_endpoint}"; fi
if [ -z "${db_port}" ]; then db_port="${rds_port}"; fi
if [ -z "${db_name}" ]; then db_name="${rds_db_name}"; fi

if [ -z "${db_username}" ] || [ -z "${db_password}" ] || [ -z "${db_host}" ] || [ -z "${db_port}" ] || [ -z "${db_name}" ]; then
  echo "incomplete database secret material from AWS Secrets Manager" >&2
  exit 1
fi

enc_user="$(jq -rn --arg v "${db_username}" '$v|@uri')"
enc_pass="$(jq -rn --arg v "${db_password}" '$v|@uri')"
database_url="postgresql+psycopg://${enc_user}:${enc_pass}@${db_host}:${db_port}/${db_name}"

kubectl -n "${namespace}" create secret generic "${db_secret_name}" \
  --from-literal=DATABASE_URL="${database_url}" \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null

# OpenSearch username/password are stored as plain strings in separate secrets.
os_user_value="$(aws "${aws_args[@]}" secretsmanager get-secret-value --secret-id "${os_user_secret_name}" --query SecretString --output text)"
os_pass_value="$(aws "${aws_args[@]}" secretsmanager get-secret-value --secret-id "${os_pass_secret_name}" --query SecretString --output text)"

kubectl -n "${namespace}" create secret generic "${os_user_secret_name}" \
  --from-literal=username="${os_user_value}" \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null

kubectl -n "${namespace}" create secret generic "${os_pass_secret_name}" \
  --from-literal=password="${os_pass_value}" \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null

if [ -n "${langfuse_secret_name}" ]; then
  langfuse_secret_string="$(aws "${aws_args[@]}" secretsmanager get-secret-value --secret-id "${langfuse_secret_name}" --query SecretString --output text)"
  langfuse_public_key="$(printf "%s" "${langfuse_secret_string}" | jq -r '.LANGFUSE_PUBLIC_KEY // empty')"
  langfuse_secret_key="$(printf "%s" "${langfuse_secret_string}" | jq -r '.LANGFUSE_SECRET_KEY // empty')"
  for ns in "${namespace}" "${HELM_OBSERVABILITY_NAMESPACE:-observability}"; do
    kubectl get namespace "${ns}" >/dev/null 2>&1 || continue
    kubectl -n "${ns}" create secret generic "${langfuse_secret_name}" \
      --from-literal=LANGFUSE_PUBLIC_KEY="${langfuse_public_key}" \
      --from-literal=LANGFUSE_SECRET_KEY="${langfuse_secret_key}" \
      --dry-run=client -o yaml | kubectl apply -f - >/dev/null
  done
fi

echo "synced Kubernetes secrets in namespace=${namespace}"
echo "- ${db_secret_name} (DATABASE_URL)"
echo "- ${os_user_secret_name} (username)"
echo "- ${os_pass_secret_name} (password)"
if [ -n "${langfuse_secret_name}" ]; then
  echo "- ${langfuse_secret_name} (LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY)"
fi

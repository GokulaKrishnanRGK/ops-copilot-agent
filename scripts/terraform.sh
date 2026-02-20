#!/usr/bin/env bash
set -euo pipefail

if ! command -v terraform >/dev/null 2>&1; then
  echo "terraform is required" >&2
  exit 1
fi

action="${1:-}"
if [ -z "${action}" ]; then
  echo "usage: $0 <init|plan|apply|destroy|output|fmt|validate>" >&2
  exit 1
fi

tf_dir="deploy/terraform"
tf_env="${TF_ENV:-dev}"
tf_vars_file="${TF_VARS_FILE:-${tf_dir}/environments/${tf_env}.tfvars}"
tf_state_key="${TF_STATE_KEY:-ops-copilot/${tf_env}/terraform.tfstate}"
tf_auto_approve="${TF_AUTO_APPROVE:-0}"

resolve_var_file() {
  local candidate="$1"
  if [ -z "${candidate}" ]; then
    return 0
  fi
  if [ -f "${candidate}" ]; then
    printf "%s" "${candidate}"
    return 0
  fi
  if [ -f "${tf_dir}/${candidate}" ]; then
    printf "%s" "${tf_dir}/${candidate}"
    return 0
  fi
}

var_file_path="$(resolve_var_file "${tf_vars_file}")"
var_file_abs=""
if [ -n "${var_file_path}" ]; then
  var_file_abs="$(cd "$(dirname "${var_file_path}")" && pwd)/$(basename "${var_file_path}")"
fi

cd "${tf_dir}"

init_backend_args=()
if [ -n "${TF_BACKEND_BUCKET:-}" ]; then
  init_backend_args+=("-backend-config=bucket=${TF_BACKEND_BUCKET}")
  if [ -n "${TF_BACKEND_REGION:-}" ]; then
    init_backend_args+=("-backend-config=region=${TF_BACKEND_REGION}")
  fi
  if [ -n "${TF_BACKEND_DYNAMODB_TABLE:-}" ]; then
    init_backend_args+=("-backend-config=dynamodb_table=${TF_BACKEND_DYNAMODB_TABLE}")
  fi
  if [ -n "${tf_state_key}" ]; then
    init_backend_args+=("-backend-config=key=${tf_state_key}")
  fi
fi

run_init() {
  if [ "${#init_backend_args[@]}" -gt 0 ]; then
    terraform init -reconfigure "${init_backend_args[@]}"
  else
    terraform init -reconfigure
  fi
}

plan_args=()
if [ -n "${var_file_abs}" ]; then
  plan_args+=("-var-file=${var_file_abs}")
fi

case "${action}" in
  init)
    run_init
    ;;
  plan)
    run_init
    if [ "${#plan_args[@]}" -gt 0 ]; then
      terraform plan "${plan_args[@]}"
    else
      terraform plan
    fi
    ;;
  apply)
    run_init
    if [ "${tf_auto_approve}" = "1" ]; then
      if [ "${#plan_args[@]}" -gt 0 ]; then
        terraform apply -auto-approve "${plan_args[@]}"
      else
        terraform apply -auto-approve
      fi
    else
      if [ "${#plan_args[@]}" -gt 0 ]; then
        terraform apply "${plan_args[@]}"
      else
        terraform apply
      fi
    fi
    ;;
  destroy)
    run_init
    if [ "${tf_auto_approve}" = "1" ]; then
      if [ "${#plan_args[@]}" -gt 0 ]; then
        terraform destroy -auto-approve "${plan_args[@]}"
      else
        terraform destroy -auto-approve
      fi
    else
      if [ "${#plan_args[@]}" -gt 0 ]; then
        terraform destroy "${plan_args[@]}"
      else
        terraform destroy
      fi
    fi
    ;;
  output)
    run_init >/dev/null
    terraform output -json
    ;;
  fmt)
    terraform fmt -recursive -check
    ;;
  validate)
    run_init
    terraform validate
    ;;
  *)
    echo "unsupported action: ${action}" >&2
    exit 1
    ;;
esac

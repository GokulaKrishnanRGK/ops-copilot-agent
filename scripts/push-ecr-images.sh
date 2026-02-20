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
if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

tf_env="${TF_ENV:-dev}"
tf_vars_file="${TF_VARS_FILE:-deploy/terraform/environments/${tf_env}.tfvars}"
tf_state_key="${TF_STATE_KEY:-ops-copilot/${tf_env}/terraform.tfstate}"
image_tag="${IMAGE_TAG:-dev}"

aws_region="${AWS_REGION:-}"
if [ -z "${aws_region}" ]; then
  echo "AWS_REGION is required" >&2
  exit 1
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

api_repo="$(printf "%s" "${tf_output_json}" | jq -r '.artifacts.value.ecr_repository_urls.api // empty')"
web_repo="$(printf "%s" "${tf_output_json}" | jq -r '.artifacts.value.ecr_repository_urls.web // empty')"
tool_repo="$(printf "%s" "${tf_output_json}" | jq -r '.artifacts.value.ecr_repository_urls.tool_server // empty')"

if [ -z "${api_repo}" ] || [ -z "${web_repo}" ] || [ -z "${tool_repo}" ]; then
  echo "missing ECR repository outputs from Terraform" >&2
  exit 1
fi

aws_profile_args=()
if [ -n "${AWS_PROFILE:-}" ]; then
  aws_profile_args+=(--profile "${AWS_PROFILE}")
fi

aws_account_id="$(aws "${aws_profile_args[@]}" sts get-caller-identity --query Account --output text)"
aws ecr get-login-password --region "${aws_region}" "${aws_profile_args[@]}" | \
  docker login --username AWS --password-stdin "${aws_account_id}.dkr.ecr.${aws_region}.amazonaws.com"

docker build -f "${repo_root}/apps/api/Dockerfile" -t "${api_repo}:${image_tag}" "${repo_root}"
docker build -f "${repo_root}/apps/web/Dockerfile" -t "${web_repo}:${image_tag}" "${repo_root}"
docker build -f "${repo_root}/apps/tool-server/Dockerfile" -t "${tool_repo}:${image_tag}" "${repo_root}/apps/tool-server"

push_with_retry() {
  local image_ref="$1"
  local attempts="${ECR_PUSH_RETRIES:-5}"
  local delay_seconds=5
  local attempt=1

  while [ "${attempt}" -le "${attempts}" ]; do
    if docker push "${image_ref}"; then
      return 0
    fi
    if [ "${attempt}" -eq "${attempts}" ]; then
      echo "failed to push ${image_ref} after ${attempts} attempts" >&2
      return 1
    fi
    echo "push failed for ${image_ref} (attempt ${attempt}/${attempts}); retrying in ${delay_seconds}s..." >&2
    sleep "${delay_seconds}"
    delay_seconds=$((delay_seconds * 1))
    attempt=$((attempt + 1))
  done
}

push_with_retry "${api_repo}:${image_tag}"
push_with_retry "${web_repo}:${image_tag}"
push_with_retry "${tool_repo}:${image_tag}"

echo "pushed images with tag=${image_tag}"
echo "api: ${api_repo}:${image_tag}"
echo "web: ${web_repo}:${image_tag}"
echo "tool-server: ${tool_repo}:${image_tag}"

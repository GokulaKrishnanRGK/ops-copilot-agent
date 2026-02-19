#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

if ! command -v python >/dev/null 2>&1; then
  echo "python is required" >&2
  exit 1
fi
if ! command -v twine >/dev/null 2>&1; then
  echo "twine is required" >&2
  exit 1
fi

mode="${1:-publish}"
if [ "${mode}" != "build" ] && [ "${mode}" != "publish" ]; then
  echo "usage: $0 <build|publish>" >&2
  exit 1
fi

packages=(
  "packages/observability"
  "packages/db"
  "packages/llm-gateway"
  "packages/rag"
  "packages/tools"
  "packages/agent-runtime"
)

build_packages() {
  for pkg_dir in "${packages[@]}"; do
    echo "building ${pkg_dir}"
    (
      cd "${pkg_dir}"
      rm -rf dist build *.egg-info
      python -m build
    )
  done
}

if [ "${mode}" = "build" ]; then
  build_packages
  exit 0
fi

if [ -z "${PYTHON_PACKAGE_REGISTRY_URL:-}" ]; then
  echo "PYTHON_PACKAGE_REGISTRY_URL is required for publish mode" >&2
  exit 1
fi

if [ -z "${CODEARTIFACT_AUTH_TOKEN:-}" ]; then
  if ! command -v aws >/dev/null 2>&1; then
    echo "CODEARTIFACT_AUTH_TOKEN is unset and aws CLI is unavailable to fetch one" >&2
    exit 1
  fi
  if [ -z "${CODEARTIFACT_DOMAIN:-}" ] || [ -z "${CODEARTIFACT_DOMAIN_OWNER:-}" ]; then
    echo "Set CODEARTIFACT_AUTH_TOKEN or provide CODEARTIFACT_DOMAIN and CODEARTIFACT_DOMAIN_OWNER" >&2
    exit 1
  fi
  echo "fetching CodeArtifact auth token"
  CODEARTIFACT_AUTH_TOKEN="$(aws codeartifact get-authorization-token \
    --domain "${CODEARTIFACT_DOMAIN}" \
    --domain-owner "${CODEARTIFACT_DOMAIN_OWNER}" \
    --query authorizationToken \
    --output text)"
  export CODEARTIFACT_AUTH_TOKEN
fi

build_packages

export TWINE_USERNAME="aws"
export TWINE_PASSWORD="${CODEARTIFACT_AUTH_TOKEN}"

for pkg_dir in "${packages[@]}"; do
  echo "publishing ${pkg_dir}"
  (
    cd "${pkg_dir}"
    twine upload --repository-url "${PYTHON_PACKAGE_REGISTRY_URL}" dist/*
  )
done


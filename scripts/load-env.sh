__load_env_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
__load_env_repo_root="$(cd "${__load_env_script_dir}/" && pwd)"
ENV_FILE="${1:-${__load_env_repo_root}/.env}"
if [ ! -f "${ENV_FILE}" ]; then
  echo "missing env file: ${ENV_FILE}" >&2
  return 1 2>/dev/null || exit 1
fi
set -a
. "${ENV_FILE}"
set +a
unset __load_env_script_dir
unset __load_env_repo_root

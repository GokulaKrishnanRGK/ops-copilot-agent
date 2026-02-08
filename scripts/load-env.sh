script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/" && pwd)"
ENV_FILE="${1:-${repo_root}/.env}"
if [ ! -f "$ENV_FILE" ]; then
  echo "missing env file: $ENV_FILE" >&2
  return 1 2>/dev/null || exit 1
fi
set -a
. "$ENV_FILE"
set +a

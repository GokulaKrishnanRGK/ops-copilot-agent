#!/usr/bin/env bash
set -uo pipefail

if [ "$#" -lt 3 ]; then
  echo "usage: $0 <label> -- <command...>" >&2
  exit 2
fi

label="$1"
shift

if [ "$1" != "--" ]; then
  echo "usage: $0 <label> -- <command...>" >&2
  exit 2
fi
shift

run_dir="${TEST_RUN_DIR:-}"
if [ -z "${run_dir}" ]; then
  run_dir="$(TEST_LOG_ROOT="${TEST_LOG_ROOT:-}" bash ./scripts/new-test-run-dir.sh)"
fi
mkdir -p "${run_dir}"

log_file="${run_dir}/${label}.log"
echo "test log: ${log_file}"

"$@" 2>&1 | tee -a "${log_file}"
status="${PIPESTATUS[0]}"
exit "${status}"

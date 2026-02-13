#!/usr/bin/env bash
set -euo pipefail

root="${TEST_LOG_ROOT:-/Volumes/Work/Projects/logs/opscopilot/tests}"
today="$(date +%F)"
day_dir="${root}/${today}"
mkdir -p "${day_dir}"

index=1
while [ -d "${day_dir}/test-${index}" ]; do
  index=$((index + 1))
done

run_dir="${day_dir}/test-${index}"
mkdir -p "${run_dir}"
echo "${run_dir}"

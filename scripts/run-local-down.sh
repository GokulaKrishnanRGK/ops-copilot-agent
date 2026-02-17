#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

local_postgres="${LOCAL_POSTGRES:-1}"
local_opensearch="${LOCAL_OPENSEARCH:-1}"
local_otel="${LOCAL_OTEL:-1}"

compose_files=(
  "deploy/compose/app.yml"
  "deploy/compose/tool-server.yml"
)
if [ "$local_postgres" = "1" ]; then
  compose_files+=("deploy/compose/postgres.yml")
fi
if [ "$local_opensearch" = "1" ]; then
  compose_files+=("deploy/compose/opensearch.yml")
fi
if [ "$local_otel" = "1" ]; then
  compose_files+=("deploy/compose/observability.yml")
fi

compose_cmd=(docker compose --env-file .env)
for file in "${compose_files[@]}"; do
  compose_cmd+=(-f "$file")
done

"${compose_cmd[@]}" down

#!/usr/bin/env bash
set -euo pipefail

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

api_base="${SMOKE_API_BASE_URL:-http://localhost:8000/api}"
prompt="${SMOKE_PROMPT:-List the Kubernetes pods in namespace default and report their status.}"
tmp_dir="$(mktemp -d)"
stream_file="${tmp_dir}/stream.sse"

cleanup() {
  rm -rf "${tmp_dir}"
}
trap cleanup EXIT

wait_http() {
  local name="$1"
  local url="$2"
  local timeout_seconds="$3"
  local elapsed=0
  while [ "$elapsed" -lt "$timeout_seconds" ]; do
    if curl -sf "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  echo "smoke failed: ${name} not ready (${url})" >&2
  return 1
}

wait_http "api" "http://localhost:8000/health" 120
wait_http "tool-server" "http://localhost:8080/health" 120

create_response="$(
  curl -fsS \
    -H "Content-Type: application/json" \
    -d '{"title":"Local Smoke Session"}' \
    "${api_base}/sessions"
)"

session_id="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"${create_response}")"
if [ -z "${session_id}" ]; then
  echo "smoke failed: empty session id" >&2
  exit 1
fi

chat_payload="$(
  SMOKE_PROMPT_VALUE="${prompt}" python3 -c 'import json,os; print(json.dumps({"message": os.environ["SMOKE_PROMPT_VALUE"]}))'
)"

curl -fsS -N \
  -H "Content-Type: application/json" \
  -d "${chat_payload}" \
  "${api_base}/sessions/${session_id}/chat/stream" > "${stream_file}"

if grep -q "event: agent_run.failed" "${stream_file}"; then
  echo "smoke failed: agent_run.failed in stream" >&2
  sed -n '1,220p' "${stream_file}" >&2
  exit 1
fi
if ! grep -q "event: agent_run.completed" "${stream_file}"; then
  echo "smoke failed: missing agent_run.completed in stream" >&2
  sed -n '1,220p' "${stream_file}" >&2
  exit 1
fi
if ! grep -q "event: assistant.token.delta" "${stream_file}"; then
  echo "smoke failed: missing assistant.token.delta in stream" >&2
  sed -n '1,220p' "${stream_file}" >&2
  exit 1
fi

run_id="$(
  python3 - "${stream_file}" <<'PY'
import json
import sys

path = sys.argv[1]
event_type = None
with open(path, "r", encoding="utf-8") as handle:
    for raw in handle:
        line = raw.strip()
        if line.startswith("event: "):
            event_type = line[len("event: "):]
            continue
        if event_type == "agent_run.started" and line.startswith("data: "):
            payload = json.loads(line[len("data: "):])
            run_id = payload.get("agent_run_id")
            if isinstance(run_id, str) and run_id:
                print(run_id)
                sys.exit(0)
print("")
PY
)"

if [ -z "${run_id}" ]; then
  echo "smoke failed: could not extract run id from stream" >&2
  sed -n '1,220p' "${stream_file}" >&2
  exit 1
fi

runs_response="$(curl -fsS "${api_base}/runs?session_id=${session_id}")"
python3 -c '
import json
import sys

run_id = sys.argv[1]
payload = json.load(sys.stdin)
items = payload.get("items")
if not isinstance(items, list) or not items:
    raise SystemExit("smoke failed: runs list is empty")
if not any(isinstance(item, dict) and item.get("id") == run_id for item in items):
    raise SystemExit("smoke failed: run id not found in runs list")
' "${run_id}" <<<"${runs_response}"

messages_response="$(curl -fsS "${api_base}/messages?session_id=${session_id}")"
python3 -c '
import json
import sys

run_id = sys.argv[1]
payload = json.load(sys.stdin)
items = payload.get("items")
if not isinstance(items, list) or len(items) < 2:
    raise SystemExit("smoke failed: expected at least two persisted messages")
assistant_messages = [item for item in items if isinstance(item, dict) and item.get("role") == "assistant"]
if not assistant_messages:
    raise SystemExit("smoke failed: missing persisted assistant message")
if not any(
    isinstance(item.get("metadata_json"), dict) and item["metadata_json"].get("run_id") == run_id
    for item in assistant_messages
):
    raise SystemExit("smoke failed: assistant message missing run_id metadata")
' "${run_id}" <<<"${messages_response}"

tool_success=0
for _ in $(seq 1 20); do
  tool_calls_response="$(curl -fsS "${api_base}/tool-calls?run_id=${run_id}")"
  if python3 -c 'import json,sys; items=json.load(sys.stdin).get("items"); raise SystemExit(0 if isinstance(items, list) and len(items) > 0 else 1)' <<<"${tool_calls_response}"
  then
    tool_success=1
    break
  fi
  sleep 1
done

if [ "${tool_success}" -ne 1 ]; then
  echo "smoke failed: no tool calls persisted for run ${run_id}" >&2
  echo "tip: ensure prompt and scope lead to tool execution in current environment" >&2
  exit 1
fi

echo "smoke-local passed"
echo "session_id=${session_id}"
echo "run_id=${run_id}"

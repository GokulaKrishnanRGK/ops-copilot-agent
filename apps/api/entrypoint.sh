#!/bin/sh
set -e

if [ -n "${LANGFUSE_HOST:-}" ]; then
  echo "startup: pushing prompts to Langfuse at ${LANGFUSE_HOST}"
  if python -m opscopilot_agent_runtime.cli.prompts --prompts-dir /app/prompts; then
    echo "startup: prompts push completed"
  else
    echo "startup: prompts push failed — continuing startup" >&2
  fi

  echo "startup: pushing eval dataset to Langfuse"
  if python -m opscopilot_eval.cli push-dataset \
      --dataset ops-copilot-v1 \
      --datasets-dir /app/datasets; then
    echo "startup: eval dataset push completed"
  else
    echo "startup: eval dataset push failed — continuing startup" >&2
  fi
else
  echo "startup: LANGFUSE_HOST not set, skipping prompts and dataset push"
fi

exec uvicorn opscopilot_api.main:app --host 0.0.0.0 --port 8000

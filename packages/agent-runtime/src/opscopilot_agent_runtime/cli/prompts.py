from __future__ import annotations

import argparse
import os
import sys

from opscopilot_agent_runtime.prompts import push_prompts_to_langfuse


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync local prompt YAML files to Langfuse.")
    parser.add_argument("--prompts-dir", default=os.getenv("PROMPTS_DIR", "prompts"))
    return parser


def run(args: argparse.Namespace) -> int:
    host = os.getenv("LANGFUSE_HOST")
    if host:
        print(f"Pushing prompts to Langfuse at {host}.")
    pushed = push_prompts_to_langfuse(prompts_dir=args.prompts_dir)
    print(f"Pushed {pushed} prompt versions to Langfuse.")
    return 0


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(run(args))
    except Exception as exc:
        print(f"prompts push failed: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()

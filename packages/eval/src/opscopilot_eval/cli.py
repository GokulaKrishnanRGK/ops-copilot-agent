from __future__ import annotations

import argparse
import os
import sys

from opscopilot_eval.datasets import dataset_store_from_env


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Ops Copilot evaluation datasets.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List local datasets")
    list_parser.add_argument("--datasets-dir", default=os.getenv("EVAL_DATASETS_DIR"))

    run_parser = subparsers.add_parser("run", help="Load a local dataset")
    run_parser.add_argument("--dataset", required=True)
    run_parser.add_argument("--datasets-dir", default=os.getenv("EVAL_DATASETS_DIR"))
    return parser


def run(args: argparse.Namespace) -> int:
    store = dataset_store_from_env(datasets_dir=args.datasets_dir)
    if args.command == "list":
        for name in store.list_datasets():
            print(name)
        return 0
    if args.command == "run":
        examples = store.load(args.dataset)
        print(f"Loaded {len(examples)} examples from dataset '{args.dataset}'.")
        return 0
    raise RuntimeError(f"unsupported command: {args.command}")


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(run(args))
    except Exception as exc:
        print(f"eval failed: {exc}", file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import os
import sys

from opscopilot_eval.datasets import dataset_store_from_env
from opscopilot_eval.runner import LangfuseDatasetPusher, LangfuseSdkExperimentRunner


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Ops Copilot evaluation datasets.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List local datasets")
    list_parser.add_argument("--datasets-dir", default=os.getenv("EVAL_DATASETS_DIR"))

    push_parser = subparsers.add_parser("push-dataset", help="Push a dataset to Langfuse without running the app")
    push_parser.add_argument("--dataset", required=True)
    push_parser.add_argument("--datasets-dir", default=os.getenv("EVAL_DATASETS_DIR"))

    run_parser = subparsers.add_parser("run-langfuse", help="Run a Langfuse SDK-only experiment")
    run_parser.add_argument("--dataset", required=True)
    run_parser.add_argument("--experiment-name", default=os.getenv("EVAL_EXPERIMENT_NAME"))
    run_parser.add_argument("--prompt-version", default=os.getenv("LANGFUSE_PROMPT_VERSION", "local"))
    run_parser.add_argument("--model", default=os.getenv("LLM_MODEL_ID", "local"))

    return parser


def run(args: argparse.Namespace) -> int:
    if args.command == "list":
        store = dataset_store_from_env(datasets_dir=args.datasets_dir)
        for name in store.list_datasets():
            print(name)
        return 0
    if args.command == "push-dataset":
        store = dataset_store_from_env(datasets_dir=args.datasets_dir)
        examples = store.load(args.dataset)
        pushed = LangfuseDatasetPusher.from_env().push(args.dataset, examples)
        print(f"Pushed {pushed} examples to Langfuse dataset '{args.dataset}'.")
        return 0
    if args.command == "run-langfuse":
        experiment_name = args.experiment_name or f"{args.dataset}-{args.prompt_version}-{args.model}"
        url = LangfuseSdkExperimentRunner.from_env().run(
            dataset_name=args.dataset,
            experiment_name=experiment_name,
            model=args.model,
            prompt_version=args.prompt_version,
        )
        if url:
            print(f"Langfuse experiment: {url}")
        else:
            print(f"Langfuse experiment '{experiment_name}' completed.")
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

from __future__ import annotations

import argparse
import os
import sys

from opscopilot_eval.datasets import dataset_store_from_env
from opscopilot_eval.runner import (
    EvalRunner,
    HttpAgentClient,
    LangfuseExperimentUploader,
    default_summary_path,
    write_summary,
)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run Ops Copilot evaluation datasets.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List local datasets")
    list_parser.add_argument("--datasets-dir", default=os.getenv("EVAL_DATASETS_DIR"))

    run_parser = subparsers.add_parser("run", help="Run a dataset against the agent API")
    run_parser.add_argument("--dataset", required=True)
    run_parser.add_argument("--datasets-dir", default=os.getenv("EVAL_DATASETS_DIR"))
    run_parser.add_argument("--prompt-version", default=os.getenv("LANGFUSE_PROMPT_VERSION", "local"))
    run_parser.add_argument("--model", default=os.getenv("LLM_MODEL_ID", "local"))
    run_parser.add_argument("--api-url", default=os.getenv("EVAL_API_URL"))
    run_parser.add_argument("--experiment-name", default=os.getenv("EVAL_EXPERIMENT_NAME"))
    run_parser.add_argument("--summary-path", default=os.getenv("EVAL_SUMMARY_PATH"))
    return parser


def run(args: argparse.Namespace) -> int:
    store = dataset_store_from_env(datasets_dir=args.datasets_dir)
    if args.command == "list":
        for name in store.list_datasets():
            print(name)
        return 0
    if args.command == "run":
        if not args.api_url:
            raise RuntimeError("EVAL_API_URL or --api-url is required for eval run")
        examples = store.load(args.dataset)
        runner = EvalRunner(
            agent_client=HttpAgentClient(args.api_url),
            experiment_uploader=LangfuseExperimentUploader.from_env(),
        )
        summary = runner.run(
            dataset_name=args.dataset,
            examples=examples,
            prompt_version=args.prompt_version,
            model=args.model,
            experiment_name=args.experiment_name,
        )
        summary_path = args.summary_path or default_summary_path(args.dataset, summary.experiment_name)
        write_summary(summary, summary_path)
        print(f"Ran {summary.total_examples} examples from dataset '{args.dataset}'.")
        print(f"Wrote summary to {summary_path}.")
        if summary.langfuse_experiment_url:
            print(f"Langfuse experiment: {summary.langfuse_experiment_url}")
        else:
            print("Langfuse experiment upload skipped.")
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

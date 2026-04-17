from __future__ import annotations

import json
import os
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class ExampleRecord:
    input: str
    expected_intent: str
    expected_answer_contains: list[str]


class DatasetStore(Protocol):
    def list_datasets(self) -> list[str]: ...

    def load(self, name: str) -> list[ExampleRecord]: ...


class LocalJsonlDatasetStore:
    def __init__(self, datasets_dir: str | Path | None = None) -> None:
        self._datasets_dir = self._resolve_datasets_dir(datasets_dir)

    def list_datasets(self) -> list[str]:
        if not self._datasets_dir.exists():
            return []
        return sorted(path.stem for path in self._datasets_dir.glob("*.jsonl"))

    def load(self, name: str) -> list[ExampleRecord]:
        path = self._datasets_dir / f"{name}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"dataset not found: {name}")

        records: list[ExampleRecord] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            records.append(_parse_record(payload, str(path), line_number))
        return records

    def _resolve_datasets_dir(self, datasets_dir: str | Path | None) -> Path:
        if datasets_dir is not None:
            return Path(datasets_dir)

        for base in (Path.cwd(), *Path(__file__).resolve().parents):
            candidate = base / "packages" / "eval" / "datasets"
            if candidate.exists():
                return candidate

        return Path("packages/eval/datasets")


class S3DatasetStore:
    def __init__(
        self,
        bucket: str,
        prefix: str = "eval/datasets",
        client: Any | None = None,
    ) -> None:
        self._bucket = bucket
        self._prefix = prefix.strip("/")
        self._client = client or _create_s3_client()

    def list_datasets(self) -> list[str]:
        response = self._client.list_objects_v2(
            Bucket=self._bucket,
            Prefix=f"{self._prefix}/",
        )
        names = []
        for item in response.get("Contents", []):
            key = item.get("Key")
            if isinstance(key, str) and key.endswith(".jsonl"):
                names.append(Path(key).stem)
        return sorted(names)

    def load(self, name: str) -> list[ExampleRecord]:
        key = f"{self._prefix}/{name}.jsonl"
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        body = response["Body"].read().decode("utf-8")
        return _parse_jsonl(body, f"s3://{self._bucket}/{key}")


def dataset_store_from_env(
    client: Any | None = None,
    datasets_dir: str | Path | None = None,
) -> DatasetStore:
    bucket = os.getenv("EVAL_DATASET_BUCKET")
    if bucket:
        prefix = os.getenv("EVAL_DATASET_PREFIX", "eval/datasets")
        return S3DatasetStore(bucket=bucket, prefix=prefix, client=client)
    return LocalJsonlDatasetStore(datasets_dir)


def _parse_jsonl(content: str, source: str) -> list[ExampleRecord]:
    records: list[ExampleRecord] = []
    for line_number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        payload = json.loads(line)
        records.append(_parse_record(payload, source, line_number))
    return records


def _create_s3_client() -> Any:
    module = import_module("boto3")
    return module.client("s3")


def _parse_record(payload: object, source: str, line_number: int) -> ExampleRecord:
    if not isinstance(payload, dict):
        raise ValueError(f"{source}:{line_number} must contain a JSON object")

    input_value = payload.get("input")
    expected_intent = payload.get("expected_intent")
    expected_answer_contains = payload.get("expected_answer_contains")

    if not isinstance(input_value, str) or not input_value.strip():
        raise ValueError(f"{source}:{line_number} input is required")
    if not isinstance(expected_intent, str) or not expected_intent.strip():
        raise ValueError(f"{source}:{line_number} expected_intent is required")
    if not isinstance(expected_answer_contains, list) or not all(
        isinstance(item, str) and item.strip() for item in expected_answer_contains
    ):
        raise ValueError(f"{source}:{line_number} expected_answer_contains is required")

    return ExampleRecord(
        input=input_value,
        expected_intent=expected_intent,
        expected_answer_contains=expected_answer_contains,
    )

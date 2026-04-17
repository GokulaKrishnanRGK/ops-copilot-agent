from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


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
            records.append(_parse_record(payload, path, line_number))
        return records

    def _resolve_datasets_dir(self, datasets_dir: str | Path | None) -> Path:
        if datasets_dir is not None:
            return Path(datasets_dir)

        for base in (Path.cwd(), *Path(__file__).resolve().parents):
            candidate = base / "packages" / "eval" / "datasets"
            if candidate.exists():
                return candidate

        return Path("packages/eval/datasets")


def _parse_record(payload: object, path: Path, line_number: int) -> ExampleRecord:
    if not isinstance(payload, dict):
        raise ValueError(f"{path}:{line_number} must contain a JSON object")

    input_value = payload.get("input")
    expected_intent = payload.get("expected_intent")
    expected_answer_contains = payload.get("expected_answer_contains")

    if not isinstance(input_value, str) or not input_value.strip():
        raise ValueError(f"{path}:{line_number} input is required")
    if not isinstance(expected_intent, str) or not expected_intent.strip():
        raise ValueError(f"{path}:{line_number} expected_intent is required")
    if not isinstance(expected_answer_contains, list) or not all(
        isinstance(item, str) and item.strip() for item in expected_answer_contains
    ):
        raise ValueError(f"{path}:{line_number} expected_answer_contains is required")

    return ExampleRecord(
        input=input_value,
        expected_intent=expected_intent,
        expected_answer_contains=expected_answer_contains,
    )

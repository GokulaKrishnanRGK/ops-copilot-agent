import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CostEntry:
    model_id: str
    input_per_1k: float
    output_per_1k: float


def load_cost_table(path: str) -> dict[str, CostEntry]:
    raw = json.loads(Path(path).read_text())
    table: dict[str, CostEntry] = {}
    for item in raw.get("models", []):
        entry = CostEntry(
            model_id=item["model_id"],
            input_per_1k=item["input_per_1k"],
            output_per_1k=item["output_per_1k"],
        )
        table[entry.model_id] = entry
    return table


def estimate_cost_usd(
    table: dict[str, CostEntry],
    model_id: str,
    tokens_input: int,
    tokens_output: int,
) -> float:
    entry = table.get(model_id)
    if entry is None:
        return 0.0
    input_cost = (tokens_input / 1000.0) * entry.input_per_1k
    output_cost = (tokens_output / 1000.0) * entry.output_per_1k
    return input_cost + output_cost

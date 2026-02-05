from dataclasses import dataclass


@dataclass
class CostRecord:
    session_id: str
    agent_run_id: str
    agent_node: str
    model_id: str
    tokens_input: int
    tokens_output: int
    cost_usd: float


class CostLedger:
    def __init__(self):
        self._records: list[CostRecord] = []

    def record(self, record: CostRecord) -> None:
        self._records.append(record)

    def records(self) -> list[CostRecord]:
        return list(self._records)

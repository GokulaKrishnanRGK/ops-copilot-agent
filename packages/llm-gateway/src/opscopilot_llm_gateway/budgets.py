from dataclasses import dataclass


@dataclass
class BudgetState:
    max_usd: float
    total_usd: float

    @property
    def remaining_usd(self) -> float:
        remaining = self.max_usd - self.total_usd
        if remaining < 0:
            return 0.0
        return remaining


class BudgetEnforcer:
    def __init__(self, state: BudgetState):
        self._state = state

    def can_spend(self, amount_usd: float) -> bool:
        return self._state.total_usd + amount_usd <= self._state.max_usd

    def record_spend(self, amount_usd: float) -> None:
        self._state.total_usd += amount_usd

    def state(self) -> BudgetState:
        return self._state

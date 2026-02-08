from opscopilot_llm_gateway.budgets import BudgetEnforcer, BudgetState


def test_budget_remaining():
    state = BudgetState(max_usd=10.0, total_usd=3.0)
    assert state.remaining_usd == 7.0


def test_budget_can_spend():
    state = BudgetState(max_usd=10.0, total_usd=9.0)
    enforcer = BudgetEnforcer(state)
    assert enforcer.can_spend(1.0) is True
    assert enforcer.can_spend(1.1) is False


def test_budget_record_spend():
    state = BudgetState(max_usd=10.0, total_usd=5.0)
    enforcer = BudgetEnforcer(state)
    enforcer.record_spend(2.5)
    assert enforcer.state().total_usd == 7.5

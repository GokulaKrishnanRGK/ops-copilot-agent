from opscopilot_llm_gateway.costs import CostEntry, estimate_cost_usd


def test_estimate_cost_usd_missing_model():
    table: dict[str, CostEntry] = {}
    cost = estimate_cost_usd(table, "m1", 1000, 1000)
    assert cost == 0.0


def test_estimate_cost_usd():
    table = {
        "m1": CostEntry(model_id="m1", input_per_1k=0.01, output_per_1k=0.02)
    }
    cost = estimate_cost_usd(table, "m1", 1000, 2000)
    assert cost == 0.05

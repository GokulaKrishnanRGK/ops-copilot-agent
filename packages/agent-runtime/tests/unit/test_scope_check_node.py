from unittest.mock import patch

import pytest

from opscopilot_agent_runtime.mcp_client import MCPTool
from opscopilot_agent_runtime.nodes.scope_check_node import ScopeCheckNode
from opscopilot_agent_runtime.state import AgentState


class _FakeClassifier:
    def __init__(self, allowed: bool = True, response: str = "ok") -> None:
        self.calls: list[dict] = []
        self._allowed = allowed
        self._response = response

    def classify(self, prompt, tool_names, recorder=None, on_delta=None):
        self.calls.append({"prompt": prompt, "tool_names": tool_names})
        return {"allowed": self._allowed, "response": self._response}


def _tool(name: str) -> MCPTool:
    return MCPTool(name=name, description="", input_schema=None, output_schema=None)


def test_scope_check_passes_current_prompt_only():
    classifier = _FakeClassifier()
    node = ScopeCheckNode(classifier=classifier)
    state = AgentState(
        prompt="list pods",
        prompt_history=["earlier turn 1", "earlier turn 2"],
    )

    node(state)

    assert len(classifier.calls) == 1
    assert classifier.calls[0]["prompt"] == "list pods"


def test_scope_check_prompt_input_independent_of_history_length():
    classifier = _FakeClassifier()
    node = ScopeCheckNode(classifier=classifier)

    short_history = AgentState(prompt="list pods")
    long_history = AgentState(
        prompt="list pods",
        prompt_history=["turn " + str(i) for i in range(20)],
    )

    node(short_history)
    node(long_history)

    assert classifier.calls[0]["prompt"] == classifier.calls[1]["prompt"] == "list pods"


def test_scope_check_passes_tool_names_from_state():
    classifier = _FakeClassifier()
    node = ScopeCheckNode(classifier=classifier)
    state = AgentState(
        prompt="list pods",
        tools=[_tool("k8s.list_pods"), _tool("k8s.describe_pod")],
    )

    node(state)

    assert classifier.calls[0]["tool_names"] == ["k8s.list_pods", "k8s.describe_pod"]


def test_scope_check_allowed_returns_completed_event():
    node = ScopeCheckNode(classifier=_FakeClassifier(allowed=True, response="proceed"))
    result = node(AgentState(prompt="list pods"))

    assert result.error is None
    assert result.event is not None
    assert result.event.event_type == "scope_check.completed"


def test_scope_check_rejected_sets_error_and_answer():
    node = ScopeCheckNode(classifier=_FakeClassifier(allowed=False, response="out of scope"))
    result = node(AgentState(prompt="delete all pods"))

    assert result.error is not None
    assert result.error["type"] == "out_of_scope"
    assert result.answer == "out of scope"
    assert result.event.event_type == "scope_check.rejected"


def test_scope_check_no_classifier_passes_through():
    node = ScopeCheckNode(classifier=None)
    state = AgentState(prompt="list pods")
    result = node(state)
    assert result is state


def test_scope_check_no_prompt_passes_through():
    classifier = _FakeClassifier()
    node = ScopeCheckNode(classifier=classifier)
    state = AgentState(prompt=None)
    result = node(state)
    assert result is state
    assert classifier.calls == []


def test_scope_check_existing_error_passes_through():
    classifier = _FakeClassifier()
    node = ScopeCheckNode(classifier=classifier)
    state = AgentState(prompt="list pods", error={"type": "prior_error"})
    result = node(state)
    assert result is state
    assert classifier.calls == []


def test_scope_check_does_not_perform_rag_retrieval():
    classifier = _FakeClassifier()
    node = ScopeCheckNode(classifier=classifier)
    state = AgentState(prompt="list pods")

    with patch("opscopilot_agent_runtime.nodes.scope_check_node.get_logger"):
        node(state)

    assert state.rag is None

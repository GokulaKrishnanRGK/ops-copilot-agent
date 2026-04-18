import time
from dataclasses import dataclass
from typing import Callable

from langgraph.graph import END, StateGraph
from opentelemetry import trace

from opscopilot_agent_runtime.runtime.logging import get_logger
from opscopilot_agent_runtime.runtime.tracing import _agent_graph_otel_ctx, set_node_observation_attributes
from opscopilot_agent_runtime.state import AgentState
from opscopilot_agent_runtime.runtime.tool_registry import ToolRegistry

_logger = get_logger(__name__)

PlannerFn = Callable[[AgentState], AgentState]
ClarifierFn = Callable[[AgentState], AgentState]
ToolExecutorFn = Callable[[AgentState], AgentState]
CriticFn = Callable[[AgentState], AgentState]
AnswerFn = Callable[[AgentState], AgentState]
ScopeCheckFn = Callable[[AgentState], AgentState]
InjectionGuardFn = Callable[[AgentState], AgentState]

_PROMPT_SNIPPET_LEN = 150


def _prompt_snippet(prompt: str | None) -> str:
    if not prompt:
        return ""
    snippet = prompt[:_PROMPT_SNIPPET_LEN].replace("\n", " ")
    return f"{snippet}…" if len(prompt) > _PROMPT_SNIPPET_LEN else snippet


def _state_in_summary(state: AgentState) -> str:
    parts: list[str] = []
    parts.append(f"prompt_len={len(state.prompt or '')}")
    if state.prompt:
        parts.append(f"prompt={_prompt_snippet(state.prompt)!r}")
    if state.plan and hasattr(state.plan, "steps"):
        tools = [s.tool_name for s in state.plan.steps]
        parts.append(f"plan_steps={len(state.plan.steps)} tools={tools}")
    if state.tool_results:
        parts.append(f"tool_results={len(state.tool_results)}")
    if state.error:
        parts.append(f"error={state.error.get('type')}")
    if state.tools:
        parts.append(f"available_tools={len(state.tools)}")
    return "  ".join(parts)


def _state_out_summary(state: AgentState) -> str:
    parts: list[str] = []
    if state.answer:
        snippet = state.answer[:120].replace("\n", " ")
        suffix = "…" if len(state.answer) > 120 else ""
        parts.append(f"answer_len={len(state.answer)} answer={snippet!r}{suffix}")
    if state.plan and hasattr(state.plan, "steps"):
        tools = [s.tool_name for s in state.plan.steps]
        parts.append(f"plan_steps={len(state.plan.steps)} tools={tools}")
    if state.tool_results:
        parts.append(f"tool_results={len(state.tool_results)}")
    if state.error:
        parts.append(f"error={state.error.get('type')} message={state.error.get('message', '')!r}")
    if state.event:
        parts.append(f"event={state.event.event_type}")
    return "  ".join(parts) if parts else "(no output changes)"


def _wrap(
    node: Callable[[AgentState], AgentState],
    tool_registry: ToolRegistry | None,
    node_name: str = "",
) -> Callable[[dict], dict]:
    label = node_name or type(node).__name__
    tracer = trace.get_tracer("opscopilot_agent_runtime")

    def adapter(state_dict: dict) -> dict:
        state = AgentState.from_dict(state_dict)
        if tool_registry and state.tools is None:
            state = state.merge(tools=tool_registry.list_tools())
        _logger.debug(
            ">>> node.enter  node=%s  %s",
            label,
            _state_in_summary(state),
        )
        t0 = time.perf_counter()
        with tracer.start_as_current_span(f"agent.node.{label}", context=_agent_graph_otel_ctx.get()) as span:
            updated = node(state)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            set_node_observation_attributes(span, state, updated, label, elapsed_ms)
        _logger.debug(
            "<<< node.exit   node=%s  elapsed_ms=%.1f  %s",
            label,
            elapsed_ms,
            _state_out_summary(updated),
        )
        return updated.to_dict()

    return adapter


@dataclass(frozen=True)
class AgentGraph:
    planner: PlannerFn
    tool_executor: ToolExecutorFn
    scope_check: ScopeCheckFn | None = None
    clarifier: ClarifierFn | None = None
    answer: AnswerFn | None = None
    critic: CriticFn | None = None
    tool_registry: ToolRegistry | None = None
    injection_guard: InjectionGuardFn | None = None

    def _entry_point(self) -> str:
        if self.injection_guard:
            return "injection_guard"
        if self.scope_check:
            return "scope_check"
        return "planner"

    def build(self):
        graph = StateGraph(dict)
        if self.injection_guard:
            graph.add_node("injection_guard", _wrap(self.injection_guard, self.tool_registry, "injection_guard"))
        if self.scope_check:
            graph.add_node("scope_check", _wrap(self.scope_check, self.tool_registry, "scope_check"))
        graph.add_node("planner", _wrap(self.planner, self.tool_registry, "planner"))
        if self.clarifier:
            graph.add_node("clarifier", _wrap(self.clarifier, self.tool_registry, "clarifier"))
        graph.add_node("tool_executor", _wrap(self.tool_executor, self.tool_registry, "tool_executor"))
        if self.answer:
            graph.add_node("answer", _wrap(self.answer, self.tool_registry, "answer"))
        graph.set_entry_point(self._entry_point())
        if self.injection_guard:
            graph.add_edge("injection_guard", "scope_check" if self.scope_check else "planner")
        if self.scope_check:
            graph.add_edge("scope_check", "planner")
        if self.clarifier:
            graph.add_edge("planner", "clarifier")
            graph.add_edge("clarifier", "tool_executor")
        else:
            graph.add_edge("planner", "tool_executor")
        if self.answer:
            graph.add_edge("tool_executor", "answer")
        if self.critic:
            graph.add_node("critic", _wrap(self.critic, self.tool_registry, "critic"))
            if self.answer:
                graph.add_edge("answer", "critic")
            else:
                graph.add_edge("tool_executor", "critic")
            graph.add_edge("critic", END)
        else:
            if self.answer:
                graph.add_edge("answer", END)
            else:
                graph.add_edge("tool_executor", END)
        return graph.compile()

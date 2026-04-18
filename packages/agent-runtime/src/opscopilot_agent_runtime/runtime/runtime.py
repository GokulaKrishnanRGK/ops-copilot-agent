from threading import Thread
from typing import Callable

from langgraph.errors import GraphRecursionError
from opentelemetry import trace

from opscopilot_agent_runtime.graph import AgentGraph
from opscopilot_agent_runtime.history import HistoryManager, SummaryStore
from opscopilot_agent_runtime.persistence import AgentRunRecorder
from opscopilot_agent_runtime.runtime.limits import ExecutionLimits, validate_limits
from opscopilot_agent_runtime.runtime.logging import clear_log_context, get_logger, set_log_context
from opscopilot_agent_runtime.state import AgentState


def _extract_log_excerpts(tool_results: list) -> list[str]:
    excerpts: list[str] = []
    for result in tool_results:
        tool_name = getattr(result, "tool_name", "") or ""
        if "get_pod_logs" not in tool_name:
            continue
        text = getattr(result, "text", "") or ""
        lines = [ln for ln in text.splitlines() if ln.strip()]
        error_lines = [ln for ln in lines if any(kw in ln.lower() for kw in ("error", "exception", "fatal", "panic"))]
        excerpts.extend(error_lines[:3])
        if not error_lines:
            excerpts.extend(lines[-3:])
    return excerpts


class AgentRuntime:
    def __init__(
        self,
        graph: AgentGraph,
        limits: ExecutionLimits,
        recorder: AgentRunRecorder | None = None,
        budget_max_usd: float | None = None,
        runtime_config_id: str | None = None,
        answer_scorer: Callable[[AgentState], None] | None = None,
        summarizer=None,
        summary_store: SummaryStore | None = None,
        history_window_turns: int = 6,
    ):
        validate_limits(limits)
        self._graph = graph
        self._limits = limits
        self._recorder = recorder
        self._budget_max_usd = budget_max_usd
        self._runtime_config_id = runtime_config_id
        self._answer_scorer = answer_scorer
        self._summarizer = summarizer
        self._summary_store = summary_store
        self._history_window_turns = history_window_turns

    def _prepare_state(self, state: AgentState) -> tuple[AgentState, AgentRunRecorder | None]:
        recorder = self._recorder
        config_json = {"limits": {"max_agent_steps": self._limits.max_agent_steps}}
        if self._budget_max_usd is not None:
            config_json["budget"] = {"max_usd": self._budget_max_usd}
        if recorder:
            recorder.start(config_json, runtime_config_id=self._runtime_config_id)
            set_log_context(recorder.session_id, recorder.run_id)
        next_state = state
        if state.prompt:
            user_prompt = state.prompt
            history = list(state.prompt_history or [])
            if not history or history[-1] != state.prompt:
                history.append(state.prompt)

            summary = state.prompt_summary
            if self._summary_store and recorder:
                stored = self._summary_store.load(recorder.session_id)
                if stored is not None:
                    summary = stored

            log_excerpts = _extract_log_excerpts(state.tool_results or [])
            recent_turns, to_summarize = HistoryManager.condense(
                history=history,
                window=self._history_window_turns,
            )
            if to_summarize and self._summarizer:
                summary = self._summarizer.summarize(
                    older_turns=to_summarize,
                    existing_summary=summary,
                    log_excerpts=log_excerpts,
                    recorder=recorder,
                )
                if self._summary_store and recorder:
                    self._summary_store.save(recorder.session_id, summary)

            if summary:
                merged_prompt = f"[SUMMARY]\n{summary}\n\n[RECENT]\n" + "\n".join(recent_turns)
            else:
                merged_prompt = "\n".join(history)

            next_state = next_state.merge(
                prompt=merged_prompt,
                user_prompt=user_prompt,
                prompt_history=history,
                prompt_summary=summary,
            )
        if state.error and state.error.get("type") == "clarification_required" and state.prompt:
            next_state = next_state.merge(error=None)
        state_with_recorder = next_state.merge(recorder=recorder) if recorder else next_state
        return state_with_recorder, recorder

    def run(self, state: AgentState) -> AgentState:
        last_state = state
        for snapshot in self.run_stream(state):
            last_state = snapshot
        return last_state

    def run_stream(self, state: AgentState):
        compiled = self._graph.build()
        state_with_recorder, recorder = self._prepare_state(state)
        try:
            final_state: AgentState | None = None
            for result_dict in compiled.stream(
                state_with_recorder.to_dict(),
                config={"recursion_limit": self._limits.max_agent_steps},
                stream_mode="values",
            ):
                final_state = AgentState.from_dict(result_dict)
                yield final_state
            if recorder:
                recorder.finish("completed")
            if final_state is not None:
                self._score_answer(final_state)
            if final_state is None:
                yield state_with_recorder
        except GraphRecursionError as exc:
            if recorder:
                recorder.finish("failed")
            yield state_with_recorder.merge(
                error={
                    "type": "recursion_limit",
                    "message": str(exc),
                }
            )
        except Exception:
            if recorder:
                recorder.finish("failed")
            raise
        finally:
            clear_log_context()

    def _score_answer(self, state: AgentState) -> None:
        if self._answer_scorer is None or not state.answer:
            return
        context = trace.get_current_span().get_span_context()
        scored_state = state
        if context.is_valid:
            scored_state = state.merge(langfuse_trace_id=trace.format_trace_id(context.trace_id))
        Thread(target=self._run_answer_scorer, args=(scored_state,), daemon=True).start()

    def _run_answer_scorer(self, state: AgentState) -> None:
        if self._answer_scorer is None:
            return
        try:
            self._answer_scorer(state)
        except Exception as exc:
            get_logger(__name__).info("answer scoring skipped: %s", exc)

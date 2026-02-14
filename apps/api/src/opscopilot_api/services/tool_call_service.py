from opscopilot_db import models, repositories


class ToolCallService:
    def __init__(
        self,
        session_repo: repositories.SessionRepository,
        run_repo: repositories.AgentRunRepository,
        tool_call_repo: repositories.ToolCallRepository,
    ) -> None:
        self._session_repo = session_repo
        self._run_repo = run_repo
        self._tool_call_repo = tool_call_repo

    def list_by_run(self, run_id: str) -> list[models.ToolCall]:
        run = self._run_repo.get(run_id)
        if run is None:
            raise ValueError("run not found")
        return list(self._tool_call_repo.list_by_run(run_id))

    def list_by_session(self, session_id: str) -> list[models.ToolCall]:
        session = self._session_repo.get(session_id)
        if session is None:
            raise ValueError("session not found")
        runs = list(self._run_repo.list_by_session(session_id))
        if not runs:
            return []
        items: list[models.ToolCall] = []
        for run in runs:
            items.extend(self._tool_call_repo.list_by_run(run.id))
        return sorted(items, key=lambda item: item.created_at)

    def list_by_runs(self, run_ids: list[str]) -> list[models.ToolCall]:
        if not run_ids:
            return []
        unique_run_ids = list(dict.fromkeys(run_ids))
        return list(self._tool_call_repo.list_by_runs(unique_run_ids))

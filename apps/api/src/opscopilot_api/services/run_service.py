from opscopilot_db import models, repositories


class RunService:
    def __init__(
        self,
        session_repo: repositories.SessionRepository,
        run_repo: repositories.AgentRunRepository,
    ) -> None:
        self._session_repo = session_repo
        self._run_repo = run_repo

    def list_by_session(self, session_id: str) -> list[models.AgentRun]:
        session = self._session_repo.get(session_id)
        if session is None:
            raise ValueError("session not found")
        return list(self._run_repo.list_by_session(session_id))

from __future__ import annotations

import logging
from datetime import datetime, timezone

from opscopilot_agent_runtime.llm.title_generator import TitleGenerator
from opscopilot_db.repositories import SessionRepository

_logger = logging.getLogger(__name__)


class TitleService:
    def __init__(
        self,
        title_generator: TitleGenerator,
        session_repo: SessionRepository,
    ) -> None:
        self._generator = title_generator
        self._session_repo = session_repo

    def generate_and_persist(self, session_id: str, prompt: str, run_id: str) -> None:
        session = self._session_repo.get(session_id)
        if session is None or session.title is not None:
            return
        try:
            raw_title = self._generator.generate(prompt=prompt, session_id=session_id, run_id=run_id)
        except Exception:
            _logger.exception("title generation failed for session %s", session_id)
            return
        if not raw_title:
            return
        final_title = self._unique_title(raw_title)
        session = self._session_repo.get(session_id)
        if session is None or session.title is not None:
            return
        session.title = final_title
        session.updated_at = datetime.now(timezone.utc)
        self._session_repo.update(session)

    def _unique_title(self, title: str) -> str:
        if self._session_repo.find_by_title(title) is None:
            return title
        suffix = 2
        while True:
            candidate = f"{title} {suffix}"
            if self._session_repo.find_by_title(candidate) is None:
                return candidate
            suffix += 1

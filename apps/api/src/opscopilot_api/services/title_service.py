from __future__ import annotations

import logging
from datetime import datetime, timezone

from opscopilot_agent_runtime.llm.title_generator import TitleGenerator
from opscopilot_db.repositories import SessionRepository

_logger = logging.getLogger(__name__)

PLACEHOLDER_TITLE = "New chat"


class TitleService:
    def __init__(
        self,
        title_generator: TitleGenerator,
        session_repo: SessionRepository,
    ) -> None:
        self._generator = title_generator
        self._session_repo = session_repo

    def generate_and_persist(self, session_id: str, prompt: str, run_id: str) -> str | None:
        _logger.debug("generate_and_persist called [session=%s run=%s]", session_id, run_id)
        session = self._session_repo.get(session_id)
        if session is None:
            _logger.debug("session not found, skipping title generation [session=%s]", session_id)
            return None
        if session.title is not None and session.title != PLACEHOLDER_TITLE:
            _logger.debug("session already has title=%r, skipping [session=%s]", session.title, session_id)
            return None
        try:
            _logger.debug("invoking LLM title generator [session=%s run=%s]", session_id, run_id)
            raw_title = self._generator.generate(prompt=prompt, session_id=session_id, run_id=run_id)
            _logger.debug("LLM title generator returned raw_title=%r [session=%s run=%s]", raw_title, session_id, run_id)
        except Exception as exc:
            _logger.exception("title generation failed for session %s: %s", session_id, exc)
            return None
        if not raw_title:
            _logger.debug("empty title returned, skipping persist [session=%s]", session_id)
            return None
        final_title = self._unique_title(raw_title)
        session = self._session_repo.get(session_id)
        if session is None or (session.title is not None and session.title != PLACEHOLDER_TITLE):
            _logger.debug("session changed state before persist, skipping [session=%s]", session_id)
            return None
        session.title = final_title
        session.updated_at = datetime.now(timezone.utc)
        self._session_repo.update(session)
        _logger.debug("title persisted final_title=%r [session=%s]", final_title, session_id)
        return final_title

    def _unique_title(self, title: str) -> str:
        if self._session_repo.find_by_title(title) is None:
            return title
        suffix = 2
        while True:
            candidate = f"{title} {suffix}"
            if self._session_repo.find_by_title(candidate) is None:
                return candidate
            suffix += 1

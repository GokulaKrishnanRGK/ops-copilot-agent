from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SummaryStore(Protocol):
    def load(self, session_id: str) -> str | None: ...
    def save(self, session_id: str, summary: str) -> None: ...


class InMemorySummaryStore:
    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    def load(self, session_id: str) -> str | None:
        return self._store.get(session_id)

    def save(self, session_id: str, summary: str) -> None:
        self._store[session_id] = summary


class PostgresSummaryStore:
    def __init__(self, sessionmaker) -> None:
        self._sessionmaker = sessionmaker

    def load(self, session_id: str) -> str | None:
        from opscopilot_db.models import Session as SessionModel

        with self._sessionmaker() as db:
            row = db.get(SessionModel, session_id)
            if row is None:
                return None
            return row.prompt_summary

    def save(self, session_id: str, summary: str) -> None:
        from datetime import datetime, timezone

        from opscopilot_db.models import Session as SessionModel

        with self._sessionmaker() as db:
            row = db.get(SessionModel, session_id)
            if row is not None:
                row.prompt_summary = summary
                row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
                db.commit()


class HistoryManager:
    @staticmethod
    def condense(
        history: list[str],
        window: int,
    ) -> tuple[list[str], list[str]]:
        """Split history into (recent_turns, older_turns).

        recent_turns: last `window` entries (passed to LLM as-is).
        older_turns: everything before the window (candidates for summarization).
        """
        if window <= 0 or len(history) <= window:
            return list(history), []
        return list(history[-window:]), list(history[:-window])

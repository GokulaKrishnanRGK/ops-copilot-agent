from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from opscopilot_api.services.title_service import TitleService
from opscopilot_db import models


def _make_session(session_id: str = "s1", title: str | None = None) -> models.Session:
    now = datetime.now(timezone.utc)
    return models.Session(id=session_id, title=title, created_at=now, updated_at=now)


def _make_service(generated_title: str = "Pod Crash Loop", existing_sessions: list | None = None):
    generator = MagicMock()
    generator.generate.return_value = generated_title

    session_repo = MagicMock()

    existing = existing_sessions or []
    title_map = {s.title: s for s in existing if s.title}

    def find_by_title(title):
        return title_map.get(title)

    session_repo.find_by_title.side_effect = find_by_title
    return TitleService(title_generator=generator, session_repo=session_repo), session_repo, generator


class TestTitleServiceGenerateAndPersist:
    def test_generates_and_persists_title(self):
        session = _make_session()
        service, repo, generator = _make_service("Pod Crash Loop")
        repo.get.return_value = session

        service.generate_and_persist("s1", "Why is the pod crashing?", "r1")

        generator.generate.assert_called_once_with(prompt="Why is the pod crashing?", session_id="s1", run_id="r1")
        repo.update.assert_called_once()
        updated = repo.update.call_args[0][0]
        assert updated.title == "Pod Crash Loop"

    def test_skips_when_session_already_has_title(self):
        session = _make_session(title="Existing Title")
        service, repo, generator = _make_service()
        repo.get.return_value = session

        service.generate_and_persist("s1", "prompt", "r1")

        generator.generate.assert_not_called()
        repo.update.assert_not_called()

    def test_skips_when_session_not_found(self):
        service, repo, generator = _make_service()
        repo.get.return_value = None

        service.generate_and_persist("s1", "prompt", "r1")

        generator.generate.assert_not_called()

    def test_skips_when_generated_title_empty(self):
        session = _make_session()
        service, repo, generator = _make_service(generated_title="")
        repo.get.return_value = session

        service.generate_and_persist("s1", "prompt", "r1")

        repo.update.assert_not_called()

    def test_deduplication_appends_suffix(self):
        session = _make_session()
        existing = [_make_session("other", "Pod Crash Loop")]
        service, repo, generator = _make_service("Pod Crash Loop", existing_sessions=existing)
        repo.get.return_value = session

        service.generate_and_persist("s1", "prompt", "r1")

        updated = repo.update.call_args[0][0]
        assert updated.title == "Pod Crash Loop 2"

    def test_deduplication_increments_suffix_until_unique(self):
        session = _make_session()
        existing = [
            _make_session("a", "Pod Crash Loop"),
            _make_session("b", "Pod Crash Loop 2"),
            _make_session("c", "Pod Crash Loop 3"),
        ]
        service, repo, generator = _make_service("Pod Crash Loop", existing_sessions=existing)
        repo.get.return_value = session

        service.generate_and_persist("s1", "prompt", "r1")

        updated = repo.update.call_args[0][0]
        assert updated.title == "Pod Crash Loop 4"

    def test_handles_generator_exception_gracefully(self):
        session = _make_session()
        service, repo, generator = _make_service()
        repo.get.return_value = session
        generator.generate.side_effect = RuntimeError("LLM failure")

        service.generate_and_persist("s1", "prompt", "r1")

        repo.update.assert_not_called()

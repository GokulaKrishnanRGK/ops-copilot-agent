from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from opscopilot_api.main import create_app
from opscopilot_db.base import Base
from opscopilot_db.connection import get_engine


@pytest.fixture(scope="session", autouse=True)
def ensure_schema() -> None:
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    yield TestClient(app)

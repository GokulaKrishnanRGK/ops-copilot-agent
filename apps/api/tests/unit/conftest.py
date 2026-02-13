from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from opscopilot_api.db import get_db
from opscopilot_api.main import create_app
from opscopilot_db.base import Base


@pytest.fixture
def testing_session_local():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return testing_session_local


@pytest.fixture
def app(testing_session_local):
    def override_get_db() -> Generator[Session, None, None]:
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    api_app = create_app()
    api_app.dependency_overrides[get_db] = override_get_db
    return api_app


@pytest.fixture
def client(app) -> Generator[TestClient, None, None]:
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()

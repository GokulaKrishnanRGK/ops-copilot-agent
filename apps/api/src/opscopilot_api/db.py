from collections.abc import Generator

from sqlalchemy.orm import Session

from opscopilot_db.connection import get_sessionmaker


def get_db() -> Generator[Session, None, None]:
    session_local = get_sessionmaker()
    db = session_local()
    try:
        yield db
    finally:
        db.close()

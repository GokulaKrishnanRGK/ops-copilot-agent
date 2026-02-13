from sqlalchemy import text

from opscopilot_db.connection import get_engine


def check_database() -> None:
    engine = get_engine()
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

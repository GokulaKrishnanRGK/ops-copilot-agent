import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is required")
    return url


def get_engine():
    return create_engine(get_database_url(), pool_pre_ping=True)


def get_sessionmaker():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())

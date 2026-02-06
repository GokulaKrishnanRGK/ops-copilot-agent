from pathlib import Path

from dotenv import load_dotenv


def pytest_sessionstart(session):
    repo_root = Path(__file__).resolve().parents[3]
    env_path = repo_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

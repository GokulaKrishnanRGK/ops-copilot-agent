from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from opscopilot_db.base import Base
from opscopilot_db import models


def _make_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _now():
    return datetime(2024, 1, 1, tzinfo=timezone.utc)


def test_session_roundtrip():
    db = _make_session()
    session = models.Session(
        id="s1",
        created_at=_now(),
        updated_at=_now(),
        title="t",
    )
    db.add(session)
    db.commit()
    loaded = db.get(models.Session, "s1")
    assert loaded is not None
    assert loaded.id == "s1"


def test_message_roundtrip():
    db = _make_session()
    db.add(
        models.Session(
            id="s1",
            created_at=_now(),
            updated_at=_now(),
            title=None,
        )
    )
    db.commit()
    message = models.Message(
        id="m1",
        session_id="s1",
        role="user",
        content="hello",
        created_at=_now(),
        metadata_json=None,
    )
    db.add(message)
    db.commit()
    loaded = db.get(models.Message, "m1")
    assert loaded is not None
    assert loaded.id == "m1"


def test_agent_run_roundtrip():
    db = _make_session()
    db.add(
        models.Session(
            id="s1",
            created_at=_now(),
            updated_at=_now(),
            title=None,
        )
    )
    db.commit()
    run = models.AgentRun(
        id="r1",
        session_id="s1",
        started_at=_now(),
        ended_at=None,
        status="completed",
        config_json={},
    )
    db.add(run)
    db.commit()
    loaded = db.get(models.AgentRun, "r1")
    assert loaded is not None
    assert loaded.id == "r1"


def test_llm_call_roundtrip():
    db = _make_session()
    db.add(
        models.Session(
            id="s1",
            created_at=_now(),
            updated_at=_now(),
            title=None,
        )
    )
    db.add(
        models.AgentRun(
            id="r1",
            session_id="s1",
            started_at=_now(),
            ended_at=None,
            status="completed",
            config_json={},
        )
    )
    db.commit()
    call = models.LlmCall(
        id="c1",
        agent_run_id="r1",
        agent_node="planner",
        model_id="m1",
        tokens_input=1,
        tokens_output=1,
        cost_usd=0.01,
        latency_ms=10,
        created_at=_now(),
        metadata_json=None,
    )
    db.add(call)
    db.commit()
    loaded = db.query(models.LlmCall).filter(models.LlmCall.agent_run_id == "r1").all()
    assert len(loaded) == 1


def test_tool_call_roundtrip():
    db = _make_session()
    db.add(
        models.Session(
            id="s1",
            created_at=_now(),
            updated_at=_now(),
            title=None,
        )
    )
    db.add(
        models.AgentRun(
            id="r1",
            session_id="s1",
            started_at=_now(),
            ended_at=None,
            status="completed",
            config_json={},
        )
    )
    db.commit()
    call = models.ToolCall(
        id="t1",
        agent_run_id="r1",
        tool_name="k8s.list_pods",
        args_json={},
        status="success",
        latency_ms=10,
        bytes_returned=0,
        truncated=False,
        error_message=None,
        created_at=_now(),
    )
    db.add(call)
    db.commit()
    loaded = db.query(models.ToolCall).filter(models.ToolCall.agent_run_id == "r1").all()
    assert len(loaded) == 1


def test_budget_event_roundtrip():
    db = _make_session()
    db.add(
        models.Session(
            id="s1",
            created_at=_now(),
            updated_at=_now(),
            title=None,
        )
    )
    db.add(
        models.AgentRun(
            id="r1",
            session_id="s1",
            started_at=_now(),
            ended_at=None,
            status="completed",
            config_json={},
        )
    )
    db.commit()
    event = models.BudgetEvent(
        id="b1",
        agent_run_id="r1",
        kind="llm_cost",
        delta_usd=0.1,
        total_usd=0.1,
        created_at=_now(),
        metadata_json=None,
    )
    db.add(event)
    db.commit()
    loaded = db.query(models.BudgetEvent).filter(models.BudgetEvent.agent_run_id == "r1").all()
    assert len(loaded) == 1

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from opscopilot_api.config_cache import RuntimeConfigData
from opscopilot_api.db import get_db
from opscopilot_api.schemas.settings import NodeConfigSchema, SettingsNodesSchema, SettingsResponse, SettingsUpdate
from opscopilot_db.repositories.sqlalchemy import RuntimeConfigRepo

router = APIRouter()


def _to_response(config: RuntimeConfigData) -> SettingsResponse:
    def _node(name: str) -> NodeConfigSchema:
        n = config.node(name)
        return NodeConfigSchema(model_id=n.model_id, prompt_version=n.prompt_version)

    return SettingsResponse(
        id=config.id,
        schema_version=config.schema_version,
        nodes=SettingsNodesSchema(
            scope=_node("scope"),
            planner=_node("planner"),
            clarifier=_node("clarifier"),
            answer=_node("answer"),
            summarizer=_node("summarizer"),
            injection_classifier=_node("injection_classifier"),
        ),
        max_agent_steps=config.max_agent_steps,
        max_budget_usd=config.max_budget_usd,
        history_window_turns=config.history_window_turns,
        summarizer_prompt_version=config.summarizer_prompt_version,
        eval_sample_rate=config.eval_sample_rate,
        eval_llm_judge_enabled=config.eval_llm_judge_enabled,
        eval_ragas_enabled=config.eval_ragas_enabled,
        eval_judge_model_id=config.eval_judge_model_id,
        prompt_injection_llm_check=config.prompt_injection_llm_check,
        agent_max_tool_calls=config.agent_max_tool_calls,
        agent_max_llm_calls=config.agent_max_llm_calls,
        agent_max_execution_time_ms=config.agent_max_execution_time_ms,
        bedrock_embedding_model_id=config.bedrock_embedding_model_id,
    )


@router.get("", response_model=SettingsResponse)
def get_settings(request: Request) -> SettingsResponse:
    config = request.app.state.config_cache.get()
    return _to_response(config)


@router.patch("", response_model=SettingsResponse)
def patch_settings(
    payload: SettingsUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> SettingsResponse:
    current = request.app.state.config_cache.get()
    config_json = {
        "nodes": payload.nodes.model_dump(),
        "limits": {
            "max_agent_steps": payload.max_agent_steps,
            "max_budget_usd": payload.max_budget_usd,
            "history_window_turns": payload.history_window_turns,
            "summarizer_prompt_version": payload.summarizer_prompt_version,
        },
        "env_overrides": {
            "eval_sample_rate": payload.eval_sample_rate,
            "eval_llm_judge_enabled": payload.eval_llm_judge_enabled,
            "eval_ragas_enabled": payload.eval_ragas_enabled,
            "eval_judge_model_id": payload.eval_judge_model_id,
            "prompt_injection_llm_check": payload.prompt_injection_llm_check,
            "agent_max_tool_calls": payload.agent_max_tool_calls,
            "agent_max_llm_calls": payload.agent_max_llm_calls,
            "agent_max_execution_time_ms": payload.agent_max_execution_time_ms,
            "bedrock_embedding_model_id": payload.bedrock_embedding_model_id,
        },
    }
    new_row = RuntimeConfigRepo(db=db).create(config_json=config_json, schema_version=current.schema_version)
    new_config = RuntimeConfigData.from_db(new_row)
    request.app.state.config_cache.set(new_config)
    return _to_response(new_config)

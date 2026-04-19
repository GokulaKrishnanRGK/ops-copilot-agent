from unittest.mock import MagicMock, patch

from opscopilot_agent_runtime.llm.title_generator import LlmTitleGenerator, NoOpTitleGenerator


def _make_response(text: str = "Pod Crash Loop Debug", error=None):
    output = MagicMock()
    output.text = text
    output.type = "text"
    resp = MagicMock()
    resp.output = output
    resp.error = error
    resp.tokens_input = 10
    resp.tokens_output = 5
    resp.cost_usd = 0.0001
    resp.latency_ms = 120
    resp.cache_hit = False
    resp.cache_read_input_tokens = 0
    resp.finish_reason = "end_turn"
    resp.provider_metadata = {}
    return resp


def _make_prompt_source(text: str = "Generate a title.") -> MagicMock:
    source = MagicMock()
    source.get.return_value = text
    return source


def _make_generator(prompt_source=None, prompt_version: str = "v1"):
    provider = MagicMock()
    budget = MagicMock()
    budget.state.return_value = MagicMock(total_usd=0.0)
    ledger = MagicMock()
    return LlmTitleGenerator(
        provider=provider,
        model_id="global.anthropic.claude-haiku-4-5-20251001-v1:0",
        budget=budget,
        ledger=ledger,
        prompt_source=prompt_source or _make_prompt_source(),
        prompt_version=prompt_version,
    )


class TestNoOpTitleGenerator:
    def test_returns_empty_string(self):
        gen = NoOpTitleGenerator()
        assert gen.generate("any prompt", "session-1", "run-1") == ""


class TestLlmTitleGenerator:
    def test_returns_title_on_success(self):
        gen = _make_generator()
        with patch.object(gen, "_call", return_value=_make_response("Pod Crash Loop Debug")):
            result = gen.generate("Why is my pod crashing?", "s1", "r1")
        assert result == "Pod Crash Loop Debug"

    def test_strips_surrounding_quotes(self):
        gen = _make_generator()
        with patch.object(gen, "_call", return_value=_make_response('"Pod Crash Loop Debug"')):
            result = gen.generate("Why is my pod crashing?", "s1", "r1")
        assert result == "Pod Crash Loop Debug"

    def test_returns_empty_on_error(self):
        error = MagicMock()
        error.message = "provider error"
        resp = _make_response(text=None, error=error)
        resp.output = None
        gen = _make_generator()
        with patch.object(gen, "_call", return_value=resp):
            result = gen.generate("prompt", "s1", "r1")
        assert result == ""

    def test_fetches_prompt_from_source(self):
        source = _make_prompt_source("My system prompt.")
        gen = _make_generator(prompt_source=source, prompt_version="v1")
        with patch.object(gen, "_call", return_value=_make_response()):
            gen.generate("prompt", "s1", "r1")
        source.get.assert_called_once_with("title_gen", "v1")

    def test_prompt_included_in_system_message(self):
        source = _make_prompt_source("Custom system prompt text.")
        gen = _make_generator(prompt_source=source)
        captured = {}

        def fake_call(request, agent_node, recorder):
            captured["system"] = request.messages[0].content
            return _make_response()

        with patch.object(gen, "_call", side_effect=fake_call):
            gen.generate("prompt", "s1", "r1")

        assert captured["system"] == "Custom system prompt text."

    def test_prompt_ref_included_in_request(self):
        source = _make_prompt_source()
        ref_result = MagicMock()
        ref_result.name = "title_gen"
        source.ref.return_value = ref_result
        gen = _make_generator(prompt_source=source, prompt_version="v1")
        captured = {}

        def fake_call(request, agent_node, recorder):
            captured["prompt_ref"] = request.prompt_ref
            return _make_response()

        with patch.object(gen, "_call", side_effect=fake_call):
            gen.generate("prompt", "s1", "r1")

        assert captured["prompt_ref"] is not None
        assert captured["prompt_ref"].name == "title_gen"
        source.ref.assert_called_once_with("title_gen", "v1")

    def test_passes_session_and_run_in_request(self):
        gen = _make_generator()
        captured = {}

        def fake_call(request, agent_node, recorder):
            captured["tags"] = request.tags
            captured["node"] = agent_node
            return _make_response()

        with patch.object(gen, "_call", side_effect=fake_call):
            gen.generate("prompt", "session-abc", "run-xyz")

        assert captured["tags"].session_id == "session-abc"
        assert captured["tags"].agent_run_id == "run-xyz"
        assert captured["node"] == "title_gen"

    def test_truncates_long_prompt(self):
        gen = _make_generator()
        long_prompt = "a" * 1000
        captured = {}

        def fake_call(request, agent_node, recorder):
            captured["user_content"] = request.messages[-1].content
            return _make_response()

        with patch.object(gen, "_call", side_effect=fake_call):
            gen.generate(long_prompt, "s1", "r1")

        assert len(captured["user_content"]) <= 500

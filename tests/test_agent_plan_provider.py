import pytest

import src.llm.agent_plan as plan_module


def test_plan_with_llm_routes_to_ollama(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")

    monkeypatch.setattr(
        plan_module,
        "plan_with_ollama",
        lambda user_text, mcp_tools, allowed_builtin_cmds: {
            "kind": "chat",
            "answer_hint": "success",
        },
    )
    monkeypatch.setattr(
        plan_module,
        "plan_with_zhipu",
        lambda user_text, mcp_tools, allowed_builtin_cmds: {
            "kind": "chat",
            "answer_hint": "bad",
        },
    )

    out = plan_module.plan_with_llm("hi", [], {"time"})
    assert out["plan"]["kind"] == "chat"
    assert out["plan"]["answer_hint"] == "success"
    assert out["meta"]["provider_used"] == "ollama"
    assert out["meta"]["fallback_used"] is False


def test_plan_with_llm_routes_to_zhipu(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "zhipu")

    monkeypatch.setattr(
        plan_module,
        "plan_with_ollama",
        lambda user_text, mcp_tools, allowed_builtin_cmds: {
            "kind": "chat",
            "answer_hint": "bad",
        },
    )
    monkeypatch.setattr(
        plan_module,
        "plan_with_zhipu",
        lambda user_text, mcp_tools, allowed_builtin_cmds: {
            "kind": "chat",
            "answer_hint": "success",
        },
    )
    out = plan_module.plan_with_llm("hi", [], {"time"})
    assert out["plan"]["kind"] == "chat"
    assert out["plan"]["answer_hint"] == "success"
    assert out["meta"]["provider_used"] == "zhipu"
    assert out["meta"]["fallback_used"] is False


def test_plan_with_llm_fallback_when_primary_fails(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "zhipu")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "ollama")

    def _zhipu_fail(user_text, mcp_tools, allowed_builtin_cmds):
        raise plan_module.PlanError("zhipu down")

    monkeypatch.setattr(plan_module, "plan_with_zhipu", _zhipu_fail)
    monkeypatch.setattr(
        plan_module,
        "plan_with_ollama",
        lambda user_text, mcp_tools, allowed_builtin_cmds: {
            "kind": "chat",
            "answer_hint": "from_fallback",
        },
    )

    out = plan_module.plan_with_llm("hi", [], {"time"})
    assert out["plan"]["kind"] == "chat"
    assert out["plan"]["answer_hint"] == "from_fallback"
    assert out["meta"]["provider_used"] == "ollama"
    assert out["meta"]["fallback_used"] is True


def test_plan_with_llm_primary_and_fallback_both_fail(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "zhipu")
    monkeypatch.setenv("LLM_FALLBACK_PROVIDER", "ollama")

    def _zhipu_fail(user_text, mcp_tools, allowed_builtin_cmds):
        raise plan_module.PlanError("zhipu timeout")

    def _ollama_fail(user_text, mcp_tools, allowed_builtin_cmds):
        raise plan_module.PlanError("ollama down")

    monkeypatch.setattr(plan_module, "plan_with_zhipu", _zhipu_fail)
    monkeypatch.setattr(plan_module, "plan_with_ollama", _ollama_fail)
    with pytest.raises(plan_module.PlanError) as e:
        plan_module.plan_with_llm("hi", [], {"time"})
    msg = str(e.value)
    assert "主 provider（zhipu）失败" in msg
    assert "fallback（ollama）也失败" in msg

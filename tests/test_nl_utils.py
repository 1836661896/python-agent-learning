import pytest

from src.routers.nl_utils import (
    build_builtin_event_payload,
    build_mcp_event_payload,
    build_mcp_fail_data,
    is_allowed_nl_command,
    parse_manual_mcp_or_none,
)


def test_is_allowed_nl_command():
    assert is_allowed_nl_command("list") is True
    assert is_allowed_nl_command("echo hello") is True
    assert is_allowed_nl_command("add 买牛奶") is True
    assert is_allowed_nl_command("delete 1") is False


def test_parse_manual_mcp_or_none_success():
    parsed, err = parse_manual_mcp_or_none('mcp echo {"text":"hi"}')
    assert err is None
    assert parsed is not None
    tool_name, args = parsed
    assert tool_name == "echo"
    assert args == {"text": "hi"}


def test_parse_manual_mcp_or_none_non_mcp_text():
    parsed, err = parse_manual_mcp_or_none("你好，今天天气如何")
    assert parsed is None
    assert err is None


def test_parse_manual_mcp_or_none_parse_error():
    parsed, err = parse_manual_mcp_or_none("mcp ping =x a=1")
    assert parsed is None
    assert err is not None
    assert "参数名不能为空" in err


def test_build_mcp_event_payload_success():
    summary, payload = build_mcp_event_payload(
        route="mcp",
        tool_name="echo",
        plan_meta={"provider_used": "ollama"},
        ok_flag=True,
        result_data={"text": "hi"},
    )
    assert summary == "mcp success: echo"
    assert payload["route"] == "mcp"
    assert payload["tool_name"] == "echo"
    assert payload["result"] == {"text": "hi"}


def test_build_mcp_event_payload_fail_with_allowed():
    summary, payload = build_mcp_event_payload(
        route="mcp",
        tool_name="echo",
        plan_meta={"provider_used": "manual_mcp"},
        ok_flag=False,
        error_type="mcp_not_allowed",
        allowed=["ping", "now"],
    )
    assert summary == "mcp failed"
    assert payload["error_type"] == "mcp_not_allowed"
    assert payload["allowed"] == ["ping", "now"]


def test_build_mcp_fail_data():
    data = build_mcp_fail_data(
        tool_name="echo",
        detail="boom",
        allowed=["ping", "now"],
        planner_meta={"provider_used": "manual_mcp"},
    )
    assert data["route"] == "mcp"
    assert data["tool_name"] == "echo"
    assert data["detail"] == "boom"
    assert data["allowed"] == ["ping", "now"]
    assert data["planner_meta"]["provider_used"] == "manual_mcp"


def test_build_builtin_event_payload_success():
    summary, payload = build_builtin_event_payload(
        cmd="time",
        plan_meta={"provider_used": "ollama"},
        ok_flag=True,
        tool_msg="ok",
        data="2026-01-01 00:00:00 UTC",
    )
    assert summary == "builtin success: time"
    assert payload["route"] == "builtin"
    assert payload["command"] == "time"
    assert payload["result"] == "2026-01-01 00:00:00 UTC"


def test_build_builtin_event_payload_fail():
    summary, payload = build_builtin_event_payload(
        cmd="time",
        plan_meta={"provider_used": "ollama"},
        ok_flag=False,
        tool_msg="boom",
        data=None,
    )
    assert summary == "builtin failed: time"
    assert payload["error_type"] == "builtin_run_failed"


def test_parse_manual_mcp_or_none_raises_for_internal_value_error(monkeypatch):
    from src import routers

    monkeypatch.setattr(
        routers.nl_utils, "parse_mcp_call", lambda _msg: (_ for _ in ()).throw(ValueError("x"))
    )
    with pytest.raises(ValueError):
        parse_manual_mcp_or_none("hello")

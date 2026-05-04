import pytest

from src.llm.agent_plan import PlanError, parse_plan_json, validate_plan


def test_parse_plan_json_ok():
    raw = '{"kind": "mcp", "tool_name": "echo", "arguments": {"text": "hi"}}'
    obj = parse_plan_json(raw)
    assert obj["kind"] == "mcp"


def test_parse_plan_json_markdown_block_ok():
    raw = """```json
{"kind": "chat", "answer_hint": ""}
```"""
    obj = parse_plan_json(raw)
    assert obj["kind"] == "chat"


def test_validate_ok():
    plan = {"kind": "mcp", "tool_name": "echo", "arguments": {"text": "hi"}}
    out = validate_plan(
        plan, {"echo", "ping"}, {"time", "list", "help", "version", "echo", "add"}
    )
    assert out["kind"] == "mcp"
    assert out["tool_name"] == "echo"


def test_validate_mcp_tool_not_allowed():
    plan = {"kind": "mcp", "tool_name": "hack", "arguments": {}}
    with pytest.raises(PlanError):
        validate_plan(
            plan, {"echo", "ping"}, {"time", "list", "help", "version", "echo", "add"}
        )


def test_validate_builtin_not_allowed():
    plan = {"kind": "builtin", "command": "rm -rf //"}
    with pytest.raises(PlanError):
        validate_plan(
            plan, {"echo", "ping"}, {"time", "list", "help", "version", "echo", "add"}
        )

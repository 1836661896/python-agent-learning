"""`decide_route_auto`：行程 preset 与动态 MCP 工具列表（mock，不联网）。"""

from unittest.mock import MagicMock

from src.services.agent_presets import PRESET_SCHEDULE
from src.services.route_auto import decide_route_auto


def _run_list_tools_result(tools: list) -> object:
    r = MagicMock()
    r.tools = tools
    return r


def _patch_list_tools(monkeypatch, tools: list) -> None:
    async def _fake_list():
        return _run_list_tools_result(tools)

    monkeypatch.setattr(
        "src.services.route_auto.mcp_list_tools_async",
        _fake_list,
    )


def _make_tool(name: str, *, required: list[str] | None = None) -> MagicMock:
    t = MagicMock()
    t.name = name
    t.description = f"tool {name}"
    schema: dict = {"properties": {"x": {"type": "string"}}}
    if required is not None:
        schema["required"] = required
    else:
        schema["properties"] = {}
    t.inputSchema = schema
    return t


def test_decide_schedule_keywords_chat_with_preset(monkeypatch):
    _patch_list_tools(monkeypatch, [])
    d = decide_route_auto("我想规划明天行程")
    assert d["route"] == "chat"
    assert d["mcp_tool"] is None
    assert d["preset"] == PRESET_SCHEDULE


def test_decide_obvious_mcp_uses_dynamic_tool_name(monkeypatch):
    ping = _make_tool("ping")
    _patch_list_tools(monkeypatch, [ping])
    d = decide_route_auto("请调用 ping")
    assert d["route"] == "mcp"
    assert d["mcp_tool"] == "ping"
    assert d["mcp_arguments"] == {}
    assert d["preset"] is None


def test_decide_llm_mcp_tool_from_list(monkeypatch):
    ping = _make_tool("ping")
    _patch_list_tools(monkeypatch, [ping])
    monkeypatch.setattr(
        "src.services.route_auto.complete_chat",
        lambda _msgs: '{"route":"mcp","mcp_tool":"ping","mcp_arguments":{}}',
    )
    d = decide_route_auto("随便说一句")
    assert d["route"] == "mcp"
    assert d["mcp_tool"] == "ping"


def test_decide_list_tools_fails_fallback_chat(monkeypatch):
    def _boom(_fn):
        raise OSError("mcp down")

    monkeypatch.setattr("src.services.route_auto.anyio.run", _boom)
    d = decide_route_auto("你好")
    assert d["route"] == "chat"
    assert d["preset"] is None

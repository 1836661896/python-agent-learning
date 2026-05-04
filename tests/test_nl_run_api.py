import src.routers.agent as agent_router_module


def test_nl_run_api_ok(client, monkeypatch):
    # 新逻辑： patch planner， 返回 builtin 命令
    monkeypatch.setattr(
        agent_router_module.llm_client,
        "plan",
        lambda user_text, mcp_tools, allowed_builtin_cmds: {
            "plan": {"kind": "builtin", "command": "time"},
            "meta": {"provider_used": "ollama", "fallback_used": False},
        },
    )

    text = "现在几点了"
    create_resp = client.post("/agent/nl-run", json={"text": text})
    assert create_resp.status_code == 200
    data = create_resp.json()
    assert data["code"] == 0
    assert data["data"]["command"] == "time"
    assert isinstance(data["data"]["result"], str)
    assert data["data"]["result"].endswith("UTC")
    assert data["data"]["planner_meta"]["provider_used"] == "ollama"
    assert data["data"]["planner_meta"]["fallback_used"] is False


def test_nl_run_api_reject_unknown(client, monkeypatch):
    # 返回不在白名单内的 builtin 命令， 触发拒绝
    monkeypatch.setattr(
        agent_router_module.llm_client,
        "plan",
        lambda user_text, mcp_tools, allowed_builtin_cmds: {
            "plan": {"kind": "builtin", "command": "unknown"},
            "meta": {"provider_used": "ollama", "fallback_used": False},
        },
    )

    text = "帮我删除 id=1 的任务"
    resp = client.post("/agent/nl-run", json={"text": text})

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 1
    assert "仅允许" in data["msg"]
    assert data["data"]["planner_meta"]["provider_used"] == "ollama"
    assert data["data"]["planner_meta"]["fallback_used"] is False


def test_nl_run_mcp_parse_error(client):
    # 显式 mcp 语法解析错误，走 parse_mcp_call 的错误分支（与 planner 无关）
    resp = client.post("/agent/nl-run", json={"text": "mcp ping =x a=1"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 1
    assert data["msg"] == "MCP 参数错误"
    assert data.get("data", {}).get("route") == "mcp"
    assert "参数名不能为空" in data["data"]["detail"]


def test_nl_run_manual_mcp_not_allowed_records_event(client, monkeypatch):
    captured = {}

    def _fake_record_event(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(agent_router_module, "record_event", _fake_record_event)
    monkeypatch.setattr(
        agent_router_module.mcp_client,
        "allowed_tool_names",
        lambda: {"ping", "now"},
    )

    resp = client.post("/agent/nl-run", json={"text": 'mcp echo {"text":"hi"}'})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 1
    assert body["msg"] == "不允许调用该 MCP 工具"
    assert body["data"]["route"] == "mcp"
    assert body["data"]["tool_name"] == "echo"
    assert body["data"]["allowed"] == ["now", "ping"]

    assert captured["type_"] == "mcp"
    assert captured["endpoint"] == "/agent/nl-run"
    assert captured["ok"] is False
    assert captured["summary"] == "mcp failed"
    assert captured["provider_used"] == "manual_mcp"
    assert captured["fallback_used"] is False
    assert captured["payload"]["error_type"] == "mcp_not_allowed"


def test_nl_run_manual_mcp_run_failed_records_event(client, monkeypatch):
    captured = {}

    def _fake_record_event(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(agent_router_module, "record_event", _fake_record_event)
    monkeypatch.setattr(
        agent_router_module.mcp_client,
        "allowed_tool_names",
        lambda: {"echo", "ping"},
    )
    monkeypatch.setattr(
        agent_router_module.mcp_client,
        "call_tool",
        lambda tool_name, args: {"ok": False, "msg": "mock mcp error", "data": {}},
    )

    resp = client.post("/agent/nl-run", json={"text": 'mcp echo {"text":"hi"}'})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 1
    assert body["msg"] == "执行失败"
    assert body["data"]["route"] == "mcp"
    assert body["data"]["tool_name"] == "echo"
    assert "mock mcp error" in body["data"]["detail"]

    assert captured["type_"] == "mcp"
    assert captured["ok"] is False
    assert captured["summary"] == "mcp failed"
    assert captured["payload"]["error_type"] == "mcp_run_failed"


def test_nl_run_manual_mcp_success_records_event(client, monkeypatch):
    captured = {}

    def _fake_record_event(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(agent_router_module, "record_event", _fake_record_event)
    monkeypatch.setattr(
        agent_router_module.mcp_client,
        "allowed_tool_names",
        lambda: {"echo", "ping"},
    )
    monkeypatch.setattr(
        agent_router_module.mcp_client,
        "call_tool",
        lambda tool_name, args: {"ok": True, "msg": "ok", "data": {"text": "hi"}},
    )

    resp = client.post("/agent/nl-run", json={"text": 'mcp echo {"text":"hi"}'})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["route"] == "mcp"
    assert body["data"]["tool_name"] == "echo"
    assert body["data"]["result"]["text"] == "hi"

    assert captured["type_"] == "mcp"
    assert captured["ok"] is True
    assert captured["summary"] == "mcp success: echo"

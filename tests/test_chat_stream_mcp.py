import json

import src.routers.chat as chat_module


def _fake_call_tool(tool_name: str, args: dict):
    """与 src/mcp/client.py 里 call_tool 成功时返回形状一致"""
    if tool_name == "echo" and args == {"text": "hi"}:
        return {
            "ok": True,
            "msg": "ok",
            "data": {
                "text": "hi",
                "structured": {"result": "hi"},
            },
        }
    return {"ok": False, "msg": "unexpected", "data": {}}


def test_chat_stream_mcp_echo_sse_order(client, monkeypatch):
    monkeypatch.setattr(
        chat_module.mcp_client,
        "allowed_tool_names",
        lambda: {"echo", "ping", "now"},
    )
    monkeypatch.setattr(chat_module.mcp_client, "call_tool", _fake_call_tool)

    resp = client.post(
        "/chat/stream",
        json={"message": 'mcp echo {"text": "hi"}'},
    )

    assert resp.status_code == 200
    assert "event-stream" in (resp.headers.get("content-type") or "").lower()

    body = resp.text
    # SSE：多行data： {...}；顺序应为 delta -> tool_result -> done
    d_delta = body.find('"type": "delta"')
    d_tool = body.find('"type": "tool_result"')
    d_done = body.find('"type": "done"')
    assert 0 <= d_delta < d_tool < d_done

    # 可选：抽查某一行时能解析的 JSON （第一条 data 行）
    for line in body.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line.removeprefix("data: ").strip())
            if payload.get("type") == "delta":
                assert payload.get("text") == "hi"
                break
        else:
            raise AssertionError("未找到 delta 事件")


def test_chat_stream_mcp_not_allowed(client, monkeypatch):
    monkeypatch.setattr(
        chat_module.mcp_client,
        "allowed_tool_names",
        lambda: {"ping", "now"},
    )

    resp = client.post(
        "/chat/stream",
        json={"message": 'mcp echo {"text": "hi"}'},
    )

    assert resp.status_code == 200
    body = resp.text
    assert '"type": "error"' in body
    assert "不允许调用该 MCP 工具" in body
    assert '"tool_name": "echo"' in body or '"tool_name":"echo"' in body.replace(
        " ", ""
    )


def test_chat_stream_mcp_not_allowed_records_event(client, monkeypatch):
    # 1) 仅允许 ping/now，故意不允许 echo
    monkeypatch.setattr(
        chat_module.mcp_client,
        "allowed_tool_names",
        lambda: {"ping", "now"},
    )

    # 2) 捕获 record_event 参数（避免真实写库）
    captured = {}

    def _fake_record_event(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(chat_module, "record_event", _fake_record_event)

    # 3) 请求手动 mcp
    resp = client.post(
        "/chat/stream",
        json={"message": 'mcp echo {"text": "hi"}'},
    )
    assert resp.status_code == 200
    body = resp.text
    assert '"type": "error"' in body

    # 4) 断言事件字段（这是本测试核心）
    assert captured["type_"] == "mcp"
    assert captured["endpoint"] == "/chat/stream"
    assert captured["ok"] is False
    assert captured["summary"] == "mcp failed"
    assert captured["provider_used"] == "manual_mcp"
    assert captured["fallback_used"] is False

    payload = captured["payload"]
    assert payload["route"] == "mcp"
    assert payload["tool_name"] == "echo"
    assert payload["error_type"] == "mcp_not_allowed"
    assert payload["allowed"] == ["now", "ping"]



def test_chat_stream_mcp_run_failed_records_event(client, monkeypatch):
    # 1) 允许 echo，确保能进入 call_tool 执行分支
    monkeypatch.setattr(
        chat_module.mcp_client,
        "allowed_tool_names",
        lambda: {"echo", "ping", "now"},
    )

    # 2) 模拟 MCP 执行失败（ok=False）
    monkeypatch.setattr(
        chat_module.mcp_client,
        "call_tool",
        lambda tool_name, args: {"ok": False, "msg": "mock mcp error", "data": {}},
    )

    # 3) 捕获 record_event 参数
    captured = {}

    def _fake_record_event(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(chat_module, "record_event", _fake_record_event)

    # 4) 发请求
    resp = client.post(
        "/chat/stream",
        json={"message": 'mcp echo {"text": "hi"}'},
    )
    assert resp.status_code == 200
    body = resp.text
    assert '"type": "error"' in body

    # 5) 断言事件
    assert captured["type_"] == "mcp"
    assert captured["endpoint"] == "/chat/stream"
    assert captured["ok"] is False
    assert captured["summary"] == "mcp failed"
    assert captured["provider_used"] == "manual_mcp"
    assert captured["fallback_used"] is False

    payload = captured["payload"]
    assert payload["route"] == "mcp"
    assert payload["tool_name"] == "echo"
    assert payload["error_type"] == "mcp_run_failed"
    assert "mock mcp error" in payload["detail"]
import src.routers.chat as chat_module


def test_chat_stream_plan_builtin(client, monkeypatch):
    # planner 返回 builtin
    monkeypatch.setattr(
        chat_module.llm_client,
        "plan",
        lambda user_text, mcp_tools, allowed_builtin_cmds: {
            "plan": {"kind": "builtin", "command": "time"},
            "meta": {"provider_used": "ollama", "fallback_used": False},
        },
    )

    resp = client.post("/chat/stream", json={"message": "现在几点了"})
    assert resp.status_code == 200
    body = resp.text

    # builtin 分支：delta + tool_result + done
    assert '"type": "delta"' in body
    assert '"type": "tool_result"' in body
    assert '"type": "done"' in body
    assert '"command": "time"' in body or '"command":"time"' in body.replace(" ", "")
    assert '"planner_meta"' in body


def test_chat_stream_plan_chat(client, monkeypatch):
    # planner 返回 chat，streaming 走 chat_streaming
    monkeypatch.setattr(
        chat_module.llm_client,
        "plan",
        lambda user_text, mcp_tools, allowed_builtin_cmds: {
            "plan": {"kind": "chat", "answer_hint": ""},
            "meta": {"provider_used": "ollama", "fallback_used": False},
        },
    )
    monkeypatch.setattr(
        chat_module.llm_client, "chat_streaming", lambda _msg: iter(["你", "好"])
    )

    resp = client.post("/chat/stream", json={"message": "你好呀"})
    assert resp.status_code == 200
    body = resp.text

    # chat 分支：只要有 delta + done，且不应有 tool_result
    assert '"type": "delta"' in body
    assert '"type": "done"' in body
    assert '"type": "tool_result"' not in body
    assert "你" in body and "好" in body


def test_chat_stream_plan_error(client, monkeypatch):
    # planner 抛错 -> 降级走 chat_streaming（不再返回 error）
    def _raise(*args, **kwargs):
        raise chat_module.PlanError("bad plan")

    monkeypatch.setattr(chat_module.llm_client, "plan", _raise)
    monkeypatch.setattr(
        chat_module.llm_client, "chat_streaming", lambda _msg: iter(["你", "好"])
    )

    resp = client.post("/chat/stream", json={"message": "随便说点啥"})
    assert resp.status_code == 200
    body = resp.text

    assert '"type": "delta"' in body
    assert '"type": "done"' in body
    assert '"type": "error"' not in body
    assert "你" in body and "好" in body


def test_chat_stream_planner_error_fallback_to_chat(client, monkeypatch):
    import src.routers.chat as chat_module

    def _raise(*args, **kwargs):
        raise chat_module.PlanError("bad json")

    monkeypatch.setattr(chat_module.llm_client, "plan", _raise)
    monkeypatch.setattr(
        chat_module.llm_client, "chat_streaming", lambda _m: iter(["你", "好"])
    )

    resp = client.post("/chat/stream", json={"message": "你好"})
    body = resp.text

    assert resp.status_code == 200
    assert '"type": "delta"' in body
    assert '"type": "done"' in body
    assert '"type": "error"' not in body


def test_chat_stream_plan_builtin_rejected_records_event(client, monkeypatch):
    monkeypatch.setattr(
        chat_module.llm_client,
        "plan",
        lambda user_text, mcp_tools, allowed_builtin_cmds: {
            "plan": {"kind": "builtin", "command": "unknown"},
            "meta": {"provider_used": "ollama", "fallback_used": False},
        },
    )

    captured = {}

    def _fake_record_event(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(chat_module, "record_event", _fake_record_event)

    resp = client.post("/chat/stream", json={"message": "帮我做危险操作"})
    assert resp.status_code == 200
    body = resp.text

    assert '"type": "delta"' in body
    assert '"type": "done"' in body
    assert "不在允许范围内" in body
    assert "解析结果：unknown" in body

    assert captured["type_"] == "builtin"
    assert captured["endpoint"] == "/chat/stream"
    assert captured["tool_succeeded"] is False
    assert captured["summary"] == "builtin rejected"
    assert captured["payload"]["error_type"] == "command_not_allowed"

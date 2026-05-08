import src.routers.chat as chat_module


def test_chat_api_plan_builtin(client, monkeypatch):
    monkeypatch.setattr(
        chat_module.llm_client,
        "plan",
        lambda user_text, mcp_tools, allowed_builtin_cmds: {
            "plan": {"kind": "builtin", "command": "time"},
            "meta": {"provider_used": "ollama", "fallback_used": False},
        },
    )

    resp = client.post("/chat", json={"message": "现在几点了"})
    assert resp.status_code == 200
    body = resp.json()

    assert body["code"] == 0
    data = body["data"]
    assert data["route"] == "builtin"
    assert data["command"] == "time"
    assert "planner_meta" in data
    assert data["planner_meta"]["provider_used"] == "ollama"
    assert data["planner_meta"]["fallback_used"] is False


def test_chat_api_plan_chat(client, monkeypatch):
    monkeypatch.setattr(
        chat_module.llm_client,
        "plan",
        lambda user_text, mcp_tools, allowed_builtin_cmds: {
            "plan": {"kind": "chat", "answer_hint": ""},
            "meta": {"provider_used": "zhipu", "fallback_used": True},
        },
    )
    monkeypatch.setattr(
        chat_module.llm_client, "chat_simple", lambda _msg: "你好，我是助手"
    )
    resp = client.post("/chat", json={"message": "你好"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    data = body["data"]
    assert data["route"] == "chat"
    assert data["text"] == "你好，我是助手"
    assert data["planner_meta"]["provider_used"] == "zhipu"
    assert data["planner_meta"]["fallback_used"] is True


def test_chat_plannerror_fallback_records_event(client, monkeypatch):
    import src.routers.chat as chat_module

    # 1) planner 抛错，触发 fallback chat 分支
    def _raise_plan_error(*args, **kwargs):
        raise chat_module.PlanError("planner failed")

    monkeypatch.setattr(chat_module.llm_client, "plan", _raise_plan_error)
    monkeypatch.setattr(
        chat_module.llm_client, "chat_simple", lambda _msg: "fallback reply"
    )

    # 2) 捕获 record_event 入参，避免真的写库
    captured = {}

    def _fake_record_event(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(chat_module, "record_event", _fake_record_event)

    # 3) 发请求
    resp = client.post("/chat", json=({"message": "测试 fallback"}))
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["route"] == "chat"
    assert body["data"]["text"] == "fallback reply"

    # 4) 断言事件以记录，且语义正确
    assert captured["type_"] == "chat"
    assert captured["endpoint"] == "/chat"
    assert captured["tool_succeeded"] is True
    assert captured["summary"] == "planner fallback chat"
    assert captured["provider_used"] == "planner_fallback_chat"
    assert captured["fallback_used"] is True
    assert captured["payload"]["route"] == "chat"
    assert captured["payload"]["message"] == "测试 fallback"
    assert captured["payload"]["reply"] == "fallback reply"


def test_chat_api_builtin_fail_records_event(client, monkeypatch):
    import src.routers.chat as chat_module

    # 1) planner 返回 builtin 路由
    monkeypatch.setattr(
        chat_module.llm_client,
        "plan",
        lambda **kwargs: {
            "plan": {"kind": "builtin", "command": "time"},
            "meta": {"provider_used": "ollama", "fallback_used": False},
        },
    )

    # 2) run_tool 失败，触发 builtin failed 分支
    monkeypatch.setattr(
        chat_module,
        "run_tool",
        lambda _cmd: (False, "mock tool failed", None),
    )

    # 3) 捕获 record_event 参数
    captured = {}

    def _fake_record_event(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(chat_module, "record_event", _fake_record_event)

    # 4) 请求并断言响应
    resp = client.post("/chat", json={"message": "现在几点了"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 1
    assert body["msg"] == "执行失败"

    # 5) 断言事件入库参数
    assert captured["type_"] == "builtin"
    assert captured["endpoint"] == "/chat"
    assert captured["tool_succeeded"] is False
    assert captured["summary"] == "builtin failed: time"
    assert captured["provider_used"] == "ollama"
    assert captured["fallback_used"] is False

    payload = captured["payload"]
    assert payload["route"] == "builtin"
    assert payload["command"] == "time"
    assert payload["tool_msg"] == "mock tool failed"
    assert payload["error_type"] == "builtin_run_failed"


def test_chat_api_builtin_rejected_records_event(client, monkeypatch):
    monkeypatch.setattr(
        chat_module.llm_client,
        "plan",
        lambda **kwargs: {
            "plan": {"kind": "builtin", "command": "unknown"},
            "meta": {"provider_used": "ollama", "fallback_used": False},
        },
    )

    captured = {}

    def _fake_record_event(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(chat_module, "record_event", _fake_record_event)

    resp = client.post("/chat", json={"message": "帮我删库"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 1
    assert "无法把这句话安全的转成可执行命令" in body["msg"]

    assert captured["type_"] == "builtin"
    assert captured["endpoint"] == "/chat"
    assert captured["tool_succeeded"] is False
    assert captured["summary"] == "builtin rejected"
    assert captured["payload"]["route"] == "builtin"
    assert captured["payload"]["command"] == "unknown"
    assert captured["payload"]["error_type"] == "command_not_allowed"

import src.routers.agent as agent_router_module


def test_nl_run_api_ok(client, monkeypatch):
    monkeypatch.setattr(agent_router_module, "nl_to_command", lambda _text: "time")

    text = "现在几点了"
    create_resp = client.post("/agent/nl-run", json={"text": text})
    assert create_resp.status_code == 200
    data = create_resp.json()
    assert data["code"] == 0
    assert data["data"]["command"] == "time"
    assert isinstance(data["data"]["result"], str)
    assert data["data"]["result"].endswith("UTC")


def test_nl_run_api_reject_unknown(client, monkeypatch):
    monkeypatch.setattr(agent_router_module, "nl_to_command", lambda _text: "unknown")

    text = "帮我删除 id=1 的任务"
    resp = client.post("/agent/nl-run", json={"text": text})

    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 1
    assert "仅允许" in data["msg"]

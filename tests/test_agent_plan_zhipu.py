import src.llm.agent_plan as plan_module


class _FakeResponse:
    def __init__(self, body: dict):
        self._body = body
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self._body


class _FakeClient:
    last_headers = None

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url, json=None, headers=None, **kwargs):
        _FakeClient.last_headers = headers
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"kind": "mcp", "tool_name": "echo", "arguments": {"text": "hi"}}',
                        }
                    }
                ]
            }
        )


def test_plan_with_zhipu_mcp_success(monkeypatch):
    monkeypatch.setenv("ZHIPU_API_KEY", "fake-key-for-test")
    monkeypatch.setattr(plan_module.httpx, "Client", _FakeClient)

    mcp_tools = [
        {"name": "echo", "description": "回显", "input_schema": {"type": "object"}},
        {"name": "ping", "description": "连通性", "input_schema": {"type": "object"}},
    ]
    allowed_builtin = {"time", "list", "help", "version", "echo", "add"}
    out = plan_module.plan_with_zhipu("帮我回显 hi", mcp_tools, allowed_builtin)
    assert out["kind"] == "mcp"
    assert out["tool_name"] == "echo"
    assert out["arguments"] == {"text": "hi"}

    assert _FakeClient.last_headers is not None
    assert _FakeClient.last_headers.get("Authorization") == "Bearer fake-key-for-test"

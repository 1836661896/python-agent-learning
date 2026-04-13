def test_agent_run_and_last_step_has_utc_timestamp(client):
    # 1) 运行一次 run
    run_agent_resp = client.post("/agent/run", json={"text": "time"})
    assert run_agent_resp.status_code == 200
    run_agent_data = run_agent_resp.json()
    assert run_agent_data["code"] == 0

    last_step_resp = client.get("/agent/last-step")
    assert last_step_resp.status_code == 200
    last_step_data = last_step_resp.json()
    assert last_step_data["code"] == 0

    step_list_resp = client.get("/agent/steps")
    assert step_list_resp.status_code == 200
    step_list_data = step_list_resp.json()
    assert step_list_data["code"] == 0

    step = last_step_data["data"]
    assert step["tool_name"] == "time"
    assert step["input_text"] == "time"
    assert isinstance(step["timestamp"], str)
    assert step["timestamp"].endswith(" UTC")

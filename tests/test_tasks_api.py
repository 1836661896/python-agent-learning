from datetime import datetime, timezone


def _unique_task_name() -> str:
    # 用时间戳拼唯一名字，避免“任务已存在”导致偶发报错
    return f"pytest-task-{datetime.now(timezone.utc).timestamp()}"


def test_tasks_create_list_delete_flow(client):
    task_name = _unique_task_name()

    # 1) create
    create_resp = client.post("/tasks", json={"description": task_name})
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    assert create_data["code"] == 0
    task_id = create_data["data"]["task_id"]

    # 2) list
    list_resp = client.get("/tasks")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["code"] == 0
    assert any(t["task_id"] == task_id for t in list_data["data"])

    # 3) delete
    delete_resp = client.delete(f"/tasks/{task_id}")
    assert delete_resp.status_code == 200
    delete_data = delete_resp.json()
    assert delete_data["code"] == 0


def test_tasks_create_duplicate_should_fail(client):
    task_name = _unique_task_name()

    # 1) create
    create_resp = client.post("/tasks", json={"description": task_name})
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    assert create_data["code"] == 0

    task_id = create_data["data"]["task_id"]

    # 2) 重复创建
    second_create_resp = client.post("/tasks", json={"description": task_name})
    assert second_create_resp.status_code == 200
    second_create_data = second_create_resp.json()
    assert second_create_data["code"] == 1

    # 3) delete
    delete_resp = client.delete(f"/tasks/{task_id}")
    assert delete_resp.status_code == 200
    delete_data = delete_resp.json()
    assert delete_data["code"] == 0


def test_tasks_delete_fail(client):
    task_id = int(datetime.now(timezone.utc).timestamp())
    delete_resp = client.delete(f"/tasks/{task_id}")
    assert delete_resp.status_code == 200
    delete_data = delete_resp.json()
    assert delete_data["code"] == 1

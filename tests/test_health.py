from fastapi.testclient import TestClient

from src.api import app

client = TestClient(app)


def test_health_success():
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["code"] == 0
    assert isinstance(data["msg"], str)

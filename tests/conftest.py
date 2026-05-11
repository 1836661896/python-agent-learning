import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from src.api import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def requires_postgres():
    """需要本机可连的 PostgreSQL（`.env` 中 `DATABASE_URL`）。"""
    from src.db.session import SessionLocal

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"PostgreSQL 不可用: {exc}")
    finally:
        db.close()

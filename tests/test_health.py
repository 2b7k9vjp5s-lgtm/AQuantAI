from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_root_returns_200() -> None:
    response = client.get("/")

    assert response.status_code == 200


def test_health_returns_200() -> None:
    response = client.get("/health")

    assert response.status_code == 200


def test_health_status_is_ok() -> None:
    response = client.get("/health")

    assert response.json()["status"] == "ok"

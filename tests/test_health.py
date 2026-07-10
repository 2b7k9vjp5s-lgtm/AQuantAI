from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_root_returns_200() -> None:
    response = client.get("/")

    assert response.status_code == 200


def test_root_reports_v02_local_dashboard_baseline() -> None:
    response = client.get("/")

    assert response.json() == {
        "project": "AQuantAI",
        "status": "v0.2 research-only local Dashboard baseline",
        "version": "0.2.0",
        "phase": "v0.2 local read-only Dashboard baseline",
    }


def test_fastapi_metadata_reports_v02() -> None:
    assert app.version == "0.2.0"
    assert app.openapi()["info"]["version"] == "0.2.0"


def test_health_returns_200() -> None:
    response = client.get("/health")

    assert response.status_code == 200


def test_health_status_is_ok() -> None:
    response = client.get("/health")

    assert response.json()["status"] == "ok"

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.main import app


ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "industry_analysis" / "static"


def test_accepted_result_page_exposes_two_layers_and_exact_selector() -> None:
    html = (STATIC / "accepted_result.html").read_text(encoding="utf-8")
    script = (STATIC / "accepted_result.js").read_text(encoding="utf-8")
    css = (STATIC / "accepted_result_assembly.css").read_text(encoding="utf-8")

    assert "已接受研究快照" in html
    assert "当前候选覆盖层" in html
    assert 'id="snapshot-select"' in html
    assert 'id="map-nodes"' in html
    assert "/industry-analysis/static/accepted_result_assembly.css" in html
    assert "output-link-revisions" in script
    assert "investment_candidate_snapshot_revision_id" in script
    assert "window.location.assign" in script
    assert 'picker.firstElementChild.value = ""' in script
    assert 'picker.value = result.candidate_overlay.snapshot_revision_id || ""' in script
    assert "applySnapshotSelection" in script
    assert "不使用最新版本回退" in html
    assert "latest_fallback_used" in script
    assert ".candidate-highlights" in css

    forbidden = (
        'fetch("http',
        "fetch('http",
        "WebSocket",
        "EventSource",
        "target price",
        "expected return",
    )
    assert all(token not in script for token in forbidden)


def test_page_route_and_openapi_include_read_only_assembly() -> None:
    client = TestClient(app)
    page = client.get(
        "/industry-analysis/sessions/"
        f"{uuid4()}/revisions/{uuid4()}/accepted-result"
    )
    assert page.status_code == 200
    assert "当前候选覆盖层" in page.text

    paths = client.get("/openapi.json").json()["paths"]
    path = (
        "/industry-analysis/api/output-link-revisions/"
        "{output_link_revision_id}/assembled-result"
    )
    assert path in paths
    assert set(paths[path]) == {"get"}

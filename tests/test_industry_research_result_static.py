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
    assert "完整已接受成员" in html
    assert "逐公司精确解释" in html
    assert "解释不改写历史" in html
    assert "产品、业绩传导、预期、估值、催化和风险只展开精确冻结" in html
    assert 'id="snapshot-select"' in html
    assert 'id="map-nodes"' in html
    assert 'id="company-explanations"' in html
    assert "/industry-analysis/static/accepted_result_assembly.css" in html
    assert "output-link-revisions" in script
    assert "investment_candidate_snapshot_revision_id" in script
    assert "window.location.assign" in script
    assert 'picker.firstElementChild.value = ""' in script
    assert 'picker.value = result.candidate_overlay.snapshot_revision_id || ""' in script
    assert "applySnapshotSelection" in script
    assert "不使用最新版本回退" in html
    assert "为什么受益 / 为什么是当前研究状态" in script
    assert "SOURCE_LAYER_LABELS" in script
    assert 'deterministic_candidate: "确定性规则/候选计算"' in script
    assert "memberSummaryCard" in script
    assert '"#complete-members"' in script
    assert '"#company-explanations"' in script
    assert "explained_result_content_sha256" in script
    assert "explained_result_uses_latest_fallback" in script
    assert "未显式选择包含该公司的候选快照，因此不推断当前候选状态" in script
    assert ".candidate-highlights" in css
    assert ".explained-research" in css
    assert ".source-deterministic_candidate" in css

    complete_index = html.index('id="complete-title"')
    overlay_index = html.index('id="overlay-title"')
    explanation_index = html.index('id="company-explanations-title"')
    assert complete_index < overlay_index < explanation_index

    forbidden = (
        'fetch("http',
        "fetch('http",
        "WebSocket",
        "EventSource",
        "localStorage",
        "setInterval(",
        "target price",
        "expected return",
        "priority_candidate =",
        "watch_candidate =",
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
    assert "完整已接受成员" in page.text
    assert "逐公司精确解释" in page.text

    paths = client.get("/openapi.json").json()["paths"]
    path = (
        "/industry-analysis/api/output-link-revisions/"
        "{output_link_revision_id}/assembled-result"
    )
    assert path in paths
    assert set(paths[path]) == {"get"}

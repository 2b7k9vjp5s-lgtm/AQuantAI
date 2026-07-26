from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.main import app


def test_owner_acceptance_and_result_pages_are_active() -> None:
    client = TestClient(app)
    session_id = uuid4()
    reviewed_id = uuid4()
    accepted_id = uuid4()

    acceptance = client.get(
        f"/industry-analysis/sessions/{session_id}/revisions/{reviewed_id}/acceptance"
    )
    assert acceptance.status_code == 200
    assert "研究归属已由审核计划冻结" in acceptance.text
    assert "生成变更预览" in acceptance.text
    assert "确认接受研究成果" in acceptance.text
    assert "页面不会自动提交、自动重试" in acceptance.text

    result = client.get(
        f"/industry-analysis/sessions/{session_id}/revisions/{accepted_id}/accepted-result"
    )
    assert result.status_code == 200
    assert "完整已接受成员" in result.text
    assert "supported 后续研究" in result.text
    assert "不构成投资建议" in result.text


def test_owner_acceptance_scripts_are_local_explicit_and_context_bound() -> None:
    root = Path(__file__).resolve().parents[1]
    acceptance = (
        root / "industry_analysis" / "static" / "owner_acceptance.js"
    ).read_text(encoding="utf-8")
    result = (
        root / "industry_analysis" / "static" / "accepted_result.js"
    ).read_text(encoding="utf-8")
    reviewed = (
        root / "industry_analysis" / "static" / "review_result.js"
    ).read_text(encoding="utf-8")
    history_guard = (
        root
        / "industry_analysis"
        / "static"
        / "workbench_phase2b_history_guard.js"
    ).read_text(encoding="utf-8")

    forbidden = (
        'fetch("http',
        "fetch('http",
        "WebSocket",
        "EventSource",
        "broker",
        "position sizing",
        "target price",
        "expected return",
    )
    assert all(
        token not in script
        for script in (acceptance, result, history_guard)
        for token in forbidden
    )
    assert "window.confirm" in acceptance
    assert "preview_fingerprint_sha256" in acceptance
    assert "owner_context.research_case_id" in acceptance
    assert "owner_context.industry_map_id" in acceptance
    assert "owner_context.industry_map_revision_id" in acceptance
    assert "页面不会自动新建或推断" in acceptance
    assert "ranking_applied" not in acceptance

    assert "accepted-result-view" in result
    assert "supported_handoff_members" in result
    assert "页面只读且不会移动版本" in result

    assert "aquantai.industry-thesis-acceptance-plan.v2" in reviewed
    assert "owner-acceptance-link" in reviewed
    assert "/acceptance?" in reviewed

    assert 'workflow_state !== "accepted_outputs_linked"' in history_guard
    assert 'kind: "accepted_result"' in history_guard
    assert 'label: "查看已接受成果"' in history_guard
    assert "/accepted-result?" in history_guard
    assert "as_of_cutoff" in history_guard
    assert "as_of_recorded_at_utc" in history_guard
    assert "window.location.assign" not in history_guard
    assert "visible_latest_revision_id" in history_guard

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import backend.api.industry_analysis as industry_api


ROOT = Path(__file__).resolve().parents[1]
CUTOFF = date(2026, 7, 23)
RECORDED = datetime(2026, 7, 23, 12, 30, tzinfo=timezone.utc)


def _history_item(workflow_state: str) -> dict:
    return {
        "session_id": str(uuid4()),
        "visible_latest_revision_id": str(uuid4()),
        "visible_latest_revision_number": 3,
        "information_cutoff_date": CUTOFF.isoformat(),
        "recorded_at_utc": RECORDED.isoformat(),
        "workflow_state": workflow_state,
    }


def test_exact_continuation_mapping_uses_response_owned_identity_and_boundaries() -> None:
    expected = {
        "draft": ("scope", "/industry-analysis/new"),
        "candidate_build_ready": (
            "candidate_review",
            "/industry-analysis/sessions/",
        ),
        "awaiting_review": (
            "candidate_review",
            "/industry-analysis/sessions/",
        ),
        "reviewed_plan_ready": ("result", "/industry-analysis/sessions/"),
    }

    for workflow_state, (kind, path_prefix) in expected.items():
        item = _history_item(workflow_state)
        continuation = industry_api._exact_continuation(item)
        assert continuation["kind"] == kind
        assert continuation["path"] is not None
        assert continuation["path"].startswith(path_prefix)
        parsed = urlparse(continuation["path"])
        query = parse_qs(parsed.query)
        assert query["as_of_cutoff"] == [item["information_cutoff_date"]]
        assert query["as_of_recorded_at_utc"] == [item["recorded_at_utc"]]
        assert item["session_id"] in continuation["path"]
        assert item["visible_latest_revision_id"] in continuation["path"]
        if workflow_state == "draft":
            assert query["revision_number"] == ["3"]


def test_non_continuable_unknown_and_malformed_states_fail_closed() -> None:
    for workflow_state in (
        "accepted_outputs_linked",
        "superseded",
        "abandoned",
        "future_unknown_state",
    ):
        continuation = industry_api._exact_continuation(
            _history_item(workflow_state)
        )
        assert continuation["kind"] == "unavailable"
        assert continuation["path"] is None
        assert continuation["reason_code"]

    malformed = _history_item("draft")
    malformed["visible_latest_revision_id"] = "not-a-uuid"
    continuation = industry_api._exact_continuation(malformed)
    assert continuation == {
        "kind": "unavailable",
        "label": "当前记录不可继续",
        "path": None,
        "reason_code": "malformed_exact_metadata",
    }


def test_adapter_adds_projection_without_changing_order_or_selecting_another_record(
    monkeypatch,
) -> None:
    newest = _history_item("abandoned")
    newest["thesis_title"] = "最新但已停止"
    older = _history_item("awaiting_review")
    older["thesis_title"] = "较旧且可继续"
    payload = {
        "sessions": [newest, older],
        "session_count": 2,
        "limit": 20,
        "has_more": False,
    }
    service_calls = 0

    class FakeQueryService:
        def __init__(self, _session):
            pass

        def list_sessions(self, **_kwargs):
            nonlocal service_calls
            service_calls += 1
            return payload

    class SessionContext:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(
        industry_api, "IndustryThesisWorkbenchQueryService", FakeQueryService
    )
    result = industry_api.list_industry_thesis_sessions(
        as_of_cutoff=CUTOFF,
        as_of_recorded_at_utc=RECORDED,
        limit=20,
        session_factory=lambda: SessionContext(),
    )

    assert service_calls == 1
    assert [item["thesis_title"] for item in result["sessions"]] == [
        "最新但已停止",
        "较旧且可继续",
    ]
    assert result["sessions"][0]["continuation"]["path"] is None
    assert result["sessions"][1]["continuation"]["kind"] == "candidate_review"


def test_bootstrap_navigation_activates_today_market_without_future_modules() -> None:
    modules = {item["key"]: item for item in industry_api._MODULES}
    assert modules["today-market"] == {
        "key": "today-market",
        "label": "今日市场",
        "state": "active",
        "path": "/today-market",
    }
    assert modules["industry-analysis"]["state"] == "active"
    assert modules["follow-track"]["state"] == "future"
    assert modules["follow-track"]["path"] is None
    assert modules["research-portfolio"]["state"] == "future"
    assert modules["research-portfolio"]["path"] is None


def test_phase2b_static_helper_uses_same_history_response_and_fail_closed_paths() -> None:
    script = (
        ROOT / "industry_analysis" / "static" / "workbench_phase2b.js"
    ).read_text(encoding="utf-8")

    assert "payload.sessions[0]" in script
    assert 'path === "/industry-analysis/api/sessions"' in script
    assert "fetch(`/industry-analysis/api/sessions" not in script
    assert ".find(" not in script
    assert "parsed.origin !== window.location.origin" in script
    assert "kind === \"unavailable\"" in script
    assert "path === null" in script
    assert "window.localStorage" not in script
    assert "window.location.assign" not in script
    assert "http://" not in script
    assert "https://" not in script


def test_five_step_copy_primary_action_and_conflict_contracts_are_static() -> None:
    script = (
        ROOT / "industry_analysis" / "static" / "workbench_phase2b.js"
    ).read_text(encoding="utf-8")
    for label in ("研究主题", "确认范围", "候选公司", "人工审核", "研究结果"):
        assert label in script
    for heading in ("发生了什么", "为什么重要", "现在可以做什么"):
        assert heading in script
    assert 'item.setAttribute("aria-current", "step")' in script
    assert 'item.setAttribute("aria-disabled", "true")' in script
    assert "demotePrimaryActions" in script
    assert "makePrimary" in script
    assert "response.status === 409" in script
    assert "保留当前页面中的未保存决定" in script


def test_participating_pages_load_phase2b_before_existing_page_scripts() -> None:
    paths = (
        ROOT / "industry_analysis" / "static" / "workbench.html",
        ROOT / "industry_analysis" / "static" / "candidate_review.html",
        ROOT / "industry_analysis" / "static" / "review_result.html",
    )
    existing = {
        "workbench.html": "workbench.js",
        "candidate_review.html": "candidate_review.js",
        "review_result.html": "review_result.js",
    }
    for path in paths:
        html = path.read_text(encoding="utf-8")
        assert "workbench_phase2b.css" in html
        assert "workbench_phase2b.js" in html
        assert html.index("workbench_phase2b.js") < html.index(existing[path.name])
        assert 'id="phase2b-workflow"' in html
        assert "UUID" not in html
        assert "fingerprint" not in html.lower()


def test_workbench_navigation_and_first_use_are_honest() -> None:
    html = (
        ROOT / "industry_analysis" / "static" / "workbench.html"
    ).read_text(encoding="utf-8")
    helper = (
        ROOT / "industry_analysis" / "static" / "workbench_phase2b.js"
    ).read_text(encoding="utf-8")

    assert 'href="/today-market"' in html
    assert "本地快照" in html
    assert html.count('aria-disabled="true"') == 2
    assert 'id="recent-research-panel"' in html
    assert "不会跳过停止或不可继续的记录" in html
    for phrase in ("描述研究主题", "确认研究范围", "审核完整候选池"):
        assert phrase in helper
    assert "不会用演示数据伪装为当前研究" in html
    assert "模拟收益" not in html


def test_scope_save_requires_successful_check_and_review_conflict_keeps_dom_input() -> None:
    html = (
        ROOT / "industry_analysis" / "static" / "workbench.html"
    ).read_text(encoding="utf-8")
    review_script = (
        ROOT / "industry_analysis" / "static" / "candidate_review.js"
    ).read_text(encoding="utf-8")

    assert 'id="scope-save-button"' in html
    assert 'id="scope-save-button" class="button button-secondary" type="submit" disabled' in html
    assert "scopePrimary(true)" in (
        ROOT / "industry_analysis" / "static" / "workbench_phase2b.js"
    ).read_text(encoding="utf-8")
    assert "已保留当前页面中的全部选择和文字" in review_script
    assert "页面不会自动重试" in review_script

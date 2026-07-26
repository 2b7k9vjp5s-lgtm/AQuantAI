"""Offline ordinary-user acceptance and accepted-result usability demo."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.main import app
from scripts.demo_industry_thesis_owner_acceptance import (
    build_industry_thesis_owner_acceptance_demo_payload,
)


def run_demo() -> dict:
    core = build_industry_thesis_owner_acceptance_demo_payload()
    assert core["workflow_state"] == "accepted_outputs_linked"
    assert core["complete_member_count"] == 3
    assert core["supported_handoff_count"] == 2
    assert core["accepted_candidate_pool_revision_present"] is True
    assert core["ranking_applied"] is False

    session_id = uuid4()
    reviewed_id = uuid4()
    accepted_id = uuid4()
    client = TestClient(app)
    acceptance = client.get(
        f"/industry-analysis/sessions/{session_id}/revisions/{reviewed_id}/acceptance"
    )
    accepted = client.get(
        f"/industry-analysis/sessions/{session_id}/revisions/{accepted_id}/accepted-result"
    )
    assert acceptance.status_code == 200
    assert accepted.status_code == 200
    assert "研究归属已由审核计划冻结" in acceptance.text
    assert "新建与追加必须显式作者化" in acceptance.text
    assert "Map assertion、Case Claim" in acceptance.text
    assert "完整已接受成员" in accepted.text

    root = Path(__file__).resolve().parents[1]
    acceptance_script = (
        root / "industry_analysis" / "static" / "owner_acceptance.js"
    ).read_text(encoding="utf-8")
    accepted_script = (
        root / "industry_analysis" / "static" / "accepted_result.js"
    ).read_text(encoding="utf-8")
    scripts = [acceptance_script, accepted_script]
    forbidden = (
        'fetch("http',
        "fetch('http",
        "WebSocket",
        "EventSource",
        "broker",
        "target price",
        "expected return",
    )
    assert all(token not in script for script in scripts for token in forbidden)
    assert 'const OP_APPEND = "append_beneficiary_revision"' in acceptance_script
    assert (
        'const OP_CREATE = "create_beneficiary_identity_and_revision"'
        in acceptance_script
    )
    assert "map_assertion_revisions" in acceptance_script
    assert "claim_revision_ids" in acceptance_script
    assert 'semantic_operation: "none"' in acceptance_script

    return {
        "core_golden_path": core,
        "ordinary_pages": {
            "acceptance_page": "active",
            "accepted_result_page": "active",
            "explicit_preview_required": True,
            "explicit_commit_confirmation_required": True,
            "explicit_stage1_reuse": True,
            "explicit_stage1_append": True,
            "explicit_stage1_create": True,
            "context_bound_assertion_and_claim_authoring": True,
            "exact_history_reopening": True,
        },
        "boundaries": {
            "external_network": False,
            "automatic_retry": False,
            "automatic_context_inference": False,
            "cross_revision_semantic_reuse": False,
            "ranking_or_scoring": False,
            "not_investment_advice": True,
        },
    }


def main() -> None:
    print(json.dumps(run_demo(), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.main import app
from industry_alpha.industry_research_e2e_rules import (
    acceptance_view_snapshot_content_sha256,
)


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
    assert "新建与追加必须显式作者化" in acceptance.text
    assert "受益类型、assessment 状态、Map assertion、Case Claim" in acceptance.text
    assert "生成变更预览" in acceptance.text
    assert "确认接受研究成果" in acceptance.text
    assert "页面不会自动提交、自动重试、自动撤销" in acceptance.text
    main_script = acceptance.text.index(
        "/industry-analysis/static/owner_acceptance.js"
    )
    pool_script = acceptance.text.index(
        "/industry-analysis/static/owner_acceptance_pool.js"
    )
    assert main_script < pool_script

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
    pool = (
        root / "industry_analysis" / "static" / "owner_acceptance_pool.js"
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
        for script in (acceptance, pool, result, history_guard)
        for token in forbidden
    )
    assert "window.confirm" in acceptance
    assert "preview_fingerprint_sha256" in acceptance
    assert "owner_context.research_case_id" in acceptance
    assert "owner_context.industry_map_id" in acceptance
    assert "owner_context.industry_map_revision_id" in acceptance
    assert 'const OP_REUSE = "reuse_exact_beneficiary_revision"' in acceptance
    assert 'const OP_APPEND = "append_beneficiary_revision"' in acceptance
    assert 'const OP_CREATE = "create_beneficiary_identity_and_revision"' in acceptance
    assert "expected_latest_revision_id" in acceptance
    assert "map_assertion_revisions" in acceptance
    assert "claim_revision_ids" in acceptance
    assert "legacy_beneficiary_kind" in acceptance
    assert "assessment_status" in acceptance
    assert 'semantic_operation: "none"' in acceptance
    assert "selectedOptions" in acceptance
    assert "页面不会根据股票、名称或唯一可达路径自动决定" in acceptance
    assert "ranking_applied" not in acceptance
    assert "acceptance_view_snapshot_contract_version" in acceptance
    assert "acceptance_view_snapshot_content_sha256" in acceptance
    assert "state.view.acceptance_view_snapshot_content_sha256" in acceptance
    assert "crypto.subtle" not in acceptance
    assert "Web Crypto" not in acceptance
    assert ".digest(" not in acceptance

    assert 'const MODE_REUSE = "reuse_exact_supported_handoff"' in pool
    assert "beneficiary_revision_ids" in pool
    assert "exactIdSetEqual" in pool
    assert "eligibleReuseOptions" in pool
    assert "exactSupportedRevisionIds" in pool
    assert "selection.option.revision_number" in pool
    assert "已从所选候选池" in pool
    assert "精确预填标题和范围" in pool
    assert "复用不会写入新的候选池 Revision" in pool
    assert "invalid_candidate_pool_selection" in pool

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


def _canonical_contract_view() -> dict:
    authoring = {
        "legacy_beneficiary_kind_options": [
            {"value": "direct", "label": "直接受益"}
        ],
        "assessment_status_options": [
            {"value": "supported", "label": "已有支持"}
        ],
        "map_assertion_options": [
            {
                "assertion_kind": "node",
                "assertion_revision_id": "assertion-revision-1",
                "ordinary_label": "产业链节点 · 关键材料",
                "assertion_status": "accepted",
            }
        ],
        "claim_revision_options": [
            {
                "claim_revision_id": "claim-revision-1",
                "ordinary_label": "需求增长传导至材料环节",
                "claim_kind": "industry_driver",
                "claim_status": "accepted",
                "claim_key": "claim-key-1",
            }
        ],
    }
    return {
        "reviewed_session_revision_id": "reviewed-revision-1",
        "expected_session_latest_revision_number": 3,
        "reviewed_plan_fingerprint_sha256": "a" * 64,
        "owner_context": {
            "owner_context_contract_version": "owner-context-v2",
            "research_case_id": "case-1",
            "map_mode": "reuse_exact_existing_map_revision",
            "industry_map_id": "map-1",
            "industry_map_revision_id": "map-revision-1",
            "ordinary_context_label": "仅用于展示",
        },
        "information_cutoff_date": "2026-07-28",
        "owner_acceptance_plan_version": "owner-acceptance-v1",
        "members": [
            {
                "sequence": 0,
                "reviewed_candidate_revision_id": "candidate-revision-1",
                "ordinary_identity_label": "示例公司",
                "reviewed_proposal_exposure": "direct",
                "frozen_stock_binding": {
                    "state": "available",
                    "stock_basic_record_id": 1,
                    "ordinary_label": "示例公司（000001）",
                    "source": "fixture",
                    "stock_code": "000001",
                    "exchange": "SZSE",
                    "industry": "仅展示行业",
                },
                "stage1_reuse_options": [
                    {
                        "beneficiary_id": "beneficiary-1",
                        "beneficiary_revision_id": "beneficiary-revision-1",
                        "revision_number": 2,
                        "stock_basic_record_id": 1,
                        "legacy_beneficiary_kind": "direct",
                        "assessment_status": "supported",
                        "rationale_summary": "受益路径已确认",
                        "semantic_reuse_options": [
                            {
                                "profile_id": "profile-1",
                                "profile_revision_id": "profile-revision-1",
                                "summary": "直接受益语义",
                                "overall_status": "accepted",
                            }
                        ],
                    }
                ],
                "stage1_append_options": [
                    {
                        "beneficiary_id": "beneficiary-1",
                        "expected_latest_revision_id": "beneficiary-revision-1",
                        "revision_number": 2,
                        "stock_basic_record_id": 1,
                        "source": "fixture",
                        "stock_code": "000001",
                        "current_legacy_beneficiary_kind": "direct",
                        "current_assessment_status": "supported",
                        "current_rationale_summary": "受益路径已确认",
                    }
                ],
                "stage1_create_contract": {
                    "available": False,
                    "stock_basic_record_id": 1,
                    "source": "fixture",
                    "stock_code": "000001",
                    "context_locked": True,
                    **deepcopy(authoring),
                    "blocking_reason": "该身份已存在，仅用于展示。",
                },
                "stage1_authoring_contract": deepcopy(authoring),
                "semantic_authoring_state": "reuse_or_none_only",
                "blocking_reasons": [
                    {"code": "display-only", "message": "仅用于展示的阻断文案。"}
                ],
            }
        ],
        "candidate_pool_operation_contract": {
            "create_contract": {
                "mode": "create_supported_handoff",
                "pool_key": "pool-key",
                "title_default": "supported 后续研究",
                "scope_default": "精确 supported 成员",
            },
            "append_options": [
                {
                    "candidate_pool_id": "pool-1",
                    "expected_latest_revision_id": "pool-revision-1",
                    "revision_number": 1,
                    "title": "候选池",
                    "scope": "精确范围",
                }
            ],
            "reuse_options": [
                {
                    "candidate_pool_id": "pool-1",
                    "candidate_pool_revision_id": "pool-revision-1",
                    "revision_number": 1,
                    "title": "候选池",
                    "scope": "精确范围",
                    "beneficiary_revision_ids": ["beneficiary-revision-1"],
                }
            ],
            "zero_supported_contract": {"mode": "none_no_supported_members"},
        },
        "output_metadata_defaults": {
            "output_title": "接受结果",
            "output_scope": "精确产业研究范围",
        },
        "technical_details": {"display_only": True},
    }


def test_snapshot_hash_excludes_presentation_only_copy_but_keeps_substantive_options() -> None:
    original = _canonical_contract_view()
    baseline = acceptance_view_snapshot_content_sha256(original)

    presentation = deepcopy(original)
    presentation["owner_context"]["ordinary_context_label"] = "展示文案已变化"
    member = presentation["members"][0]
    member["ordinary_identity_label"] = "展示名称已变化"
    member["frozen_stock_binding"]["ordinary_label"] = "展示证券名称已变化"
    member["frozen_stock_binding"]["exchange"] = "展示交易所已变化"
    member["frozen_stock_binding"]["industry"] = "展示行业已变化"
    member["blocking_reasons"][0]["message"] = "展示阻断文案已变化"
    member["stage1_create_contract"]["blocking_reason"] = "展示创建提示已变化"
    for contract in (
        member["stage1_create_contract"],
        member["stage1_authoring_contract"],
    ):
        contract["legacy_beneficiary_kind_options"][0]["label"] = "展示受益类型"
        contract["assessment_status_options"][0]["label"] = "展示评估状态"
        contract["map_assertion_options"][0]["ordinary_label"] = "展示地图断言"
        contract["claim_revision_options"][0]["ordinary_label"] = "展示 Claim"
    presentation["technical_details"]["display_only"] = False

    assert acceptance_view_snapshot_content_sha256(presentation) == baseline

    substantive = deepcopy(original)
    substantive["members"][0]["stage1_reuse_options"][0][
        "assessment_status"
    ] = "disputed"
    assert acceptance_view_snapshot_content_sha256(substantive) != baseline

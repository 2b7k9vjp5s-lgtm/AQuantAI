from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

import backend.api.industry_analysis_acceptance as acceptance_api
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    IndustryThesisOwnerAcceptanceError,
)
from scripts.run_industry_thesis_ordinary_user_acceptance_fixture import (
    _view,
    api_client,
    build_golden_fixture,
    golden_plan,
    owner_counts,
    query_params,
)


UTC = timezone.utc
CUTOFF = date(2026, 7, 9)
BOUNDARY = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class _Session:
    def __init__(self, rows):
        self.rows = rows

    def execute(self, _statement):
        return _Rows(self.rows)


def _request_payload(*, bindings, pool_operation):
    case_id = uuid4()
    map_id = uuid4()
    map_revision_id = uuid4()
    reviewed_id = uuid4()
    return acceptance_api.OwnerAcceptancePlanRequest(
        reviewed_session_revision_id=reviewed_id,
        expected_session_latest_revision_number=3,
        reviewed_plan_fingerprint_sha256="a" * 64,
        research_case_id=case_id,
        map_mode="reuse_exact_existing_map_revision",
        industry_map_id=map_id,
        industry_map_revision_id=map_revision_id,
        candidate_owner_bindings=bindings,
        candidate_pool_operation=pool_operation,
        output_title="精确成果",
        output_scope="精确范围",
        information_cutoff_date=CUTOFF,
        revision_note="明确接受",
        owner_acceptance_plan_version=(
            "aquantai.industry-thesis-owner-acceptance-plan.v1"
        ),
    )


def test_multiple_owner_contexts_fail_closed_even_when_coverage_is_unequal() -> None:
    case_a, map_a, revision_a = uuid4(), uuid4(), uuid4()
    case_b, map_b, revision_b = uuid4(), uuid4(), uuid4()
    view = {
        "members": [
            {
                "frozen_stock_binding": {
                    "state": "available",
                    "stock_basic_record_id": 1,
                }
            },
            {
                "frozen_stock_binding": {
                    "state": "available",
                    "stock_basic_record_id": 2,
                }
            },
        ],
        "research_case": {"id": str(case_a)},
        "industry_map": {"id": str(map_a), "revision_id": str(revision_a)},
    }
    rows = [
        SimpleNamespace(
            case_id=case_a,
            map_id=map_a,
            selected_map_revision_id=revision_a,
        ),
        SimpleNamespace(
            case_id=case_b,
            map_id=map_b,
            selected_map_revision_id=revision_b,
        ),
    ]
    with pytest.raises(IndustryThesisOwnerAcceptanceError) as raised:
        acceptance_api._require_single_exact_owner_context(
            _Session(rows),
            view,
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=BOUNDARY,
        )
    assert raised.value.code == "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED"


def test_http_rejects_context_substitution_and_semantic_authoring_without_writes() -> None:
    fixture = build_golden_fixture()
    try:
        with api_client(fixture.database) as client:
            view = _view(client, fixture.reviewed)
            plan = golden_plan(view)
            before = owner_counts(fixture.database.factory)

            substituted = {**plan, "research_case_id": str(uuid4())}
            response = client.post(
                f"/industry-analysis/api/session-revisions/"
                f"{fixture.reviewed.reviewed_session_revision_id}/owner-acceptance/preview",
                params=query_params(fixture.reviewed),
                json=substituted,
            )
            assert response.status_code == 409
            assert response.json()["detail"]["code"] == (
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE"
            )
            assert owner_counts(fixture.database.factory) == before

            semantic_append = golden_plan(view)
            semantic_append["candidate_owner_bindings"][0][
                "semantic_operation"
            ] = "append_complete_semantic_profile"
            semantic_append["candidate_owner_bindings"][0]["semantic"] = {
                "unexpected": "ordinary-user semantic authoring"
            }
            response = client.post(
                f"/industry-analysis/api/session-revisions/"
                f"{fixture.reviewed.reviewed_session_revision_id}/owner-acceptance/preview",
                params=query_params(fixture.reviewed),
                json=semantic_append,
            )
            assert response.status_code == 422
            assert response.json()["detail"]["code"] == (
                "INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_PAYLOAD_INCOMPLETE"
            )
            assert owner_counts(fixture.database.factory) == before
    finally:
        fixture.database.engine.dispose()


def test_exact_pool_reuse_requires_all_supported_members_to_be_exact_reuse() -> None:
    candidate_a, candidate_b = uuid4(), uuid4()
    beneficiary_a, beneficiary_b = uuid4(), uuid4()
    revision_a, revision_b = uuid4(), uuid4()
    pool_id, pool_revision_id = uuid4(), uuid4()
    bindings = [
        {
            "reviewed_candidate_revision_id": str(candidate_a),
            "sequence": 0,
            "stage1_operation": "reuse_exact_beneficiary_revision",
            "stage1": {
                "beneficiary_id": str(beneficiary_a),
                "beneficiary_revision_id": str(revision_a),
                "stock_basic_record_id": 1,
            },
            "semantic_operation": "none",
            "semantic": None,
            "readiness_note": "明确记录",
        },
        {
            "reviewed_candidate_revision_id": str(candidate_b),
            "sequence": 1,
            "stage1_operation": "reuse_exact_beneficiary_revision",
            "stage1": {
                "beneficiary_id": str(beneficiary_b),
                "beneficiary_revision_id": str(revision_b),
                "stock_basic_record_id": 2,
            },
            "semantic_operation": "none",
            "semantic": None,
            "readiness_note": "明确记录",
        },
    ]
    view = {
        "members": [
            {
                "reviewed_candidate_revision_id": str(candidate_a),
                "stage1_reuse_options": [
                    {
                        "beneficiary_id": str(beneficiary_a),
                        "beneficiary_revision_id": str(revision_a),
                        "stock_basic_record_id": 1,
                        "assessment_status": "supported",
                    }
                ],
            },
            {
                "reviewed_candidate_revision_id": str(candidate_b),
                "stage1_reuse_options": [
                    {
                        "beneficiary_id": str(beneficiary_b),
                        "beneficiary_revision_id": str(revision_b),
                        "stock_basic_record_id": 2,
                        "assessment_status": "supported",
                    }
                ],
            },
        ],
        "candidate_pool_operation_contract": {
            "reuse_options": [
                {
                    "candidate_pool_id": str(pool_id),
                    "candidate_pool_revision_id": str(pool_revision_id),
                    "beneficiary_revision_ids": [str(revision_a), str(revision_b)],
                }
            ]
        },
    }
    payload = _request_payload(
        bindings=bindings,
        pool_operation={
            "mode": "reuse_exact_supported_handoff",
            "candidate_pool_id": str(pool_id),
            "candidate_pool_revision_id": str(pool_revision_id),
        },
    )
    acceptance_api._validate_reuse_pool_selection(payload, view)

    view["candidate_pool_operation_contract"]["reuse_options"][0][
        "beneficiary_revision_ids"
    ] = [str(revision_a)]
    with pytest.raises(IndustryThesisOwnerAcceptanceError) as raised:
        acceptance_api._validate_reuse_pool_selection(payload, view)
    assert raised.value.code == (
        "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH"
    )

    create_supported = [dict(bindings[0]), dict(bindings[1])]
    create_supported[1] = {
        **create_supported[1],
        "stage1_operation": "append_beneficiary_revision",
        "stage1": {
            "beneficiary_id": str(beneficiary_b),
            "expected_latest_revision_id": str(revision_b),
            "stock_basic_record_id": 2,
            "legacy_beneficiary_kind": "direct",
            "assessment_status": "supported",
            "rationale_summary": "明确追加",
            "map_assertion_revisions": [],
            "claim_revision_ids": [],
        },
    }
    payload = _request_payload(
        bindings=create_supported,
        pool_operation={
            "mode": "reuse_exact_supported_handoff",
            "candidate_pool_id": str(pool_id),
            "candidate_pool_revision_id": str(pool_revision_id),
        },
    )
    with pytest.raises(IndustryThesisOwnerAcceptanceError) as raised:
        acceptance_api._validate_reuse_pool_selection(payload, view)
    assert raised.value.code == (
        "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH"
    )


def test_cross_pool_or_zero_supported_company_research_is_not_attached() -> None:
    case_id, map_id, map_revision_id = uuid4(), uuid4(), uuid4()
    beneficiary_id, revision_id, pool_revision_id = uuid4(), uuid4(), uuid4()
    base_member = {
        "beneficiary_id": str(beneficiary_id),
        "beneficiary_revision_id": str(revision_id),
        "stock_basic_record_id": 7,
        "included_in_supported_handoff": True,
        "semantic": {"state": "supported"},
        "company_research": {
            "state": "supported",
            "company_research_id": str(uuid4()),
            "company_research_revision_id": str(uuid4()),
            "reason": None,
        },
        "readiness_reason_codes": [],
    }
    result = {
        "members": [dict(base_member)],
        "supported_handoff_members": [dict(base_member)],
        "accepted_candidate_pool_revision_id": str(pool_revision_id),
        "draft_or_disputed_count": 0,
        "technical_details": {
            "research_case_id": str(case_id),
            "industry_map_id": str(map_id),
            "industry_map_revision_id": str(map_revision_id),
        },
    }
    sanitized = acceptance_api._apply_exact_company_research_readiness(
        _Session([]),
        result,
        as_of_cutoff=CUTOFF,
        as_of_recorded_at_utc=BOUNDARY,
    )
    assert sanitized["members"][0]["company_research"] == {
        "state": "missing",
        "company_research_id": None,
        "company_research_revision_id": None,
        "reason": "exact_company_research_not_found",
    }
    assert sanitized["company_research_ready_count"] == 0

    zero_member = dict(base_member)
    zero_member["included_in_supported_handoff"] = False
    zero_result = {
        "members": [zero_member],
        "supported_handoff_members": [],
        "accepted_candidate_pool_revision_id": None,
        "draft_or_disputed_count": 1,
        "technical_details": {
            "research_case_id": str(case_id),
            "industry_map_id": str(map_id),
            "industry_map_revision_id": str(map_revision_id),
        },
    }
    sanitized = acceptance_api._apply_exact_company_research_readiness(
        _Session([]),
        zero_result,
        as_of_cutoff=CUTOFF,
        as_of_recorded_at_utc=BOUNDARY,
    )
    assert sanitized["members"][0]["company_research"]["reason"] == (
        "no_supported_handoff_pool"
    )
    assert sanitized["company_research_ready_count"] == 0


def test_pool_reuse_guard_is_local_and_loaded_before_acceptance_flow() -> None:
    root = Path(__file__).resolve().parents[1] / "industry_analysis" / "static"
    html = (root / "owner_acceptance.html").read_text(encoding="utf-8")
    script = (root / "pool_reuse_guard.js").read_text(encoding="utf-8")
    assert html.index("pool_reuse_guard.js") < html.index("owner_acceptance.js")
    assert "reuse_exact_supported_handoff" in script
    assert "assessment_status === \"supported\"" in script
    assert "equalMembers" in script
    assert "option.disabled = !allowed" in script
    assert "fetch(\"http" not in script
    assert "innerHTML" not in script
    assert "localStorage" not in script

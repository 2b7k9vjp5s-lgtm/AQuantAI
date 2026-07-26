from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

import backend.api.industry_analysis_acceptance as acceptance_api
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    IndustryThesisOwnerAcceptanceError,
)
from scripts.run_industry_thesis_ordinary_user_acceptance_fixture import (
    CUTOFF,
    _view,
    api_client,
    build_golden_fixture,
    golden_plan,
    owner_counts,
    query_params,
)


UTC = timezone.utc
BOUNDARY = datetime(2026, 7, 10, 12, 0, tzinfo=UTC)


def _plan_request(
    *,
    bindings: list[dict[str, object]],
    pool_operation: dict[str, object],
) -> acceptance_api.OwnerAcceptancePlanRequest:
    return acceptance_api.OwnerAcceptancePlanRequest(
        reviewed_session_revision_id=uuid4(),
        expected_session_latest_revision_number=3,
        reviewed_plan_fingerprint_sha256="a" * 64,
        research_case_id=uuid4(),
        map_mode="reuse_exact_existing_map_revision",
        industry_map_id=uuid4(),
        industry_map_revision_id=uuid4(),
        candidate_owner_bindings=bindings,
        candidate_pool_operation=pool_operation,
        output_title="精确成果",
        output_scope="精确范围",
        information_cutoff_date=date(2026, 7, 9),
        revision_note="明确接受",
        owner_acceptance_plan_version=(
            "aquantai.industry-thesis-owner-acceptance-plan.v1"
        ),
    )


def _reuse_binding(
    *,
    candidate_id: UUID,
    beneficiary_id: UUID,
    beneficiary_revision_id: UUID,
    stock_basic_record_id: int,
    sequence: int,
) -> dict[str, object]:
    return {
        "reviewed_candidate_revision_id": str(candidate_id),
        "sequence": sequence,
        "stage1_operation": "reuse_exact_beneficiary_revision",
        "stage1": {
            "beneficiary_id": str(beneficiary_id),
            "beneficiary_revision_id": str(beneficiary_revision_id),
            "stock_basic_record_id": stock_basic_record_id,
        },
        "semantic_operation": "none",
        "semantic": None,
        "readiness_note": "明确记录",
    }


def test_unequal_multi_context_coverage_fails_closed() -> None:
    case_a, map_a, map_revision_a = uuid4(), uuid4(), uuid4()
    case_b, map_b, map_revision_b = uuid4(), uuid4(), uuid4()
    beneficiary_a1, beneficiary_a2, beneficiary_b1 = uuid4(), uuid4(), uuid4()
    revision_a1, revision_a2, revision_b1 = uuid4(), uuid4(), uuid4()

    graph = acceptance_api._LoadedAcceptanceGraph()
    graph.beneficiaries = {
        beneficiary_a1: SimpleNamespace(
            id=beneficiary_a1,
            case_id=case_a,
            map_id=map_a,
        ),
        beneficiary_a2: SimpleNamespace(
            id=beneficiary_a2,
            case_id=case_a,
            map_id=map_a,
        ),
        beneficiary_b1: SimpleNamespace(
            id=beneficiary_b1,
            case_id=case_b,
            map_id=map_b,
        ),
    }
    graph.beneficiary_revisions = {
        revision_a1: SimpleNamespace(
            id=revision_a1,
            beneficiary_id=beneficiary_a1,
            stock_basic_record_id=1,
            assessment_status="supported",
            information_cutoff_date=date(2026, 7, 9),
            recorded_at_utc=BOUNDARY,
            selected_map_revision_id=map_revision_a,
        ),
        revision_a2: SimpleNamespace(
            id=revision_a2,
            beneficiary_id=beneficiary_a2,
            stock_basic_record_id=2,
            assessment_status="draft",
            information_cutoff_date=date(2026, 7, 9),
            recorded_at_utc=BOUNDARY,
            selected_map_revision_id=map_revision_a,
        ),
        revision_b1: SimpleNamespace(
            id=revision_b1,
            beneficiary_id=beneficiary_b1,
            stock_basic_record_id=3,
            assessment_status="disputed",
            information_cutoff_date=date(2026, 7, 9),
            recorded_at_utc=BOUNDARY,
            selected_map_revision_id=map_revision_b,
        ),
    }
    view = {
        "members": [
            {
                "frozen_stock_binding": {
                    "state": "available",
                    "stock_basic_record_id": stock_id,
                }
            }
            for stock_id in (1, 2, 3)
        ],
        "research_case": {"id": str(case_a)},
        "industry_map": {
            "id": str(map_a),
            "revision_id": str(map_revision_a),
        },
    }

    with pytest.raises(IndustryThesisOwnerAcceptanceError) as raised:
        acceptance_api._require_single_exact_owner_context(
            graph,
            view,
            as_of_cutoff=date(2026, 7, 9),
            as_of_recorded_at_utc=BOUNDARY,
        )

    assert raised.value.code == "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED"


def test_preview_and_commit_bind_every_acceptance_view_snapshot_field_without_writes() -> None:
    fixture = build_golden_fixture()
    try:
        with api_client(fixture.database) as client:
            view = _view(client, fixture.reviewed)
            before = owner_counts(fixture.database.factory)
            mismatches = {
                "research_case_id": str(uuid4()),
                "industry_map_id": str(uuid4()),
                "industry_map_revision_id": str(uuid4()),
                "map_mode": "different_exact_map_mode",
                "information_cutoff_date": (CUTOFF - timedelta(days=1)).isoformat(),
                "reviewed_plan_fingerprint_sha256": "f" * 64,
                "expected_session_latest_revision_number": (
                    view["expected_session_latest_revision_number"] + 1
                ),
                "owner_acceptance_plan_version": (
                    "aquantai.industry-thesis-owner-acceptance-plan.v2"
                ),
            }

            for endpoint in ("preview", "commit"):
                for field, replacement in mismatches.items():
                    body = {**golden_plan(view), field: replacement}
                    if endpoint == "commit":
                        body["preview_fingerprint_sha256"] = "b" * 64
                    response = client.post(
                        f"/industry-analysis/api/session-revisions/"
                        f"{fixture.reviewed.reviewed_session_revision_id}/"
                        f"owner-acceptance/{endpoint}",
                        params=query_params(fixture.reviewed),
                        json=body,
                    )
                    assert response.status_code == 409, (endpoint, field, response.text)
                    assert response.json()["detail"]["code"] == (
                        "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE"
                    )
                    assert owner_counts(fixture.database.factory) == before
    finally:
        fixture.database.engine.dispose()


def test_exact_pool_reuse_rejects_missing_and_extra_members() -> None:
    candidate_a, candidate_b = uuid4(), uuid4()
    beneficiary_a, beneficiary_b = uuid4(), uuid4()
    revision_a, revision_b = uuid4(), uuid4()
    pool_id, pool_revision_id = uuid4(), uuid4()

    bindings = [
        _reuse_binding(
            candidate_id=candidate_a,
            beneficiary_id=beneficiary_a,
            beneficiary_revision_id=revision_a,
            stock_basic_record_id=1,
            sequence=0,
        ),
        _reuse_binding(
            candidate_id=candidate_b,
            beneficiary_id=beneficiary_b,
            beneficiary_revision_id=revision_b,
            stock_basic_record_id=2,
            sequence=1,
        ),
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
    operation = {
        "mode": "reuse_exact_supported_handoff",
        "candidate_pool_id": str(pool_id),
        "candidate_pool_revision_id": str(pool_revision_id),
    }
    payload = _plan_request(bindings=bindings, pool_operation=operation)
    acceptance_api._validate_reuse_pool_selection(payload, view)

    for incompatible_members in (
        [str(revision_a)],
        [str(revision_a), str(revision_b), str(uuid4())],
    ):
        incompatible_view = deepcopy(view)
        incompatible_view["candidate_pool_operation_contract"]["reuse_options"][0][
            "beneficiary_revision_ids"
        ] = incompatible_members
        with pytest.raises(IndustryThesisOwnerAcceptanceError) as raised:
            acceptance_api._validate_reuse_pool_selection(payload, incompatible_view)
        assert raised.value.code == (
            "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH"
        )


def test_exact_pool_reuse_allows_only_non_supported_create_or_append() -> None:
    candidate_reuse, candidate_changed = uuid4(), uuid4()
    beneficiary_reuse, revision_reuse = uuid4(), uuid4()
    pool_id, pool_revision_id = uuid4(), uuid4()
    view = {
        "members": [
            {
                "reviewed_candidate_revision_id": str(candidate_reuse),
                "stage1_reuse_options": [
                    {
                        "beneficiary_id": str(beneficiary_reuse),
                        "beneficiary_revision_id": str(revision_reuse),
                        "stock_basic_record_id": 1,
                        "assessment_status": "supported",
                    }
                ],
            },
            {
                "reviewed_candidate_revision_id": str(candidate_changed),
                "stage1_reuse_options": [],
            },
        ],
        "candidate_pool_operation_contract": {
            "reuse_options": [
                {
                    "candidate_pool_id": str(pool_id),
                    "candidate_pool_revision_id": str(pool_revision_id),
                    "beneficiary_revision_ids": [str(revision_reuse)],
                }
            ]
        },
    }
    operation = {
        "mode": "reuse_exact_supported_handoff",
        "candidate_pool_id": str(pool_id),
        "candidate_pool_revision_id": str(pool_revision_id),
    }
    reused = _reuse_binding(
        candidate_id=candidate_reuse,
        beneficiary_id=beneficiary_reuse,
        beneficiary_revision_id=revision_reuse,
        stock_basic_record_id=1,
        sequence=0,
    )

    for stage1_operation in (
        "create_beneficiary_identity_and_revision",
        "append_beneficiary_revision",
    ):
        changed = {
            "reviewed_candidate_revision_id": str(candidate_changed),
            "sequence": 1,
            "stage1_operation": stage1_operation,
            "stage1": {
                "assessment_status": "draft",
                "stock_basic_record_id": 2,
            },
            "semantic_operation": "none",
            "semantic": None,
            "readiness_note": "非 supported 成员不进入复用池。",
        }
        payload = _plan_request(
            bindings=[reused, changed],
            pool_operation=operation,
        )
        acceptance_api._validate_reuse_pool_selection(payload, view)

        changed["stage1"] = {
            **changed["stage1"],
            "assessment_status": "supported",
        }
        payload = _plan_request(
            bindings=[reused, changed],
            pool_operation=operation,
        )
        with pytest.raises(IndustryThesisOwnerAcceptanceError) as raised:
            acceptance_api._validate_reuse_pool_selection(payload, view)
        assert raised.value.code == (
            "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH"
        )

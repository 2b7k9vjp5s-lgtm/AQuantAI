"""Zero-network Industry Research ordinary-user end-to-end contract demo."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import timedelta
from urllib.parse import urlencode
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

import backend.api.industry_analysis as industry_api
import backend.api.industry_analysis_acceptance as acceptance_api
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
from industry_alpha.industry_research_e2e_rules import (
    ACCEPTANCE_VIEW_SNAPSHOT_CONTRACT_VERSION,
    SNAPSHOT_BODY_MISMATCH_CODE,
)
from industry_alpha.industry_thesis_models import (
    IndustryThesisOutputLinkRevision,
    IndustryThesisSessionRevision,
)
from industry_alpha.stage1_fixtures import build_stage1_beneficiary_fixture
from industry_alpha.stage1_models import Stage1CandidatePoolRevision
from tests import test_industry_thesis_owner_acceptance as owner_fixture


def _counts(factory) -> tuple[int, int, int]:
    with factory() as session:
        return (
            session.scalar(select(func.count()).select_from(IndustryThesisSessionRevision)),
            session.scalar(select(func.count()).select_from(IndustryThesisOutputLinkRevision)),
            session.scalar(select(func.count()).select_from(Stage1CandidatePoolRevision)),
        )


def _payload(view: dict) -> dict:
    bindings = []
    supported = False
    for member in view["members"]:
        option = max(
            member["stage1_reuse_options"],
            key=lambda item: item["revision_number"],
        )
        supported = supported or option["assessment_status"] == "supported"
        bindings.append(
            {
                "reviewed_candidate_revision_id": member[
                    "reviewed_candidate_revision_id"
                ],
                "sequence": member["sequence"],
                "stage1_operation": "reuse_exact_beneficiary_revision",
                "stage1": {
                    "beneficiary_id": option["beneficiary_id"],
                    "beneficiary_revision_id": option["beneficiary_revision_id"],
                    "stock_basic_record_id": option["stock_basic_record_id"],
                },
                "semantic_operation": "none",
                "semantic": None,
                "readiness_note": "离线 demo 明确复用精确 Stage 1 版本。",
            }
        )
    if supported:
        create = view["candidate_pool_operation_contract"]["create_contract"]
        pool = {
            "mode": "create_supported_handoff",
            "pool_key": create["pool_key"],
            "title": create["title_default"],
            "scope": create["scope_default"],
        }
    else:
        pool = {"mode": "none_no_supported_members"}
    return {
        "reviewed_session_revision_id": view["reviewed_session_revision_id"],
        "expected_session_latest_revision_number": view[
            "expected_session_latest_revision_number"
        ],
        "reviewed_plan_fingerprint_sha256": view[
            "reviewed_plan_fingerprint_sha256"
        ],
        "research_case_id": view["owner_context"]["research_case_id"],
        "map_mode": view["owner_context"]["map_mode"],
        "industry_map_id": view["owner_context"]["industry_map_id"],
        "industry_map_revision_id": view["owner_context"][
            "industry_map_revision_id"
        ],
        "candidate_owner_bindings": bindings,
        "candidate_pool_operation": pool,
        "output_title": view["output_metadata_defaults"]["output_title"],
        "output_scope": view["output_metadata_defaults"]["output_scope"],
        "information_cutoff_date": view["information_cutoff_date"],
        "revision_note": "离线 demo 确认精确研究归属并接受完整成果。",
        "owner_acceptance_plan_version": view[
            "owner_acceptance_plan_version"
        ],
        "acceptance_view_snapshot_contract_version": view[
            "acceptance_view_snapshot_contract_version"
        ],
        "acceptance_view_snapshot_content_sha256": view[
            "acceptance_view_snapshot_content_sha256"
        ],
    }


def run_demo() -> dict:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    app.dependency_overrides[
        acceptance_api.get_industry_analysis_session_factory
    ] = lambda: factory
    app.dependency_overrides[
        acceptance_api.get_industry_analysis_write_factory
    ] = lambda: factory
    original_get_view = (
        acceptance_api.IndustryThesisOwnerAcceptanceWorkbenchQueryService
        .get_acceptance_view
    )
    try:
        fixture = build_stage1_beneficiary_fixture(factory)
        review, *_ = owner_fixture._build_reviewed(
            factory,
            beneficiary_ids=(
                fixture.direct_beneficiary_id,
                fixture.secondary_beneficiary_id,
                fixture.draft_beneficiary_id,
            ),
        )
        client = TestClient(app)
        session_id = review["acceptance_plan"]["session_id"]
        reviewed_id = review["reviewed_session_revision_id"]
        boundary = owner_fixture.BASE_TIME + timedelta(seconds=3)
        query = urlencode(
            {
                "session_id": session_id,
                "as_of_cutoff": owner_fixture.CUTOFF.isoformat(),
                "as_of_recorded_at_utc": boundary.isoformat(),
            }
        )
        view_url = (
            f"/industry-analysis/api/session-revisions/{reviewed_id}/"
            f"owner-acceptance-view?{query}"
        )
        first = client.get(view_url)
        second = client.get(view_url)
        assert first.status_code == second.status_code == 200
        view = first.json()
        assert len(view["members"]) == 3
        assert view["acceptance_view_snapshot_contract_version"] == (
            ACCEPTANCE_VIEW_SNAPSHOT_CONTRACT_VERSION
        )
        assert view["acceptance_view_snapshot_content_sha256"] == second.json()[
            "acceptance_view_snapshot_content_sha256"
        ]
        payload = _payload(view)
        counts_before = _counts(factory)
        preview_url = (
            f"/industry-analysis/api/session-revisions/{reviewed_id}/"
            f"owner-acceptance/preview?{query}"
        )
        preview = client.post(preview_url, json=payload)
        assert preview.status_code == 200, preview.text
        assert preview.json()["commit_ready"] is True
        assert _counts(factory) == counts_before

        def replaced(self, *args, **kwargs):
            changed = deepcopy(original_get_view(self, *args, **kwargs))
            changed["members"].reverse()
            return changed

        acceptance_api.IndustryThesisOwnerAcceptanceWorkbenchQueryService.get_acceptance_view = replaced
        rejected = client.post(preview_url, json=payload)
        assert rejected.status_code == 409
        assert rejected.json()["detail"]["code"] == SNAPSHOT_BODY_MISMATCH_CODE
        assert _counts(factory) == counts_before
        acceptance_api.IndustryThesisOwnerAcceptanceWorkbenchQueryService.get_acceptance_view = original_get_view

        preview = client.post(preview_url, json=payload)
        commit = client.post(
            f"/industry-analysis/api/session-revisions/{reviewed_id}/"
            f"owner-acceptance/commit?{query}",
            json={
                **payload,
                "preview_fingerprint_sha256": preview.json()[
                    "preview_fingerprint_sha256"
                ],
            },
        )
        assert commit.status_code == 200, commit.text
        committed = commit.json()
        accepted_revision_id = UUID(committed["accepted_session_revision_id"])
        with factory() as session:
            accepted_revision = session.get(
                IndustryThesisSessionRevision,
                accepted_revision_id,
            )
            assert accepted_revision is not None
            accepted_revision_number = accepted_revision.revision_number

        result_query = urlencode(
            {
                "session_id": session_id,
                "as_of_cutoff": owner_fixture.CUTOFF.isoformat(),
                "as_of_recorded_at_utc": committed["recorded_at_utc"],
            }
        )
        result = client.get(
            f"/industry-analysis/api/session-revisions/"
            f"{committed['accepted_session_revision_id']}/accepted-result-view?"
            f"{result_query}"
        )
        assert result.status_code == 200, result.text
        assert result.json()["complete_member_count"] == 3

        continuation = industry_api._exact_continuation(
            {
                "session_id": session_id,
                "visible_latest_revision_id": committed[
                    "accepted_session_revision_id"
                ],
                "visible_latest_revision_number": accepted_revision_number,
                "information_cutoff_date": owner_fixture.CUTOFF.isoformat(),
                "recorded_at_utc": committed["recorded_at_utc"],
                "workflow_state": "accepted_outputs_linked",
            }
        )
        assert continuation["kind"] == "accepted_result"
        assert committed["accepted_session_revision_id"] in continuation["path"]
        return {
            "snapshot_contract_version": view[
                "acceptance_view_snapshot_contract_version"
            ],
            "stable_snapshot_sha256": view[
                "acceptance_view_snapshot_content_sha256"
            ],
            "complete_member_count": result.json()["complete_member_count"],
            "supported_handoff_count": result.json()["supported_handoff_count"],
            "body_replacement_rejected": True,
            "preview_zero_write": True,
            "accepted_history_continuation": continuation,
            "external_network": False,
            "ai_calls": False,
            "provider_values": False,
        }
    finally:
        acceptance_api.IndustryThesisOwnerAcceptanceWorkbenchQueryService.get_acceptance_view = original_get_view
        app.dependency_overrides.clear()
        engine.dispose()


def main() -> None:
    print(json.dumps(run_demo(), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

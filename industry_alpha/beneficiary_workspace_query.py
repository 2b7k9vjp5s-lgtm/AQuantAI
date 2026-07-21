"""Deterministic projection logic for the Industry Beneficiary Workspace."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from industry_alpha.beneficiary_workspace_contracts import (
    IndustryBeneficiaryWorkspaceContract,
    IndustryResearchMapListContract,
)
from industry_alpha.beneficiary_workspace_repository import (
    BeneficiaryOverviewRow,
    IndustryBeneficiaryWorkspaceDataError,
    IndustryBeneficiaryWorkspaceRepository,
    MapSelectorRow,
)
from industry_alpha.stage2_query_values import date_text, timestamp_text, uuid_text

WORKSPACE_NOTICES: dict[str, Any] = {
    "read_only": True,
    "research_only": True,
    "not_investment_advice": True,
    "complete_set_meaning": (
        "The company table is the complete cutoff-visible persisted Stage 1 set "
        "for the explicitly selected map, not an exhaustive market-wide universe."
    ),
    "classification_boundary": (
        "direct / secondary / potential are existing Stage 1 analytical research "
        "states. They are not scores, ranks, recommendations, or the later roadmap taxonomy."
    ),
    "stage2_boundary": (
        "Stage 2 research is linked only through exact persisted beneficiary identity "
        "and frozen revision foreign keys. Historical revision differences remain visible."
    ),
    "unsupported_fields": [
        "final direct / conditional / indirect / conceptual taxonomy",
        "rule version or analyst owner",
        "typed customer, certification, capacity, production, or order stage",
        "valuation, expected return, score, ranking, recommendation, or signal",
    ],
    "no_hidden_network_requests": True,
}


class IndustryBeneficiaryWorkspaceQueryService:
    def __init__(
        self,
        repository: IndustryBeneficiaryWorkspaceRepository,
        map_query_service: Any,
    ) -> None:
        self._repository = repository
        self._map_query_service = map_query_service

    def list_maps(
        self, *, as_of_cutoff: date | None = None
    ) -> IndustryResearchMapListContract:
        rows = self._repository.list_map_selectors(as_of_cutoff=as_of_cutoff)
        return IndustryResearchMapListContract(
            as_of_cutoff=date_text(as_of_cutoff),
            maps=tuple(_map_payload(row) for row in rows),
            notices=dict(WORKSPACE_NOTICES),
        )

    def get_workspace(
        self, map_id: UUID, *, as_of_cutoff: date | None = None
    ) -> IndustryBeneficiaryWorkspaceContract:
        map_contract = self._map_query_service.get_map(
            map_id, as_of_cutoff=as_of_cutoff
        )
        map_payload = map_contract.to_dict()
        revision_history = map_payload.get("revision_history")
        if not isinstance(revision_history, (list, tuple)) or not revision_history:
            raise IndustryBeneficiaryWorkspaceDataError(
                "accepted map detail returned no visible revision history"
            )
        visible_map_revision_ids = {
            UUID(str(item["revision_id"])) for item in revision_history
        }
        rows = self._repository.list_beneficiaries(
            map_id,
            as_of_cutoff=as_of_cutoff,
            visible_map_revision_ids=visible_map_revision_ids,
        )
        return IndustryBeneficiaryWorkspaceContract(
            as_of_cutoff=date_text(as_of_cutoff),
            industry_map=dict(map_payload["industry_map"]),
            latest_revision=dict(map_payload["latest_revision"]),
            frozen_snapshot=dict(map_payload["frozen_snapshot"]),
            map_evidence_summary={
                "evidence_grade_summary": dict(
                    map_payload.get("evidence_grade_summary", {})
                ),
                "conflicts": tuple(map_payload.get("conflicts", ())),
                "missing_evidence": tuple(
                    map_payload.get("missing_evidence", ())
                ),
            },
            beneficiaries=tuple(_beneficiary_payload(row) for row in rows),
            detail_routes={
                "beneficiary": "/industry-alpha/beneficiaries/{beneficiary_id}",
                "company_research": (
                    "/industry-alpha/company-research/{company_research_id}"
                ),
            },
            notices=dict(WORKSPACE_NOTICES),
        )


def _map_payload(row: MapSelectorRow) -> dict[str, Any]:
    return {
        "map_id": str(row.map_id),
        "case_id": str(row.case_id),
        "map_key": row.map_key,
        "created_at_utc": timestamp_text(row.created_at_utc),
        "latest_revision": {
            "revision_id": str(row.revision_id),
            "revision_no": row.revision_no,
            "title": row.title,
            "scope": row.scope,
            "information_cutoff_date": date_text(
                row.information_cutoff_date
            ),
            "recorded_at_utc": timestamp_text(row.recorded_at_utc),
            "supersedes_revision_id": uuid_text(
                row.supersedes_revision_id
            ),
        },
    }


def _beneficiary_payload(row: BeneficiaryOverviewRow) -> dict[str, Any]:
    stage2 = None
    if row.company_research_id is not None:
        historical_mismatch = (
            row.stage2_frozen_beneficiary_revision_id != row.revision_id
        )
        stage2 = {
            "company_research_id": str(row.company_research_id),
            "frozen_beneficiary_revision_id": str(
                row.stage2_frozen_beneficiary_revision_id
            ),
            "current_overview_beneficiary_revision_id": str(row.revision_id),
            "historical_revision_mismatch": historical_mismatch,
            "history_notice": (
                "该公司研究冻结于较早的 Stage 1 修订，未自动重绑到当前修订。"
                if historical_mismatch
                else "该公司研究与当前显示的 Stage 1 修订一致。"
            ),
            "selected_map_revision_id": str(
                row.stage2_selected_map_revision_id
            ),
            "stock_basic_record_id": row.stage2_stock_basic_record_id,
            "latest_revision": {
                "revision_id": str(row.company_research_revision_id),
                "revision_no": row.company_research_revision_no,
                "workflow_state": row.company_research_workflow_state,
                "conclusion_status": (
                    row.company_research_conclusion_status
                ),
                "research_question": row.company_research_question,
                "summary": row.company_research_summary,
                "information_cutoff_date": date_text(
                    row.company_research_information_cutoff_date
                ),
                "recorded_at_utc": timestamp_text(
                    row.company_research_recorded_at_utc
                ),
                "supersedes_revision_id": uuid_text(
                    row.company_research_supersedes_revision_id
                ),
            },
            "detail_path": (
                f"/industry-alpha/company-research/{row.company_research_id}"
            ),
        }
    return {
        "beneficiary_id": str(row.beneficiary_id),
        "case_id": str(row.case_id),
        "map_id": str(row.map_id),
        "source": row.source,
        "stock_code": row.stock_code,
        "created_at_utc": timestamp_text(row.created_at_utc),
        "stock": {
            "stock_basic_record_id": row.stock_basic_record_id,
            "stock_name": row.stock_name,
            "exchange": row.exchange,
            "provider_industry": row.provider_industry,
            "listing_date": date_text(row.listing_date),
            "status": row.stock_status,
            "source": row.source,
            "ingestion_run": {
                "ingestion_run_id": row.ingestion_run_id,
                "series_key": row.ingestion_series_key,
                "provider": row.ingestion_provider,
                "information_cutoff_date": date_text(
                    row.ingestion_information_cutoff_date
                ),
                "completed_at_utc": timestamp_text(
                    row.ingestion_completed_at_utc
                ),
            },
        },
        "latest_revision": {
            "revision_id": str(row.revision_id),
            "revision_no": row.revision_no,
            "selected_map_revision_id": str(
                row.selected_map_revision_id
            ),
            "beneficiary_kind": row.beneficiary_kind,
            "assessment_status": row.assessment_status,
            "rationale_summary": row.rationale_summary,
            "information_cutoff_date": date_text(
                row.information_cutoff_date
            ),
            "recorded_at_utc": timestamp_text(row.recorded_at_utc),
            "supersedes_revision_id": uuid_text(
                row.supersedes_revision_id
            ),
        },
        "company_research": stage2,
        "beneficiary_detail_path": (
            f"/industry-alpha/beneficiaries/{row.beneficiary_id}"
        ),
    }

"""Read-only assembly of accepted research and one exact candidate overlay."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from industry_alpha.industry_research_result_accepted import (
    AcceptedResultProjectionReader,
)
from industry_alpha.industry_research_result_candidate import CandidateOverlayReader
from industry_alpha.industry_research_result_company import ExplainedCompanyProjectionReader
from industry_alpha.industry_research_result_map import ExactIndustryMapRevisionReader
from industry_alpha.industry_research_result_rules import (
    DEFAULT_OPTION_LIMIT,
    EXPLAINED_RESULT_CONTRACT_VERSION,
    MAX_OPTION_LIMIT,
    RESULT_CONTRACT_VERSION,
    IndustryResearchResultError,
    conclusion_cards,
    explained_result_fingerprint,
    recorded_boundary,
)


class IndustryResearchResultQueryService:
    """Compose accepted history with an explicitly selected optional snapshot."""

    def __init__(self, session: Session) -> None:
        self._accepted = AcceptedResultProjectionReader(session)
        self._map = ExactIndustryMapRevisionReader(session)
        self._candidate = CandidateOverlayReader(session)
        self._company = ExplainedCompanyProjectionReader(session)

    def get_assembled_result(
        self,
        output_link_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
        investment_candidate_snapshot_revision_id: UUID | None = None,
        option_limit: int = DEFAULT_OPTION_LIMIT,
    ) -> dict[str, Any]:
        boundary = recorded_boundary(as_of_recorded_at_utc)
        if as_of_cutoff > boundary.date():
            raise IndustryResearchResultError(
                "industry_research_result_boundary_invalid",
                "as_of_cutoff cannot be later than as_of_recorded_at_utc",
            )
        if option_limit < 1 or option_limit > MAX_OPTION_LIMIT:
            raise IndustryResearchResultError(
                "industry_research_result_option_limit_invalid",
                f"option_limit must be between 1 and {MAX_OPTION_LIMIT}",
            )
        output, accepted, readiness = self._accepted.read(
            output_link_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=boundary,
        )
        exact_map = self._map.read(
            UUID(output["industry_map_revision_id"]),
            expected_map_id=UUID(output["industry_map_id"]),
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=boundary,
        )
        readiness_by_revision = {
            item["beneficiary_revision_id"]: item for item in readiness["items"]
        }
        members = []
        for member in accepted["members"]:
            item = dict(member)
            item["readiness"] = readiness_by_revision[
                item["beneficiary_revision_id"]
            ]
            item["candidate_overlay"] = None
            item["explained_research"] = None
            members.append(item)

        pool_revision_text = output["accepted_candidate_pool_revision_id"]
        option_result = {"options": [], "has_more": False}
        if pool_revision_text is not None:
            option_result = self._candidate.list_options(
                UUID(pool_revision_text),
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=boundary,
                limit=option_limit,
            )
        overlay = self._candidate.resolve(
            accepted_pool_revision_id=(
                None if pool_revision_text is None else UUID(pool_revision_text)
            ),
            accepted_beneficiary_revision_ids={
                UUID(item["beneficiary_revision_id"]) for item in members
            },
            selected_snapshot_revision_id=(
                investment_candidate_snapshot_revision_id
            ),
            options=option_result["options"],
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=boundary,
        )
        if overlay.get("snapshot") is not None:
            by_revision = {
                item["beneficiary_revision_id"]: item
                for item in overlay["snapshot"]["members"]
            }
            for member in members:
                member["candidate_overlay"] = by_revision.get(
                    member["beneficiary_revision_id"]
                )

        explained = self._company.explain(
            members,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=boundary,
        )
        explained_by_revision = {
            item["beneficiary_revision_id"]: item for item in explained["members"]
        }
        for member in members:
            member["explained_research"] = explained_by_revision[
                member["beneficiary_revision_id"]
            ]

        supported = [
            item for item in members if item["included_in_supported_handoff"]
        ]
        cards, largest_gap = conclusion_cards(
            members,
            supported,
            exact_map=exact_map,
            overlay=overlay,
        )
        explained_fingerprint = explained_result_fingerprint(explained)
        return {
            "result_contract_version": RESULT_CONTRACT_VERSION,
            "explained_result": {
                "contract_version": EXPLAINED_RESULT_CONTRACT_VERSION,
                "content_sha256": explained_fingerprint,
                "creates_owner_state": explained["creates_owner_state"],
                "recomputes_candidate": explained["recomputes_candidate"],
                "uses_latest_fallback": explained["uses_latest_fallback"],
                "external_network": explained["external_network"],
            },
            "accepted_snapshot": {
                "output_link_revision_id": output["output_link_revision_id"],
                "reviewed_session_revision_id": output[
                    "reviewed_session_revision_id"
                ],
                "accepted_session_revision_id": output[
                    "accepted_session_revision_id"
                ],
                "research_case_id": output["research_case_id"],
                "industry_map_id": output["industry_map_id"],
                "industry_map_revision_id": output["industry_map_revision_id"],
                "accepted_candidate_pool_revision_id": pool_revision_text,
                "title": accepted["title"],
                "complete_member_count": len(members),
                "supported_handoff_count": len(supported),
                "members": members,
                "supported_handoff_members": supported,
                "coverage_notice": accepted["coverage_notice"],
                "information_cutoff_date": output["information_cutoff_date"],
                "recorded_at_utc": output["recorded_at_utc"],
                "technical_details": output,
            },
            "industry_map": exact_map,
            "candidate_snapshot_options": {
                "options": option_result["options"],
                "limit": option_limit,
                "has_more": option_result["has_more"],
                "auto_selected": False,
            },
            "candidate_overlay": overlay,
            "conclusion_cards": cards,
            "largest_missing_prerequisite": largest_gap,
            "coverage_notice": accepted["coverage_notice"],
            "writes_performed": False,
        }


__all__ = (
    "DEFAULT_OPTION_LIMIT",
    "MAX_OPTION_LIMIT",
    "IndustryResearchResultError",
    "IndustryResearchResultQueryService",
)

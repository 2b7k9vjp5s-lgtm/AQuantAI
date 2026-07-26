"""Bounded projections over the accepted Industry Thesis output owner."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticProfile,
    Stage1BeneficiarySemanticProfileRevision,
)
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateRevision,
    IndustryThesisOutputLinkRevision,
)
from industry_alpha.industry_thesis_owner_acceptance_query import (
    IndustryThesisAcceptedOutputQueryService,
)
from industry_alpha.industry_thesis_rules import json_value
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryRevision,
)
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
)
from industry_alpha.industry_research_result_rules import (
    IndustryResearchResultError,
)


class AcceptedResultProjectionReader:
    """Reuse owner validation while keeping member reads query-bounded."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._owner = IndustryThesisAcceptedOutputQueryService(session)

    def read(
        self,
        output_link_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        prefetched = self._prefetch(output_link_revision_id)
        output = self._owner.get_output(
            output_link_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=as_of_recorded_at_utc,
        )
        result = self._owner.get_result(
            output_link_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=as_of_recorded_at_utc,
        )
        readiness = self._batch_readiness(
            output,
            result,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=as_of_recorded_at_utc,
        )
        del prefetched
        return output, result, readiness

    def _prefetch(self, output_link_revision_id: UUID) -> list[Any]:
        output = self._session.get(
            IndustryThesisOutputLinkRevision,
            output_link_revision_id,
        )
        if output is None:
            return []
        bindings = json_value(
            output.ordered_owner_output_bindings_json,
            "ordered owner output bindings",
        )
        if not isinstance(bindings, list):
            return [output]
        try:
            groups = (
                (
                    IndustryThesisCandidateRevision,
                    [UUID(item["reviewed_candidate_revision_id"]) for item in bindings],
                ),
                (
                    Stage1Beneficiary,
                    [UUID(item["beneficiary_id"]) for item in bindings],
                ),
                (
                    Stage1BeneficiaryRevision,
                    [UUID(item["beneficiary_revision_id"]) for item in bindings],
                ),
                (
                    Stage1BeneficiarySemanticProfile,
                    [
                        UUID(item["semantic_profile_id"])
                        for item in bindings
                        if item.get("semantic_profile_id") is not None
                    ],
                ),
                (
                    Stage1BeneficiarySemanticProfileRevision,
                    [
                        UUID(item["semantic_profile_revision_id"])
                        for item in bindings
                        if item.get("semantic_profile_revision_id") is not None
                    ],
                ),
            )
        except (KeyError, TypeError, ValueError, AttributeError):
            return [output]
        rows: list[Any] = [output]
        for model, ids in groups:
            if ids:
                rows.extend(
                    self._session.scalars(select(model).where(model.id.in_(ids)))
                )
        return rows

    def _batch_readiness(
        self,
        output: dict[str, Any],
        result: dict[str, Any],
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        pool_revision_text = output["accepted_candidate_pool_revision_id"]
        revision_ids = [
            UUID(item["beneficiary_revision_id"]) for item in result["members"]
        ]
        research_rows = (
            list(
                self._session.scalars(
                    select(Stage2CompanyResearch).where(
                        Stage2CompanyResearch.candidate_pool_revision_id
                        == UUID(pool_revision_text),
                        Stage2CompanyResearch.beneficiary_revision_id.in_(
                            revision_ids
                        ),
                        Stage2CompanyResearch.created_at_utc
                        <= as_of_recorded_at_utc,
                    )
                )
            )
            if pool_revision_text is not None
            else []
        )
        research_by_beneficiary: dict[UUID, Stage2CompanyResearch] = {}
        for research in research_rows:
            if research.beneficiary_revision_id in research_by_beneficiary:
                raise IndustryResearchResultError(
                    "industry_research_result_readiness_graph_incomplete",
                    "more than one Company Research identity binds one exact member",
                )
            research_by_beneficiary[research.beneficiary_revision_id] = research
        research_ids = [item.id for item in research_rows]
        visible_revisions = (
            list(
                self._session.scalars(
                    select(Stage2CompanyResearchRevision)
                    .where(
                        Stage2CompanyResearchRevision.company_research_id.in_(
                            research_ids
                        ),
                        Stage2CompanyResearchRevision.information_cutoff_date
                        <= as_of_cutoff,
                        Stage2CompanyResearchRevision.recorded_at_utc
                        <= as_of_recorded_at_utc,
                    )
                    .order_by(
                        Stage2CompanyResearchRevision.company_research_id,
                        Stage2CompanyResearchRevision.revision_no.desc(),
                    )
                )
            )
            if research_ids
            else []
        )
        latest_by_research: dict[UUID, Stage2CompanyResearchRevision] = {}
        for revision in visible_revisions:
            latest_by_research.setdefault(revision.company_research_id, revision)

        items = []
        for member in result["members"]:
            revision_id = UUID(member["beneficiary_revision_id"])
            reasons = list(member["readiness_reason_codes"])
            semantic_revision_id = member["semantic_profile_revision_id"]
            if semantic_revision_id is None:
                semantic_state = {
                    "state": "missing",
                    "profile_id": None,
                    "profile_revision_id": None,
                }
                reasons.append("typed_semantics_missing")
            else:
                semantic_state = {
                    "state": member["semantic_overall_status"],
                    "profile_id": member["semantic_profile_id"],
                    "profile_revision_id": semantic_revision_id,
                }
            research = research_by_beneficiary.get(revision_id)
            research_revision = (
                None if research is None else latest_by_research.get(research.id)
            )
            if research is None:
                company_state = {
                    "state": "missing",
                    "company_research_id": None,
                    "company_research_revision_id": None,
                    "reason": (
                        "no_supported_handoff_pool"
                        if pool_revision_text is None
                        else "exact_company_research_not_found"
                    ),
                }
            elif research_revision is None:
                company_state = {
                    "state": "missing",
                    "company_research_id": str(research.id),
                    "company_research_revision_id": None,
                    "reason": "no_visible_company_research_revision",
                }
            else:
                company_state = {
                    "state": research_revision.conclusion_status,
                    "company_research_id": str(research.id),
                    "company_research_revision_id": str(research_revision.id),
                    "workflow_state": research_revision.workflow_state,
                    "reason": None,
                }
            if company_state["state"] == "missing":
                reasons.append("company_research_missing")
            reasons.extend(
                (
                    "investment_candidate_not_created_by_acceptance",
                    "canonical_price_not_evaluated_by_acceptance",
                    "structured_valuation_not_evaluated_by_acceptance",
                )
            )
            items.append(
                {
                    "sequence": member["sequence"],
                    "beneficiary_id": member["beneficiary_id"],
                    "beneficiary_revision_id": member[
                        "beneficiary_revision_id"
                    ],
                    "assessment_status": member["assessment_status"],
                    "included_in_supported_handoff": member[
                        "included_in_supported_handoff"
                    ],
                    "typed_semantics": semantic_state,
                    "company_research": company_state,
                    "investment_candidate": {
                        "state": "not_created_by_owner_acceptance",
                        "snapshot_id": None,
                    },
                    "canonical_price_and_eligibility": {
                        "state": "not_evaluated_by_owner_acceptance"
                    },
                    "structured_financial_and_valuation": {
                        "state": "not_evaluated_by_owner_acceptance"
                    },
                    "reason_codes": sorted(set(reasons)),
                    "ready_for_later_explicit_handoff": (
                        member["included_in_supported_handoff"]
                        and semantic_revision_id is not None
                        and company_state["state"] != "missing"
                    ),
                }
            )
        return {
            "output_link_revision_id": output["output_link_revision_id"],
            "items": items,
            "creates_owner_state": False,
            "computes_score": False,
            "information_cutoff_date": as_of_cutoff.isoformat(),
            "recorded_at_utc": as_of_recorded_at_utc.isoformat(),
        }

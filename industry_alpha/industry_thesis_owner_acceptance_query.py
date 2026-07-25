"""Exact-ID reads for accepted Industry Thesis owner outputs."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticProfile,
    Stage1BeneficiarySemanticProfileRevision,
)
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateRevision,
    IndustryThesisOutputLinkIdentity,
    IndustryThesisOutputLinkRevision,
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    OUTPUT_CONTRACT_VERSION,
    IndustryThesisOwnerAcceptanceError,
)
from industry_alpha.industry_thesis_rules import json_value, stored_utc
from industry_alpha.models import ResearchCase
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
)


def _recorded_boundary(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_CHRONOLOGY_INVALID",
            "as_of_recorded_at_utc must be explicit UTC",
        )
    return value.astimezone(timezone.utc)


def _visible(
    cutoff: date,
    recorded_at: datetime,
    *,
    as_of_cutoff: date,
    as_of_recorded_at_utc: datetime,
) -> bool:
    return cutoff <= as_of_cutoff and stored_utc(recorded_at) <= as_of_recorded_at_utc


class IndustryThesisAcceptedOutputQueryService:
    """Verify and render one exact accepted output graph."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_output(
        self,
        output_link_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        graph = self._load_graph(
            output_link_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=as_of_recorded_at_utc,
        )
        output = graph["output"]
        return {
            "output_contract_version": output.output_contract_version,
            "output_link_id": str(output.output_link_id),
            "output_link_revision_id": str(output.id),
            "output_revision_number": output.revision_number,
            "reviewed_session_revision_id": str(output.reviewed_session_revision_id),
            "accepted_session_revision_id": str(output.accepted_session_revision_id),
            "research_case_id": str(output.research_case_id),
            "industry_map_id": str(output.accepted_industry_map_identity_id),
            "industry_map_revision_id": str(output.accepted_industry_map_revision_id),
            "accepted_candidate_pool_revision_id": (
                None
                if output.accepted_candidate_pool_revision_id is None
                else str(output.accepted_candidate_pool_revision_id)
            ),
            "ordered_beneficiary_revision_ids": graph[
                "ordered_beneficiary_revision_ids"
            ],
            "ordered_owner_output_bindings": graph["bindings"],
            "coverage_state": output.coverage_state,
            "reviewed_plan_fingerprint_sha256": output.reviewed_plan_fingerprint_sha256,
            "owner_acceptance_plan_fingerprint_sha256": (
                output.acceptance_plan_fingerprint_sha256
            ),
            "owner_transaction_id": output.owner_transaction_id,
            "information_cutoff_date": output.information_cutoff_date.isoformat(),
            "recorded_at_utc": stored_utc(output.recorded_at_utc).isoformat(),
        }

    def get_result(
        self,
        output_link_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        graph = self._load_graph(
            output_link_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=as_of_recorded_at_utc,
        )
        output = graph["output"]
        members: list[dict[str, Any]] = []
        for binding in graph["bindings"]:
            reviewed = graph["reviewed_candidates"][
                UUID(binding["reviewed_candidate_revision_id"])
            ]
            beneficiary = graph["beneficiaries"][UUID(binding["beneficiary_id"])]
            revision = graph["beneficiary_revisions"][
                UUID(binding["beneficiary_revision_id"])
            ]
            semantic_revision = None
            if binding["semantic_profile_revision_id"] is not None:
                semantic_revision = graph["semantic_revisions"][
                    UUID(binding["semantic_profile_revision_id"])
                ]
            members.append(
                {
                    "sequence": binding["sequence"],
                    "reviewed_candidate_revision_id": str(reviewed.id),
                    "company_label_original": reviewed.company_label_original,
                    "source_kind": reviewed.source_kind,
                    "source_reference": json_value(
                        reviewed.source_reference_json,
                        "reviewed candidate source reference",
                    ),
                    "review_rationale": json_value(
                        reviewed.rationale_json,
                        "reviewed candidate rationale",
                    ),
                    "review_uncertainty": json_value(
                        reviewed.uncertainty_json,
                        "reviewed candidate uncertainty",
                    ),
                    "reviewed_proposal_exposure": reviewed.proposed_exposure_type,
                    "beneficiary_id": str(beneficiary.id),
                    "beneficiary_revision_id": str(revision.id),
                    "source": beneficiary.source,
                    "stock_code": beneficiary.stock_code,
                    "stock_basic_record_id": revision.stock_basic_record_id,
                    "legacy_beneficiary_kind": revision.beneficiary_kind,
                    "assessment_status": revision.assessment_status,
                    "rationale_summary": revision.rationale_summary,
                    "semantic_profile_id": binding["semantic_profile_id"],
                    "semantic_profile_revision_id": (
                        None
                        if semantic_revision is None
                        else str(semantic_revision.id)
                    ),
                    "semantic_overall_status": (
                        None
                        if semantic_revision is None
                        else semantic_revision.overall_status
                    ),
                    "included_in_supported_handoff": binding[
                        "included_in_supported_handoff"
                    ],
                    "supported_handoff_reason": binding[
                        "supported_handoff_reason"
                    ],
                    "readiness_reason_codes": binding["readiness_reason_codes"],
                    "readiness_note": binding["readiness_note"],
                }
            )
        return {
            "output_link_revision_id": str(output.id),
            "title": "本次研究已接受的完整成员",
            "complete_member_count": len(members),
            "supported_handoff_count": sum(
                bool(item["included_in_supported_handoff"]) for item in members
            ),
            "accepted_candidate_pool_revision_id": (
                None
                if output.accepted_candidate_pool_revision_id is None
                else str(output.accepted_candidate_pool_revision_id)
            ),
            "members": members,
            "coverage_notice": (
                "本结果仅表示这次已审核研究中被接受的完整成员，"
                "不代表全市场或整个产业地图的穷尽覆盖。"
            ),
            "ranking_applied": False,
            "information_cutoff_date": output.information_cutoff_date.isoformat(),
            "recorded_at_utc": stored_utc(output.recorded_at_utc).isoformat(),
        }

    def get_readiness(
        self,
        output_link_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        recorded_boundary = _recorded_boundary(as_of_recorded_at_utc)
        graph = self._load_graph(
            output_link_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=recorded_boundary,
        )
        output = graph["output"]
        items: list[dict[str, Any]] = []
        for binding in graph["bindings"]:
            beneficiary_revision_id = UUID(binding["beneficiary_revision_id"])
            semantic_revision_id = binding["semantic_profile_revision_id"]
            reasons = list(binding["readiness_reason_codes"])
            company_research = self._company_research_state(
                beneficiary_revision_id=beneficiary_revision_id,
                candidate_pool_revision_id=output.accepted_candidate_pool_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=recorded_boundary,
            )
            if semantic_revision_id is None:
                semantic_state = {
                    "state": "missing",
                    "profile_id": None,
                    "profile_revision_id": None,
                }
                if "typed_semantics_missing" not in reasons:
                    reasons.append("typed_semantics_missing")
            else:
                semantic = graph["semantic_revisions"][UUID(semantic_revision_id)]
                semantic_state = {
                    "state": semantic.overall_status,
                    "profile_id": binding["semantic_profile_id"],
                    "profile_revision_id": str(semantic.id),
                }
            if company_research["state"] == "missing":
                reasons.append("company_research_missing")
            reasons.extend(
                [
                    "investment_candidate_not_created_by_acceptance",
                    "canonical_price_not_evaluated_by_acceptance",
                    "structured_valuation_not_evaluated_by_acceptance",
                ]
            )
            items.append(
                {
                    "sequence": binding["sequence"],
                    "beneficiary_id": binding["beneficiary_id"],
                    "beneficiary_revision_id": binding["beneficiary_revision_id"],
                    "assessment_status": binding["assessment_status"],
                    "included_in_supported_handoff": binding[
                        "included_in_supported_handoff"
                    ],
                    "typed_semantics": semantic_state,
                    "company_research": company_research,
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
                        binding["included_in_supported_handoff"]
                        and semantic_revision_id is not None
                        and company_research["state"] != "missing"
                    ),
                }
            )
        return {
            "output_link_revision_id": str(output.id),
            "items": items,
            "creates_owner_state": False,
            "computes_score": False,
            "information_cutoff_date": as_of_cutoff.isoformat(),
            "recorded_at_utc": recorded_boundary.isoformat(),
        }

    def _load_graph(
        self,
        output_link_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        recorded_boundary = _recorded_boundary(as_of_recorded_at_utc)
        output = self._session.get(
            IndustryThesisOutputLinkRevision,
            output_link_revision_id,
        )
        if output is None or not _visible(
            output.information_cutoff_date,
            output.recorded_at_utc,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=recorded_boundary,
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "exact output revision was not found or is outside the as-of boundary",
            )
        try:
            UUID(output.owner_transaction_id)
        except (TypeError, ValueError, AttributeError) as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "owner transaction key is not a canonical UUID",
            ) from exc
        if output.output_contract_version != OUTPUT_CONTRACT_VERSION:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "unsupported output contract version",
            )
        identity = self._session.get(
            IndustryThesisOutputLinkIdentity,
            output.output_link_id,
        )
        reviewed = self._session.get(
            IndustryThesisSessionRevision,
            output.reviewed_session_revision_id,
        )
        accepted = self._session.get(
            IndustryThesisSessionRevision,
            output.accepted_session_revision_id,
        )
        session_identity = (
            None
            if accepted is None
            else self._session.get(
                IndustryThesisSessionIdentity,
                accepted.session_id,
            )
        )
        research_case = self._session.get(ResearchCase, output.research_case_id)
        industry_map = self._session.get(
            IndustryMap,
            output.accepted_industry_map_identity_id,
        )
        map_revision = self._session.get(
            IndustryMapRevision,
            output.accepted_industry_map_revision_id,
        )
        if (
            identity is None
            or reviewed is None
            or accepted is None
            or session_identity is None
            or research_case is None
            or industry_map is None
            or map_revision is None
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )
        if (
            output.session_revision_id != accepted.id
            or accepted.workflow_state != "accepted_outputs_linked"
            or reviewed.workflow_state != "reviewed_plan_ready"
            or accepted.supersedes_revision_id != reviewed.id
            or accepted.session_id != reviewed.session_id
            or identity.session_id != reviewed.session_id
            or industry_map.case_id != research_case.id
            or map_revision.map_id != industry_map.id
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )
        for label, cutoff, recorded in (
            (
                "reviewed session",
                reviewed.information_cutoff_date,
                reviewed.recorded_at_utc,
            ),
            (
                "accepted session",
                accepted.information_cutoff_date,
                accepted.recorded_at_utc,
            ),
            (
                "map revision",
                map_revision.information_cutoff_date,
                map_revision.recorded_at_utc,
            ),
        ):
            if not _visible(
                cutoff,
                recorded,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=recorded_boundary,
            ):
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                    f"{label} is outside the exact read boundary",
                )
        accepted_graph = json_value(
            accepted.draft_graph_json,
            "accepted draft graph",
        )
        if (
            not isinstance(accepted_graph, dict)
            or accepted_graph.get("output_link_revision_id") != str(output.id)
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )
        beneficiary_ids = json_value(
            output.ordered_beneficiary_revision_ids_json,
            "ordered beneficiary revision IDs",
        )
        bindings = json_value(
            output.ordered_owner_output_bindings_json,
            "ordered owner output bindings",
        )
        if (
            not isinstance(beneficiary_ids, list)
            or not isinstance(bindings, list)
            or not bindings
            or beneficiary_ids
            != [item.get("beneficiary_revision_id") for item in bindings]
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )

        beneficiaries: dict[UUID, Stage1Beneficiary] = {}
        revisions: dict[UUID, Stage1BeneficiaryRevision] = {}
        reviewed_candidates: dict[UUID, IndustryThesisCandidateRevision] = {}
        semantic_revisions: dict[
            UUID,
            Stage1BeneficiarySemanticProfileRevision,
        ] = {}
        supported_revision_ids: list[UUID] = []
        seen_beneficiary_ids: set[UUID] = set()
        for expected_sequence, binding in enumerate(bindings):
            try:
                reviewed_id = UUID(binding["reviewed_candidate_revision_id"])
                beneficiary_id = UUID(binding["beneficiary_id"])
                beneficiary_revision_id = UUID(binding["beneficiary_revision_id"])
            except (KeyError, TypeError, ValueError) as exc:
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
                ) from exc
            if binding.get("sequence") != expected_sequence:
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                    "owner binding sequence is not dense and deterministic",
                )
            reviewed_candidate = self._session.get(
                IndustryThesisCandidateRevision,
                reviewed_id,
            )
            beneficiary = self._session.get(Stage1Beneficiary, beneficiary_id)
            revision = self._session.get(
                Stage1BeneficiaryRevision,
                beneficiary_revision_id,
            )
            if (
                reviewed_candidate is None
                or beneficiary is None
                or revision is None
                or reviewed_candidate.session_revision_id != reviewed.id
                or reviewed_candidate.review_state != "selected_for_acceptance"
                or revision.beneficiary_id != beneficiary.id
                or beneficiary.case_id != research_case.id
                or beneficiary.map_id != industry_map.id
                or revision.selected_map_revision_id != map_revision.id
                or revision.stock_basic_record_id
                != binding.get("stock_basic_record_id")
                or revision.beneficiary_kind
                != binding.get("legacy_beneficiary_kind")
                or revision.assessment_status != binding.get("assessment_status")
                or revision.assessment_status == "rejected"
                or beneficiary.id in seen_beneficiary_ids
            ):
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
                )
            if not _visible(
                revision.information_cutoff_date,
                revision.recorded_at_utc,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=recorded_boundary,
            ):
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
                )
            included = bool(binding.get("included_in_supported_handoff"))
            if included != (revision.assessment_status == "supported"):
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
                )
            if included:
                supported_revision_ids.append(revision.id)
            seen_beneficiary_ids.add(beneficiary.id)
            reviewed_candidates[reviewed_id] = reviewed_candidate
            beneficiaries[beneficiary.id] = beneficiary
            revisions[revision.id] = revision

            semantic_revision_text = binding.get("semantic_profile_revision_id")
            semantic_profile_text = binding.get("semantic_profile_id")
            if (semantic_revision_text is None) != (semantic_profile_text is None):
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
                )
            if semantic_revision_text is not None:
                semantic_profile_id = UUID(semantic_profile_text)
                semantic_revision_id = UUID(semantic_revision_text)
                profile = self._session.get(
                    Stage1BeneficiarySemanticProfile,
                    semantic_profile_id,
                )
                semantic_revision = self._session.get(
                    Stage1BeneficiarySemanticProfileRevision,
                    semantic_revision_id,
                )
                if (
                    profile is None
                    or semantic_revision is None
                    or semantic_revision.profile_id != profile.id
                    or profile.beneficiary_id != beneficiary.id
                    or semantic_revision.beneficiary_revision_id != revision.id
                    or semantic_revision.selected_map_revision_id != map_revision.id
                    or not _visible(
                        semantic_revision.information_cutoff_date,
                        semantic_revision.recorded_at_utc,
                        as_of_cutoff=as_of_cutoff,
                        as_of_recorded_at_utc=recorded_boundary,
                    )
                ):
                    raise IndustryThesisOwnerAcceptanceError(
                        "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
                    )
                semantic_revisions[semantic_revision.id] = semantic_revision

        pool_revision = None
        if supported_revision_ids:
            if output.accepted_candidate_pool_revision_id is None:
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
                )
            pool_revision = self._session.get(
                Stage1CandidatePoolRevision,
                output.accepted_candidate_pool_revision_id,
            )
            pool = (
                None
                if pool_revision is None
                else self._session.get(
                    Stage1CandidatePool,
                    pool_revision.candidate_pool_id,
                )
            )
            membership_ids = (
                []
                if pool_revision is None
                else list(
                    self._session.scalars(
                        select(
                            Stage1CandidatePoolMembership.beneficiary_revision_id
                        )
                        .where(
                            Stage1CandidatePoolMembership.candidate_pool_revision_id
                            == pool_revision.id
                        )
                        .order_by(
                            Stage1CandidatePoolMembership.beneficiary_revision_id
                        )
                    )
                )
            )
            if (
                pool_revision is None
                or pool is None
                or pool.case_id != research_case.id
                or pool.map_id != industry_map.id
                or pool_revision.selected_map_revision_id != map_revision.id
                or membership_ids != sorted(supported_revision_ids, key=str)
                or not _visible(
                    pool_revision.information_cutoff_date,
                    pool_revision.recorded_at_utc,
                    as_of_cutoff=as_of_cutoff,
                    as_of_recorded_at_utc=recorded_boundary,
                )
            ):
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
                )
        elif output.accepted_candidate_pool_revision_id is not None:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )

        return {
            "output": output,
            "identity": identity,
            "reviewed": reviewed,
            "accepted": accepted,
            "research_case": research_case,
            "industry_map": industry_map,
            "map_revision": map_revision,
            "ordered_beneficiary_revision_ids": beneficiary_ids,
            "bindings": bindings,
            "reviewed_candidates": reviewed_candidates,
            "beneficiaries": beneficiaries,
            "beneficiary_revisions": revisions,
            "semantic_revisions": semantic_revisions,
            "candidate_pool_revision": pool_revision,
        }

    def _company_research_state(
        self,
        *,
        beneficiary_revision_id: UUID,
        candidate_pool_revision_id: UUID | None,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        if candidate_pool_revision_id is None:
            return {
                "state": "missing",
                "company_research_id": None,
                "company_research_revision_id": None,
                "reason": "no_supported_handoff_pool",
            }
        research = self._session.scalar(
            select(Stage2CompanyResearch).where(
                Stage2CompanyResearch.candidate_pool_revision_id
                == candidate_pool_revision_id,
                Stage2CompanyResearch.beneficiary_revision_id
                == beneficiary_revision_id,
            )
        )
        if (
            research is None
            or stored_utc(research.created_at_utc) > as_of_recorded_at_utc
        ):
            return {
                "state": "missing",
                "company_research_id": None,
                "company_research_revision_id": None,
                "reason": "exact_company_research_not_found",
            }
        revision = self._session.scalar(
            select(Stage2CompanyResearchRevision)
            .where(
                Stage2CompanyResearchRevision.company_research_id == research.id,
                Stage2CompanyResearchRevision.information_cutoff_date <= as_of_cutoff,
                Stage2CompanyResearchRevision.recorded_at_utc
                <= as_of_recorded_at_utc,
            )
            .order_by(Stage2CompanyResearchRevision.revision_no.desc())
            .limit(1)
        )
        if revision is None:
            return {
                "state": "missing",
                "company_research_id": str(research.id),
                "company_research_revision_id": None,
                "reason": "no_visible_company_research_revision",
            }
        return {
            "state": revision.conclusion_status,
            "company_research_id": str(research.id),
            "company_research_revision_id": str(revision.id),
            "workflow_state": revision.workflow_state,
            "reason": None,
        }

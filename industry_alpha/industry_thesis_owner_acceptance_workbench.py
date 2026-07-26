"""Read-only ordinary-user projection for Owner Context v2 acceptance.

The workbench never chooses an Owner Context.  It consumes the exact context
already frozen in a fingerprint-verified reviewed plan and limits every Stage 1
lookup to that case/map/map-revision tuple.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import StockBasicRecord
from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticProfile,
    Stage1BeneficiarySemanticProfileRevision,
)
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateRevision,
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    MAP_MODE,
    OWNER_ACCEPTANCE_PLAN_VERSION,
    IndustryThesisOwnerAcceptanceError,
)
from industry_alpha.industry_thesis_review import (
    ACCEPTANCE_PLAN_VERSION,
    OWNER_CONTEXT_VERSION,
    IndustryThesisReviewedPlanQueryService,
)
from industry_alpha.industry_thesis_rules import stored_utc
from industry_alpha.models import ResearchCase
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
    Stage1CandidatePoolRevision,
)


def _recorded_boundary(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise IndustryThesisOwnerAcceptanceError(
            "INDUSTRY_THESIS_ACCEPTANCE_CHRONOLOGY_INVALID",
            "as_of_recorded_at_utc must be explicit UTC",
        )
    return value.astimezone(timezone.utc)


def _display_title(revision: IndustryThesisSessionRevision) -> str:
    reviewed = (revision.thesis_title_reviewed or "").strip()
    if reviewed:
        return reviewed
    original = revision.thesis_text_original.strip()
    first_line = next(
        (line.strip() for line in original.splitlines() if line.strip()),
        "未命名研究",
    )
    return first_line if len(first_line) <= 80 else f"{first_line[:77]}…"


class IndustryThesisOwnerAcceptanceWorkbenchQueryService:
    """Compose an exact-context acceptance view without owning accepted state."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_acceptance_view(
        self,
        *,
        session_id: UUID,
        reviewed_session_revision_id: UUID,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        recorded_boundary = _recorded_boundary(as_of_recorded_at_utc)
        reviewed_projection = IndustryThesisReviewedPlanQueryService(
            self._session
        ).get_reviewed_plan(
            reviewed_session_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=recorded_boundary,
        )
        if reviewed_projection["session_id"] != str(session_id):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_NOT_READY",
                "exact reviewed revision does not belong to the route-owned session",
            )
        if (
            reviewed_projection["acceptance_plan_version"]
            != ACCEPTANCE_PLAN_VERSION
            or reviewed_projection["acceptance_capability"]["state"] != "ready"
            or reviewed_projection["owner_context"] is None
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_NOT_READY",
                "unaccepted v1 reviewed plans require an explicit v2 re-review",
            )

        context = reviewed_projection["owner_context"]
        if (
            context.get("owner_context_contract_version")
            != OWNER_CONTEXT_VERSION
            or context.get("map_mode") != MAP_MODE
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "reviewed Owner Context contract is unsupported",
            )
        try:
            case_id = UUID(context["research_case_id"])
            map_id = UUID(context["industry_map_id"])
            map_revision_id = UUID(context["industry_map_revision_id"])
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "reviewed Owner Context identifiers are invalid",
            ) from exc

        reviewed = self._session.get(
            IndustryThesisSessionRevision,
            reviewed_session_revision_id,
        )
        identity = self._session.get(IndustryThesisSessionIdentity, session_id)
        if (
            reviewed is None
            or identity is None
            or reviewed.session_id != session_id
            or reviewed.workflow_state != "reviewed_plan_ready"
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_NOT_READY"
            )
        if identity.latest_revision_number != reviewed.revision_number:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE"
            )

        header = self._session.execute(
            select(ResearchCase, IndustryMap, IndustryMapRevision)
            .join(IndustryMap, IndustryMap.case_id == ResearchCase.id)
            .join(IndustryMapRevision, IndustryMapRevision.map_id == IndustryMap.id)
            .where(
                ResearchCase.id == case_id,
                IndustryMap.id == map_id,
                IndustryMapRevision.id == map_revision_id,
            )
        ).one_or_none()
        if header is None:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED"
            )
        research_case, industry_map, map_revision = header
        if (
            map_revision.information_cutoff_date > as_of_cutoff
            or stored_utc(map_revision.recorded_at_utc) > recorded_boundary
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_CHRONOLOGY_INVALID"
            )

        plan = reviewed_projection["acceptance_plan"]
        selected_entries = list(plan.get("selected_candidates", []))
        if not selected_entries:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE",
                "reviewed plan contains no selected candidates",
            )
        try:
            selected_ids = [UUID(item["candidate_revision_id"]) for item in selected_entries]
        except (KeyError, TypeError, ValueError) as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            ) from exc

        candidate_rows = list(
            self._session.scalars(
                select(IndustryThesisCandidateRevision).where(
                    IndustryThesisCandidateRevision.id.in_(selected_ids),
                    IndustryThesisCandidateRevision.session_revision_id == reviewed.id,
                    IndustryThesisCandidateRevision.review_state
                    == "selected_for_acceptance",
                )
            )
        )
        candidates = {row.id: row for row in candidate_rows}
        if set(candidates) != set(selected_ids):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE"
            )

        stock_ids = {
            row.proposed_stock_basic_record_id
            for row in candidate_rows
            if row.proposed_stock_basic_record_id is not None
        }
        stocks = {
            row.id: row
            for row in self._session.scalars(
                select(StockBasicRecord).where(StockBasicRecord.id.in_(stock_ids))
            )
        } if stock_ids else {}

        # Critical v2 boundary: the reviewed context is part of the SQL predicate.
        # Rows from another case, map, or map revision are never considered even
        # when they point at the same StockBasicRecord.
        owner_pairs = list(
            self._session.execute(
                select(Stage1Beneficiary, Stage1BeneficiaryRevision)
                .join(
                    Stage1BeneficiaryRevision,
                    Stage1BeneficiaryRevision.beneficiary_id == Stage1Beneficiary.id,
                )
                .where(
                    Stage1Beneficiary.case_id == case_id,
                    Stage1Beneficiary.map_id == map_id,
                    Stage1BeneficiaryRevision.selected_map_revision_id
                    == map_revision_id,
                    Stage1BeneficiaryRevision.stock_basic_record_id.in_(stock_ids),
                    Stage1BeneficiaryRevision.assessment_status != "rejected",
                    Stage1BeneficiaryRevision.information_cutoff_date <= as_of_cutoff,
                    Stage1BeneficiaryRevision.recorded_at_utc <= recorded_boundary,
                )
                .order_by(
                    Stage1Beneficiary.id,
                    Stage1BeneficiaryRevision.revision_no,
                )
            )
        ) if stock_ids else []

        revision_ids = [revision.id for _, revision in owner_pairs]
        semantic_rows = list(
            self._session.execute(
                select(
                    Stage1BeneficiarySemanticProfile,
                    Stage1BeneficiarySemanticProfileRevision,
                )
                .join(
                    Stage1BeneficiarySemanticProfileRevision,
                    Stage1BeneficiarySemanticProfileRevision.profile_id
                    == Stage1BeneficiarySemanticProfile.id,
                )
                .where(
                    Stage1BeneficiarySemanticProfileRevision.beneficiary_revision_id.in_(
                        revision_ids
                    ),
                    Stage1BeneficiarySemanticProfileRevision.selected_map_revision_id
                    == map_revision_id,
                    Stage1BeneficiarySemanticProfileRevision.overall_status != "rejected",
                    Stage1BeneficiarySemanticProfileRevision.information_cutoff_date
                    <= as_of_cutoff,
                    Stage1BeneficiarySemanticProfileRevision.recorded_at_utc
                    <= recorded_boundary,
                )
            )
        ) if revision_ids else []
        semantics_by_revision: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
        for profile, semantic_revision in semantic_rows:
            semantics_by_revision[semantic_revision.beneficiary_revision_id].append(
                {
                    "profile_id": str(profile.id),
                    "profile_revision_id": str(semantic_revision.id),
                    "summary": semantic_revision.summary,
                    "overall_status": semantic_revision.overall_status,
                }
            )

        exact_by_stock: dict[int, list[tuple[Stage1Beneficiary, Stage1BeneficiaryRevision]]] = defaultdict(list)
        latest_by_beneficiary: dict[UUID, Stage1BeneficiaryRevision] = {}
        for beneficiary, revision in owner_pairs:
            exact_by_stock[revision.stock_basic_record_id].append((beneficiary, revision))
            current = latest_by_beneficiary.get(beneficiary.id)
            if current is None or revision.revision_no > current.revision_no:
                latest_by_beneficiary[beneficiary.id] = revision

        pool_pairs = list(
            self._session.execute(
                select(Stage1CandidatePool, Stage1CandidatePoolRevision)
                .join(
                    Stage1CandidatePoolRevision,
                    Stage1CandidatePoolRevision.candidate_pool_id
                    == Stage1CandidatePool.id,
                )
                .where(
                    Stage1CandidatePool.case_id == case_id,
                    Stage1CandidatePool.map_id == map_id,
                    Stage1CandidatePoolRevision.selected_map_revision_id
                    == map_revision_id,
                    Stage1CandidatePoolRevision.information_cutoff_date <= as_of_cutoff,
                    Stage1CandidatePoolRevision.recorded_at_utc <= recorded_boundary,
                )
                .order_by(
                    Stage1CandidatePool.id,
                    Stage1CandidatePoolRevision.revision_no,
                )
            )
        )
        latest_pool_by_id: dict[UUID, tuple[Stage1CandidatePool, Stage1CandidatePoolRevision]] = {}
        for pool, revision in pool_pairs:
            current = latest_pool_by_id.get(pool.id)
            if current is None or revision.revision_no > current[1].revision_no:
                latest_pool_by_id[pool.id] = (pool, revision)

        members: list[dict[str, Any]] = []
        blocking_reasons: list[dict[str, str]] = []
        for sequence, entry in enumerate(selected_entries):
            candidate_id = UUID(entry["candidate_revision_id"])
            candidate = candidates[candidate_id]
            stock_id = candidate.proposed_stock_basic_record_id
            stock = stocks.get(stock_id) if stock_id is not None else None
            member_blocking: list[dict[str, str]] = []
            if stock_id is None:
                member_blocking.append(
                    {
                        "code": "INDUSTRY_THESIS_ACCEPTANCE_LISTED_INSTRUMENT_ONLY",
                        "message": "审核结果没有冻结可接受的正式股票记录。",
                    }
                )
            elif stock is None:
                member_blocking.append(
                    {
                        "code": "INDUSTRY_THESIS_ACCEPTANCE_STOCK_IDENTITY_REQUIRED",
                        "message": "冻结的正式股票记录已不可见或不存在。",
                    }
                )

            exact_rows = exact_by_stock.get(stock_id, []) if stock_id is not None else []
            reuse_options = [
                {
                    "beneficiary_id": str(beneficiary.id),
                    "beneficiary_revision_id": str(revision.id),
                    "revision_number": revision.revision_no,
                    "stock_basic_record_id": revision.stock_basic_record_id,
                    "legacy_beneficiary_kind": revision.beneficiary_kind,
                    "assessment_status": revision.assessment_status,
                    "rationale_summary": revision.rationale_summary,
                    "semantic_reuse_options": sorted(
                        semantics_by_revision.get(revision.id, []),
                        key=lambda item: item["profile_revision_id"],
                    ),
                }
                for beneficiary, revision in exact_rows
            ]
            append_options = [
                {
                    "beneficiary_id": str(beneficiary.id),
                    "expected_latest_revision_id": str(revision.id),
                    "revision_number": revision.revision_no,
                    "stock_basic_record_id": revision.stock_basic_record_id,
                }
                for beneficiary, revision in exact_rows
                if latest_by_beneficiary.get(beneficiary.id) is revision
            ]
            identity_exists = bool(exact_rows)
            members.append(
                {
                    "sequence": sequence,
                    "reviewed_candidate_revision_id": str(candidate.id),
                    "ordinary_identity_label": candidate.company_label_original,
                    "reviewed_proposal_exposure": candidate.proposed_exposure_type,
                    "frozen_stock_binding": (
                        {
                            "state": "available",
                            "stock_basic_record_id": stock.id,
                            "ordinary_label": f"{stock.stock_name}（{stock.stock_code}）",
                            "source": stock.source,
                            "stock_code": stock.stock_code,
                            "exchange": stock.exchange,
                            "industry": stock.industry,
                        }
                        if stock is not None
                        else {
                            "state": "missing_or_listed_instrument_only",
                            "stock_basic_record_id": None,
                            "ordinary_label": candidate.company_label_original,
                        }
                    ),
                    "stage1_reuse_options": sorted(
                        reuse_options,
                        key=lambda item: (
                            item["beneficiary_id"],
                            item["revision_number"],
                        ),
                    ),
                    "stage1_append_options": sorted(
                        append_options,
                        key=lambda item: item["beneficiary_id"],
                    ),
                    "stage1_create_contract": {
                        "available": stock is not None and not identity_exists,
                        "stock_basic_record_id": None if stock is None else stock.id,
                        "source": None if stock is None else stock.source,
                        "stock_code": None if stock is None else stock.stock_code,
                        "context_locked": True,
                    },
                    "semantic_authoring_state": "reuse_or_none_only",
                    "blocking_reasons": member_blocking,
                }
            )
            blocking_reasons.extend(member_blocking)

        return {
            "session_id": str(session_id),
            "reviewed_session_revision_id": str(reviewed.id),
            "reviewed_session_revision_number": reviewed.revision_number,
            "reviewed_plan_fingerprint_sha256": reviewed_projection[
                "acceptance_plan_fingerprint_sha256"
            ],
            "expected_session_latest_revision_number": identity.latest_revision_number,
            "thesis_title": _display_title(reviewed),
            "research_case": {
                "id": str(research_case.id),
                "case_key": research_case.case_key,
            },
            "industry_map": {
                "id": str(industry_map.id),
                "map_key": industry_map.map_key,
                "revision_id": str(map_revision.id),
                "revision_number": map_revision.revision_no,
                "title": map_revision.title,
                "scope": map_revision.scope,
            },
            "owner_context": {
                "owner_context_contract_version": OWNER_CONTEXT_VERSION,
                "map_mode": MAP_MODE,
                "research_case_id": str(case_id),
                "industry_map_id": str(map_id),
                "industry_map_revision_id": str(map_revision_id),
            },
            "map_mode": MAP_MODE,
            "owner_acceptance_plan_version": OWNER_ACCEPTANCE_PLAN_VERSION,
            "members": members,
            "candidate_pool_operation_contract": {
                "append_options": [
                    {
                        "candidate_pool_id": str(pool.id),
                        "expected_latest_revision_id": str(revision.id),
                        "revision_number": revision.revision_no,
                        "title": revision.title,
                        "scope": revision.scope,
                    }
                    for pool, revision in sorted(
                        latest_pool_by_id.values(),
                        key=lambda item: str(item[0].id),
                    )
                ],
                "reuse_options": [
                    {
                        "candidate_pool_id": str(pool.id),
                        "candidate_pool_revision_id": str(revision.id),
                        "revision_number": revision.revision_no,
                        "title": revision.title,
                        "scope": revision.scope,
                    }
                    for pool, revision in pool_pairs
                ],
                "zero_supported_contract": {
                    "mode": "none_no_supported_members"
                },
            },
            "blocking_reasons": blocking_reasons,
            "commit_possible": not blocking_reasons,
            "technical_details": {
                "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
                "selected_context": {
                    "research_case_id": str(case_id),
                    "industry_map_id": str(map_id),
                    "industry_map_revision_id": str(map_revision_id),
                },
            },
        }

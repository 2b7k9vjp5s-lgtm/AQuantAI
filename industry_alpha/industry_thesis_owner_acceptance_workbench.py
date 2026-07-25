"""Bounded ordinary-user projections for Industry Thesis owner acceptance."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import literal, select, union_all
from sqlalchemy.orm import Session

from backend.database.models import IngestionRun, StockBasicRecord
from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticProfile,
    Stage1BeneficiarySemanticProfileRevision,
)
from industry_alpha.chain_map_models import (
    IndustryMap,
    IndustryMapNodeRevision,
    IndustryMapObservationRevision,
    IndustryMapRelationshipRevision,
    IndustryMapRevision,
)
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateRevision,
    IndustryThesisOutputLinkIdentity,
    IndustryThesisOutputLinkRevision,
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    ACCEPTANCE_STATUSES,
    LEGACY_BENEFICIARY_KINDS,
    MAP_MODE,
    OUTPUT_CONTRACT_VERSION,
    OWNER_ACCEPTANCE_PLAN_VERSION,
    IndustryThesisOwnerAcceptanceError,
)
from industry_alpha.industry_thesis_review import (
    IndustryThesisReviewedPlanQueryService,
)
from industry_alpha.industry_thesis_rules import json_value, stored_utc
from industry_alpha.models import Claim, ClaimRevision, ResearchCase
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryAssertionLink,
    Stage1BeneficiaryClaimLink,
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
)


_SOURCE_LABELS = {
    "accepted_local_mapping": "已接受本地映射",
    "existing_industry_map_revision": "冻结 Stage 1 候选池",
    "user_seed": "明确公司种子",
    "ai_draft": "AI 草稿",
}
_KIND_LABELS = {"direct": "直接受益", "secondary": "次级受益", "potential": "潜在受益"}
_STATUS_LABELS = {"draft": "草稿", "supported": "已有支持", "disputed": "存在争议"}
_ASSERTION_LABELS = {
    "node": "产业链节点",
    "relationship": "产业链关系",
    "observation": "产业观察",
}


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


def _display_title(revision: IndustryThesisSessionRevision) -> str:
    reviewed = (revision.thesis_title_reviewed or "").strip()
    if reviewed:
        return reviewed
    original = revision.thesis_text_original.strip()
    first_line = next((line.strip() for line in original.splitlines() if line.strip()), "未命名研究")
    return first_line if len(first_line) <= 80 else f"{first_line[:77]}…"


def _pool_key(reviewed_session_revision_id: UUID) -> str:
    return f"industry-thesis-acceptance-v1:{reviewed_session_revision_id}"


class IndustryThesisOwnerAcceptanceWorkbenchQueryService:
    """Compose bounded ordinary-user read models without owning accepted state."""

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
                "exact route-owned reviewed revision does not belong to the session",
            )
        reviewed = self._session.get(
            IndustryThesisSessionRevision,
            reviewed_session_revision_id,
        )
        identity = self._session.get(IndustryThesisSessionIdentity, session_id)
        if (
            reviewed is None
            or identity is None
            or reviewed.workflow_state != "reviewed_plan_ready"
            or reviewed.session_id != identity.id
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_NOT_READY"
            )
        if identity.latest_revision_number != reviewed.revision_number:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE"
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
                select(IndustryThesisCandidateRevision)
                .where(IndustryThesisCandidateRevision.id.in_(selected_ids))
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
        stock_pairs = list(
            self._session.execute(
                select(StockBasicRecord, IngestionRun)
                .join(IngestionRun, IngestionRun.id == StockBasicRecord.ingestion_run_id)
                .where(StockBasicRecord.id.in_(stock_ids))
            )
        ) if stock_ids else []
        stocks = {stock.id: (stock, run) for stock, run in stock_pairs}

        owner_pairs = list(
            self._session.execute(
                select(Stage1Beneficiary, Stage1BeneficiaryRevision)
                .join(
                    Stage1BeneficiaryRevision,
                    Stage1BeneficiaryRevision.beneficiary_id == Stage1Beneficiary.id,
                )
                .where(
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
        assertion_links = list(
            self._session.scalars(
                select(Stage1BeneficiaryAssertionLink).where(
                    Stage1BeneficiaryAssertionLink.beneficiary_revision_id.in_(revision_ids)
                )
            )
        ) if revision_ids else []
        claim_rows = list(
            self._session.execute(
                select(Stage1BeneficiaryClaimLink, ClaimRevision, Claim)
                .join(
                    ClaimRevision,
                    ClaimRevision.id == Stage1BeneficiaryClaimLink.claim_revision_id,
                )
                .join(Claim, Claim.id == ClaimRevision.claim_id)
                .where(
                    Stage1BeneficiaryClaimLink.beneficiary_revision_id.in_(revision_ids),
                    ClaimRevision.information_cutoff_date <= as_of_cutoff,
                    ClaimRevision.recorded_at_utc <= recorded_boundary,
                )
            )
        ) if revision_ids else []

        assertions_by_revision: dict[UUID, list[Stage1BeneficiaryAssertionLink]] = defaultdict(list)
        for link in assertion_links:
            assertions_by_revision[link.beneficiary_revision_id].append(link)
        claims_by_revision: dict[UUID, list[tuple[Stage1BeneficiaryClaimLink, ClaimRevision, Claim]]] = defaultdict(list)
        for link, claim_revision, claim in claim_rows:
            claims_by_revision[link.beneficiary_revision_id].append((link, claim_revision, claim))

        context_coverage: dict[tuple[UUID, UUID, UUID], set[int]] = defaultdict(set)
        for beneficiary, revision in owner_pairs:
            context_coverage[
                (beneficiary.case_id, beneficiary.map_id, revision.selected_map_revision_id)
            ].add(revision.stock_basic_record_id)
        if not context_coverage:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED",
                "no exact persisted Stage 1 context is reachable for the frozen identities",
            )
        best_size = max(len(values) for values in context_coverage.values())
        best_contexts = [
            key for key, values in context_coverage.items() if len(values) == best_size
        ]
        if len(best_contexts) != 1:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED",
                "multiple exact case/map contexts are equally compatible",
            )
        case_id, map_id, map_revision_id = best_contexts[0]

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
        if not _visible(
            map_revision.information_cutoff_date,
            map_revision.recorded_at_utc,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=recorded_boundary,
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_CHRONOLOGY_INVALID"
            )

        context_pairs = [
            (beneficiary, revision)
            for beneficiary, revision in owner_pairs
            if (
                beneficiary.case_id,
                beneficiary.map_id,
                revision.selected_map_revision_id,
            )
            == best_contexts[0]
        ]
        context_revision_ids = [revision.id for _, revision in context_pairs]

        assertion_id_rows: list[tuple[str, UUID]] = []
        for revision_id in context_revision_ids:
            for link in assertions_by_revision.get(revision_id, []):
                if link.node_revision_id is not None:
                    assertion_id_rows.append(("node", link.node_revision_id))
                elif link.relationship_revision_id is not None:
                    assertion_id_rows.append(("relationship", link.relationship_revision_id))
                elif link.observation_revision_id is not None:
                    assertion_id_rows.append(("observation", link.observation_revision_id))
        assertion_id_rows = sorted(set(assertion_id_rows), key=lambda item: (item[0], str(item[1])))

        assertion_options: list[dict[str, Any]] = []
        if assertion_id_rows:
            node_ids = [value for kind, value in assertion_id_rows if kind == "node"]
            relationship_ids = [
                value for kind, value in assertion_id_rows if kind == "relationship"
            ]
            observation_ids = [
                value for kind, value in assertion_id_rows if kind == "observation"
            ]
            statements = []
            if node_ids:
                statements.append(
                    select(
                        literal("node").label("kind"),
                        IndustryMapNodeRevision.id.label("revision_id"),
                        IndustryMapNodeRevision.label.label("label"),
                        IndustryMapNodeRevision.assertion_status.label("status"),
                        IndustryMapNodeRevision.information_cutoff_date.label("cutoff"),
                        IndustryMapNodeRevision.recorded_at_utc.label("recorded_at"),
                    ).where(IndustryMapNodeRevision.id.in_(node_ids))
                )
            if relationship_ids:
                statements.append(
                    select(
                        literal("relationship").label("kind"),
                        IndustryMapRelationshipRevision.id.label("revision_id"),
                        IndustryMapRelationshipRevision.relation_kind.label("label"),
                        IndustryMapRelationshipRevision.assertion_status.label("status"),
                        IndustryMapRelationshipRevision.information_cutoff_date.label("cutoff"),
                        IndustryMapRelationshipRevision.recorded_at_utc.label("recorded_at"),
                    ).where(IndustryMapRelationshipRevision.id.in_(relationship_ids))
                )
            if observation_ids:
                statements.append(
                    select(
                        literal("observation").label("kind"),
                        IndustryMapObservationRevision.id.label("revision_id"),
                        IndustryMapObservationRevision.title.label("label"),
                        IndustryMapObservationRevision.assertion_status.label("status"),
                        IndustryMapObservationRevision.information_cutoff_date.label("cutoff"),
                        IndustryMapObservationRevision.recorded_at_utc.label("recorded_at"),
                    ).where(IndustryMapObservationRevision.id.in_(observation_ids))
                )
            assertion_result = self._session.execute(
                statements[0] if len(statements) == 1 else union_all(*statements)
            )
            for row in assertion_result:
                if (
                    row.status != "rejected"
                    and row.cutoff <= as_of_cutoff
                    and stored_utc(row.recorded_at) <= recorded_boundary
                ):
                    assertion_options.append(
                        {
                            "assertion_kind": row.kind,
                            "assertion_revision_id": str(row.revision_id),
                            "ordinary_label": f"{_ASSERTION_LABELS[row.kind]} · {row.label}",
                            "assertion_status": row.status,
                        }
                    )

        claim_option_map: dict[UUID, dict[str, Any]] = {}
        for revision_id in context_revision_ids:
            for _link, claim_revision, claim in claims_by_revision.get(revision_id, []):
                if claim_revision.claim_status == "rejected":
                    continue
                claim_option_map[claim_revision.id] = {
                    "claim_revision_id": str(claim_revision.id),
                    "ordinary_label": claim_revision.statement,
                    "claim_kind": claim_revision.claim_kind,
                    "claim_status": claim_revision.claim_status,
                    "claim_key": claim.claim_key,
                }
        claim_options = sorted(
            claim_option_map.values(),
            key=lambda item: (item["claim_key"], item["claim_revision_id"]),
        )

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
                        context_revision_ids
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
        ) if context_revision_ids else []
        semantics_by_revision: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
        for profile, semantic_revision in semantic_rows:
            semantics_by_revision[semantic_revision.beneficiary_revision_id].append(
                {
                    "profile_id": str(profile.id),
                    "profile_revision_id": str(semantic_revision.id),
                    "ordinary_label": semantic_revision.summary,
                    "overall_status": semantic_revision.overall_status,
                    "taxonomy_version": semantic_revision.taxonomy_version,
                }
            )

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
                    Stage1CandidatePoolRevision.selected_map_revision_id == map_revision_id,
                    Stage1CandidatePoolRevision.information_cutoff_date <= as_of_cutoff,
                    Stage1CandidatePoolRevision.recorded_at_utc <= recorded_boundary,
                )
                .order_by(
                    Stage1CandidatePool.id,
                    Stage1CandidatePoolRevision.revision_no,
                )
            )
        )
        pool_revision_ids = [revision.id for _, revision in pool_pairs]
        pool_memberships = list(
            self._session.scalars(
                select(Stage1CandidatePoolMembership).where(
                    Stage1CandidatePoolMembership.candidate_pool_revision_id.in_(
                        pool_revision_ids
                    )
                )
            )
        ) if pool_revision_ids else []
        pool_members_by_revision: dict[UUID, list[str]] = defaultdict(list)
        for membership in pool_memberships:
            pool_members_by_revision[membership.candidate_pool_revision_id].append(
                str(membership.beneficiary_revision_id)
            )
        latest_pool_by_id: dict[UUID, tuple[Stage1CandidatePool, Stage1CandidatePoolRevision]] = {}
        for pool, revision in pool_pairs:
            current = latest_pool_by_id.get(pool.id)
            if current is None or revision.revision_no > current[1].revision_no:
                latest_pool_by_id[pool.id] = (pool, revision)

        latest_owner_by_beneficiary: dict[UUID, tuple[Stage1Beneficiary, Stage1BeneficiaryRevision]] = {}
        for beneficiary, revision in context_pairs:
            current = latest_owner_by_beneficiary.get(beneficiary.id)
            if current is None or revision.revision_no > current[1].revision_no:
                latest_owner_by_beneficiary[beneficiary.id] = (beneficiary, revision)

        members: list[dict[str, Any]] = []
        global_blocking: list[dict[str, str]] = []
        for sequence, entry in enumerate(selected_entries):
            candidate_id = UUID(entry["candidate_revision_id"])
            candidate = candidates[candidate_id]
            stock_id = candidate.proposed_stock_basic_record_id
            stock_pair = stocks.get(stock_id) if stock_id is not None else None
            blocking: list[dict[str, str]] = []
            if stock_id is None:
                code = (
                    "INDUSTRY_THESIS_ACCEPTANCE_LISTED_INSTRUMENT_ONLY"
                    if candidate.proposed_listed_instrument_id is not None
                    else "INDUSTRY_THESIS_ACCEPTANCE_STOCK_IDENTITY_REQUIRED"
                )
                blocking.append({"code": code, "message": "审核结果没有冻结可接受的正式股票记录。"})
            elif stock_pair is None:
                blocking.append(
                    {
                        "code": "INDUSTRY_THESIS_ACCEPTANCE_STOCK_IDENTITY_REQUIRED",
                        "message": "冻结的正式股票记录已不可见或不存在。",
                    }
                )

            stock = stock_pair[0] if stock_pair else None
            run = stock_pair[1] if stock_pair else None
            exact_rows = [
                (beneficiary, revision)
                for beneficiary, revision in context_pairs
                if revision.stock_basic_record_id == stock_id
            ]
            reuse_options: list[dict[str, Any]] = []
            append_options: list[dict[str, Any]] = []
            for beneficiary, revision in exact_rows:
                complete_links = bool(assertions_by_revision.get(revision.id)) and bool(
                    claims_by_revision.get(revision.id)
                )
                if complete_links:
                    reuse_options.append(
                        {
                            "beneficiary_id": str(beneficiary.id),
                            "beneficiary_revision_id": str(revision.id),
                            "stock_basic_record_id": revision.stock_basic_record_id,
                            "ordinary_label": (
                                f"{_STATUS_LABELS.get(revision.assessment_status, revision.assessment_status)}"
                                f" · 第 {revision.revision_no} 版"
                            ),
                            "legacy_beneficiary_kind": revision.beneficiary_kind,
                            "assessment_status": revision.assessment_status,
                            "rationale_summary": revision.rationale_summary,
                            "semantic_reuse_options": semantics_by_revision.get(revision.id, []),
                        }
                    )
                latest = latest_owner_by_beneficiary.get(beneficiary.id)
                if latest and latest[1].id == revision.id:
                    append_options.append(
                        {
                            "beneficiary_id": str(beneficiary.id),
                            "expected_latest_revision_id": str(revision.id),
                            "stock_basic_record_id": revision.stock_basic_record_id,
                            "ordinary_label": f"在第 {revision.revision_no} 版后追加",
                            "current_legacy_beneficiary_kind": revision.beneficiary_kind,
                            "current_assessment_status": revision.assessment_status,
                        }
                    )

            identity_exists = any(
                beneficiary.source == stock.source
                and beneficiary.stock_code == stock.stock_code
                for beneficiary, _revision in context_pairs
            ) if stock else False
            create_available = bool(
                stock
                and run
                and not identity_exists
                and assertion_options
                and claim_options
            )
            create_blocking_reason = None
            if stock and not create_available:
                if identity_exists:
                    create_blocking_reason = "该正式公司在当前研究案例和产业地图中已有 Stage 1 身份，请使用追加或复用。"
                elif not assertion_options or not claim_options:
                    create_blocking_reason = "当前精确产业地图没有可用于创建的完整断言和研究主张绑定。"
                else:
                    create_blocking_reason = "冻结公司记录无法提供稳定的来源和股票代码。"

            member = {
                "sequence": sequence,
                "reviewed_candidate_revision_id": str(candidate.id),
                "ordinary_identity_label": candidate.company_label_original,
                "reviewed_proposal_exposure": candidate.proposed_exposure_type,
                "source_label": _SOURCE_LABELS.get(candidate.source_kind, candidate.source_kind),
                "frozen_stock_binding": (
                    {
                        "state": "available",
                        "stock_basic_record_id": stock.id,
                        "ordinary_label": f"{stock.stock_name}（{stock.stock_code}）",
                        "source": stock.source,
                        "stock_code": stock.stock_code,
                        "exchange": stock.exchange,
                        "industry": stock.industry,
                        "information_cutoff_date": run.information_cutoff_date.isoformat(),
                    }
                    if stock and run
                    else {
                        "state": "missing_or_listed_instrument_only",
                        "stock_basic_record_id": None,
                        "ordinary_label": candidate.company_label_original,
                        "source": None,
                        "stock_code": None,
                        "exchange": None,
                        "industry": None,
                        "information_cutoff_date": None,
                    }
                ),
                "frozen_stock_confirmation_required": True,
                "stage1_reuse_options": sorted(
                    reuse_options,
                    key=lambda item: item["beneficiary_revision_id"],
                ),
                "stage1_append_options": sorted(
                    append_options,
                    key=lambda item: item["beneficiary_id"],
                ),
                "stage1_create_contract": {
                    "available": create_available,
                    "stock_basic_record_id": None if stock is None else stock.id,
                    "source": None if stock is None else stock.source,
                    "stock_code": None if stock is None else stock.stock_code,
                    "legacy_beneficiary_kind_options": [
                        {"value": value, "label": _KIND_LABELS[value]}
                        for value in LEGACY_BENEFICIARY_KINDS
                    ],
                    "assessment_status_options": [
                        {"value": value, "label": _STATUS_LABELS[value]}
                        for value in ACCEPTANCE_STATUSES
                    ],
                    "map_assertion_options": assertion_options,
                    "claim_revision_options": claim_options,
                    "blocking_reason": create_blocking_reason,
                },
                "semantic_authoring_state": "reuse_or_none_only",
                "derived_handoff_rule": (
                    "最终 Stage 1 状态为 supported 时进入全局后续研究池；"
                    "draft/disputed 保留在完整成果但不进入后续研究池。"
                ),
                "blocking_reasons": blocking,
                "readiness_hints": [
                    "未绑定类型化语义时，成果仍可接受，但后续准备度会显示缺口。",
                    "本次接受不会创建公司研究或投资候选状态。",
                ],
                "technical_details": {
                    "candidate_revision_id": str(candidate.id),
                    "candidate_source_kind": candidate.source_kind,
                    "candidate_recorded_at_utc": stored_utc(candidate.recorded_at_utc).isoformat(),
                },
            }
            members.append(member)
            global_blocking.extend(blocking)

        append_pool_options = [
            {
                "candidate_pool_id": str(pool.id),
                "expected_latest_revision_id": str(revision.id),
                "ordinary_label": revision.title,
                "current_scope": revision.scope,
                "current_member_count": len(pool_members_by_revision.get(revision.id, [])),
                "revision_number": revision.revision_no,
            }
            for pool, revision in latest_pool_by_id.values()
        ]
        reuse_pool_options = [
            {
                "candidate_pool_id": str(pool.id),
                "candidate_pool_revision_id": str(revision.id),
                "ordinary_label": revision.title,
                "scope": revision.scope,
                "beneficiary_revision_ids": sorted(
                    pool_members_by_revision.get(revision.id, [])
                ),
                "revision_number": revision.revision_no,
            }
            for pool, revision in pool_pairs
        ]

        return {
            "session_id": str(session_id),
            "reviewed_session_revision_id": str(reviewed.id),
            "reviewed_session_revision_number": reviewed.revision_number,
            "reviewed_plan_fingerprint_sha256": reviewed_projection[
                "acceptance_plan_fingerprint_sha256"
            ],
            "expected_session_latest_revision_number": identity.latest_revision_number,
            "thesis_title": _display_title(reviewed),
            "thesis_text_original": reviewed.thesis_text_original,
            "coverage_state": reviewed.coverage_state,
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
            "information_cutoff_date": reviewed.information_cutoff_date.isoformat(),
            "recorded_at_utc": stored_utc(reviewed.recorded_at_utc).isoformat(),
            "as_of_cutoff": as_of_cutoff.isoformat(),
            "as_of_recorded_at_utc": recorded_boundary.isoformat(),
            "map_mode": MAP_MODE,
            "owner_acceptance_plan_version": OWNER_ACCEPTANCE_PLAN_VERSION,
            "output_metadata_defaults": {
                "output_title": _display_title(reviewed),
                "output_scope": map_revision.scope,
            },
            "members": members,
            "candidate_pool_operation_contract": {
                "create_contract": {
                    "mode": "create_supported_handoff",
                    "pool_key": _pool_key(reviewed.id),
                    "title_default": f"{_display_title(reviewed)} · supported 后续研究",
                    "scope_default": "仅包含本次接受后 Stage 1 状态为 supported 的精确成员。",
                },
                "append_options": sorted(
                    append_pool_options,
                    key=lambda item: item["candidate_pool_id"],
                ),
                "reuse_options": sorted(
                    reuse_pool_options,
                    key=lambda item: (
                        item["candidate_pool_id"],
                        item["revision_number"],
                    ),
                ),
                "zero_supported_contract": {
                    "mode": "none_no_supported_members",
                    "notice": "仅当所有最终 Stage 1 状态均为 draft/disputed 时可用。",
                },
            },
            "revision_note_constraints": {"required": True, "max_length": 1000},
            "blocking_reasons": global_blocking,
            "commit_possible": not global_blocking,
            "primary_action": {
                "kind": "preview" if not global_blocking else "correct_review",
                "label": "生成变更预览" if not global_blocking else "返回修正审核结果",
            },
            "technical_details": {
                "acceptance_plan_version": plan.get("acceptance_plan_version"),
                "selected_context": {
                    "research_case_id": str(case_id),
                    "industry_map_id": str(map_id),
                    "industry_map_revision_id": str(map_revision_id),
                    "compatible_frozen_stock_count": best_size,
                },
            },
        }

    def get_accepted_result_view(
        self,
        *,
        session_id: UUID,
        accepted_session_revision_id: UUID,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        recorded_boundary = _recorded_boundary(as_of_recorded_at_utc)
        accepted = self._session.get(
            IndustryThesisSessionRevision,
            accepted_session_revision_id,
        )
        if (
            accepted is None
            or accepted.session_id != session_id
            or accepted.workflow_state != "accepted_outputs_linked"
            or not _visible(
                accepted.information_cutoff_date,
                accepted.recorded_at_utc,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=recorded_boundary,
            )
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "exact accepted session revision is missing or outside the boundary",
            )
        accepted_graph = json_value(accepted.draft_graph_json, "accepted draft graph")
        if not isinstance(accepted_graph, dict):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )
        try:
            output_revision_id = UUID(accepted_graph["output_link_revision_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            ) from exc

        header = self._session.execute(
            select(
                IndustryThesisOutputLinkRevision,
                IndustryThesisOutputLinkIdentity,
                IndustryThesisSessionRevision,
                IndustryThesisSessionIdentity,
                ResearchCase,
                IndustryMap,
                IndustryMapRevision,
            )
            .join(
                IndustryThesisOutputLinkIdentity,
                IndustryThesisOutputLinkIdentity.id
                == IndustryThesisOutputLinkRevision.output_link_id,
            )
            .join(
                IndustryThesisSessionRevision,
                IndustryThesisSessionRevision.id
                == IndustryThesisOutputLinkRevision.reviewed_session_revision_id,
            )
            .join(
                IndustryThesisSessionIdentity,
                IndustryThesisSessionIdentity.id
                == IndustryThesisSessionRevision.session_id,
            )
            .join(
                ResearchCase,
                ResearchCase.id == IndustryThesisOutputLinkRevision.research_case_id,
            )
            .join(
                IndustryMap,
                IndustryMap.id
                == IndustryThesisOutputLinkRevision.accepted_industry_map_identity_id,
            )
            .join(
                IndustryMapRevision,
                IndustryMapRevision.id
                == IndustryThesisOutputLinkRevision.accepted_industry_map_revision_id,
            )
            .where(IndustryThesisOutputLinkRevision.id == output_revision_id)
        ).one_or_none()
        if header is None:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )
        (
            output,
            output_identity,
            reviewed,
            session_identity,
            research_case,
            industry_map,
            map_revision,
        ) = header
        if (
            output.output_contract_version != OUTPUT_CONTRACT_VERSION
            or output.accepted_session_revision_id != accepted.id
            or output.session_revision_id != accepted.id
            or accepted.supersedes_revision_id != reviewed.id
            or reviewed.workflow_state != "reviewed_plan_ready"
            or reviewed.session_id != accepted.session_id
            or output_identity.session_id != accepted.session_id
            or session_identity.id != accepted.session_id
            or industry_map.case_id != research_case.id
            or map_revision.map_id != industry_map.id
            or not _visible(
                output.information_cutoff_date,
                output.recorded_at_utc,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=recorded_boundary,
            )
            or not _visible(
                reviewed.information_cutoff_date,
                reviewed.recorded_at_utc,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=recorded_boundary,
            )
            or not _visible(
                map_revision.information_cutoff_date,
                map_revision.recorded_at_utc,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=recorded_boundary,
            )
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )

        bindings = json_value(
            output.ordered_owner_output_bindings_json,
            "ordered owner output bindings",
        )
        beneficiary_revision_ids = json_value(
            output.ordered_beneficiary_revision_ids_json,
            "ordered beneficiary revision IDs",
        )
        if (
            not isinstance(bindings, list)
            or not bindings
            or not isinstance(beneficiary_revision_ids, list)
            or beneficiary_revision_ids
            != [item.get("beneficiary_revision_id") for item in bindings]
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )
        try:
            candidate_ids = [UUID(item["reviewed_candidate_revision_id"]) for item in bindings]
            beneficiary_ids = [UUID(item["beneficiary_id"]) for item in bindings]
            revision_ids = [UUID(item["beneficiary_revision_id"]) for item in bindings]
            semantic_revision_ids = [
                UUID(item["semantic_profile_revision_id"])
                for item in bindings
                if item.get("semantic_profile_revision_id") is not None
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            ) from exc

        candidate_rows = list(
            self._session.scalars(
                select(IndustryThesisCandidateRevision).where(
                    IndustryThesisCandidateRevision.id.in_(candidate_ids)
                )
            )
        )
        owner_rows = list(
            self._session.execute(
                select(Stage1Beneficiary, Stage1BeneficiaryRevision)
                .join(
                    Stage1BeneficiaryRevision,
                    Stage1BeneficiaryRevision.beneficiary_id == Stage1Beneficiary.id,
                )
                .where(
                    Stage1Beneficiary.id.in_(beneficiary_ids),
                    Stage1BeneficiaryRevision.id.in_(revision_ids),
                )
            )
        )
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
                    Stage1BeneficiarySemanticProfileRevision.id.in_(semantic_revision_ids)
                )
            )
        ) if semantic_revision_ids else []

        candidates = {row.id: row for row in candidate_rows}
        beneficiaries = {beneficiary.id: beneficiary for beneficiary, _ in owner_rows}
        revisions = {revision.id: revision for _, revision in owner_rows}
        semantic_profiles = {revision.id: (profile, revision) for profile, revision in semantic_rows}
        if (
            set(candidates) != set(candidate_ids)
            or set(beneficiaries) != set(beneficiary_ids)
            or set(revisions) != set(revision_ids)
            or set(semantic_profiles) != set(semantic_revision_ids)
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )

        pool_members: list[Stage1CandidatePoolMembership] = []
        pool_revision = None
        pool = None
        if output.accepted_candidate_pool_revision_id is not None:
            pool_header = self._session.execute(
                select(Stage1CandidatePool, Stage1CandidatePoolRevision)
                .join(
                    Stage1CandidatePoolRevision,
                    Stage1CandidatePoolRevision.candidate_pool_id
                    == Stage1CandidatePool.id,
                )
                .where(
                    Stage1CandidatePoolRevision.id
                    == output.accepted_candidate_pool_revision_id
                )
            ).one_or_none()
            if pool_header is None:
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
                )
            pool, pool_revision = pool_header
            pool_members = list(
                self._session.scalars(
                    select(Stage1CandidatePoolMembership).where(
                        Stage1CandidatePoolMembership.candidate_pool_revision_id
                        == pool_revision.id
                    )
                )
            )

        research_rows = list(
            self._session.execute(
                select(Stage2CompanyResearch, Stage2CompanyResearchRevision)
                .join(
                    Stage2CompanyResearchRevision,
                    Stage2CompanyResearchRevision.company_research_id
                    == Stage2CompanyResearch.id,
                )
                .where(
                    Stage2CompanyResearch.beneficiary_revision_id.in_(revision_ids),
                    Stage2CompanyResearchRevision.information_cutoff_date <= as_of_cutoff,
                    Stage2CompanyResearchRevision.recorded_at_utc <= recorded_boundary,
                )
                .order_by(
                    Stage2CompanyResearch.id,
                    Stage2CompanyResearchRevision.revision_no,
                )
            )
        )
        latest_research: dict[UUID, tuple[Stage2CompanyResearch, Stage2CompanyResearchRevision]] = {}
        for research, revision in research_rows:
            current = latest_research.get(research.beneficiary_revision_id)
            if current is None or revision.revision_no > current[1].revision_no:
                latest_research[research.beneficiary_revision_id] = (research, revision)

        supported_revision_ids: list[UUID] = []
        members: list[dict[str, Any]] = []
        for expected_sequence, binding in enumerate(bindings):
            candidate_id = UUID(binding["reviewed_candidate_revision_id"])
            beneficiary_id = UUID(binding["beneficiary_id"])
            revision_id = UUID(binding["beneficiary_revision_id"])
            candidate = candidates[candidate_id]
            beneficiary = beneficiaries[beneficiary_id]
            revision = revisions[revision_id]
            if (
                binding.get("sequence") != expected_sequence
                or candidate.session_revision_id != reviewed.id
                or candidate.review_state != "selected_for_acceptance"
                or revision.beneficiary_id != beneficiary.id
                or beneficiary.case_id != research_case.id
                or beneficiary.map_id != industry_map.id
                or revision.selected_map_revision_id != map_revision.id
                or revision.stock_basic_record_id != binding.get("stock_basic_record_id")
                or revision.beneficiary_kind != binding.get("legacy_beneficiary_kind")
                or revision.assessment_status != binding.get("assessment_status")
                or revision.assessment_status == "rejected"
                or not _visible(
                    revision.information_cutoff_date,
                    revision.recorded_at_utc,
                    as_of_cutoff=as_of_cutoff,
                    as_of_recorded_at_utc=recorded_boundary,
                )
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

            semantic_state = {
                "state": "missing",
                "profile_id": None,
                "profile_revision_id": None,
            }
            semantic_revision_text = binding.get("semantic_profile_revision_id")
            semantic_profile_text = binding.get("semantic_profile_id")
            if (semantic_revision_text is None) != (semantic_profile_text is None):
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
                )
            if semantic_revision_text is not None:
                semantic_profile, semantic_revision = semantic_profiles[
                    UUID(semantic_revision_text)
                ]
                if (
                    str(semantic_profile.id) != semantic_profile_text
                    or semantic_profile.beneficiary_id != beneficiary.id
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
                semantic_state = {
                    "state": semantic_revision.overall_status,
                    "profile_id": str(semantic_profile.id),
                    "profile_revision_id": str(semantic_revision.id),
                }

            company_pair = latest_research.get(revision.id)
            company_state = (
                {
                    "state": "missing",
                    "company_research_id": None,
                    "company_research_revision_id": None,
                    "reason": (
                        "no_supported_handoff_pool"
                        if output.accepted_candidate_pool_revision_id is None
                        else "exact_company_research_not_found"
                    ),
                }
                if company_pair is None
                else {
                    "state": company_pair[1].conclusion_status,
                    "workflow_state": company_pair[1].workflow_state,
                    "company_research_id": str(company_pair[0].id),
                    "company_research_revision_id": str(company_pair[1].id),
                    "reason": None,
                }
            )
            reasons = list(binding.get("readiness_reason_codes", []))
            if semantic_state["state"] == "missing":
                reasons.append("typed_semantics_missing")
            if company_state["state"] == "missing":
                reasons.append("company_research_missing")
            reasons.extend(
                [
                    "investment_candidate_not_created_by_acceptance",
                    "canonical_price_not_evaluated_by_acceptance",
                    "structured_valuation_not_evaluated_by_acceptance",
                ]
            )
            members.append(
                {
                    "sequence": expected_sequence,
                    "reviewed_candidate_revision_id": str(candidate.id),
                    "company_label_original": candidate.company_label_original,
                    "source_kind": candidate.source_kind,
                    "reviewed_proposal_exposure": candidate.proposed_exposure_type,
                    "beneficiary_id": str(beneficiary.id),
                    "beneficiary_revision_id": str(revision.id),
                    "source": beneficiary.source,
                    "stock_code": beneficiary.stock_code,
                    "stock_basic_record_id": revision.stock_basic_record_id,
                    "legacy_beneficiary_kind": revision.beneficiary_kind,
                    "assessment_status": revision.assessment_status,
                    "rationale_summary": revision.rationale_summary,
                    "semantic": semantic_state,
                    "included_in_supported_handoff": included,
                    "supported_handoff_reason": binding.get(
                        "supported_handoff_reason"
                    ),
                    "readiness_note": binding.get("readiness_note"),
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
                    "readiness_reason_codes": sorted(set(reasons)),
                    "ready_for_later_explicit_handoff": (
                        included
                        and semantic_state["state"] != "missing"
                        and company_state["state"] != "missing"
                    ),
                }
            )

        actual_pool_members = sorted(
            (membership.beneficiary_revision_id for membership in pool_members),
            key=str,
        )
        if supported_revision_ids:
            if (
                pool is None
                or pool_revision is None
                or pool.case_id != research_case.id
                or pool.map_id != industry_map.id
                or pool_revision.selected_map_revision_id != map_revision.id
                or actual_pool_members != sorted(supported_revision_ids, key=str)
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

        owner_plan = accepted_graph.get("owner_acceptance_plan")
        if not isinstance(owner_plan, dict):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )
        supported_members = [
            item for item in members if item["included_in_supported_handoff"]
        ]
        draft_or_disputed_count = sum(
            item["assessment_status"] in {"draft", "disputed"} for item in members
        )
        semantic_covered_count = sum(
            item["semantic"]["state"] != "missing" for item in members
        )
        company_ready_count = sum(
            item["company_research"]["state"] != "missing" for item in members
        )
        largest_gap = "暂无"
        if company_ready_count < len(members):
            largest_gap = "部分成员尚未建立 Company Research"
        elif semantic_covered_count < len(members):
            largest_gap = "部分成员尚未绑定类型化语义"
        return {
            "session_id": str(session_id),
            "reviewed_session_revision_id": str(reviewed.id),
            "accepted_session_revision_id": str(accepted.id),
            "output_link_id": str(output.output_link_id),
            "output_link_revision_id": str(output.id),
            "owner_transaction_id": output.owner_transaction_id,
            "title": owner_plan.get("output_title") or _display_title(accepted),
            "scope": owner_plan.get("output_scope") or map_revision.scope,
            "status": "accepted_outputs_linked",
            "accepted_at_utc": stored_utc(output.recorded_at_utc).isoformat(),
            "information_cutoff_date": output.information_cutoff_date.isoformat(),
            "as_of_cutoff": as_of_cutoff.isoformat(),
            "as_of_recorded_at_utc": recorded_boundary.isoformat(),
            "coverage_state": output.coverage_state,
            "complete_member_count": len(members),
            "supported_handoff_count": len(supported_members),
            "candidate_pool_mode": (
                owner_plan.get("candidate_pool_operation", {}).get("mode")
            ),
            "accepted_candidate_pool_revision_id": (
                None
                if pool_revision is None
                else str(pool_revision.id)
            ),
            "draft_or_disputed_count": draft_or_disputed_count,
            "semantic_covered_count": semantic_covered_count,
            "company_research_ready_count": company_ready_count,
            "largest_missing_prerequisite": largest_gap,
            "members": members,
            "supported_handoff_members": supported_members,
            "zero_supported_notice": (
                "研究成果已经接受，但当前没有成员符合 supported 后续研究池。"
                if not supported_members
                else None
            ),
            "facts": [
                {"label": "完整成员", "value": len(members)},
                {"label": "supported 后续研究", "value": len(supported_members)},
                {
                    "label": "草稿或争议成员",
                    "value": draft_or_disputed_count,
                },
                {
                    "label": "类型化语义覆盖",
                    "value": f"{semantic_covered_count}/{len(members)}",
                },
                {
                    "label": "Company Research 已存在",
                    "value": f"{company_ready_count}/{len(members)}",
                },
                {"label": "最大准备度缺口", "value": largest_gap},
                {"label": "研究用途", "value": "不构成投资建议"},
            ],
            "primary_action": {
                "kind": "history",
                "label": "返回研究历史",
                "path": "/industry-analysis",
            },
            "technical_details": {
                "output_contract_version": output.output_contract_version,
                "reviewed_plan_fingerprint_sha256": (
                    output.reviewed_plan_fingerprint_sha256
                ),
                "owner_acceptance_plan_fingerprint_sha256": (
                    output.acceptance_plan_fingerprint_sha256
                ),
                "industry_map_id": str(industry_map.id),
                "industry_map_revision_id": str(map_revision.id),
                "research_case_id": str(research_case.id),
            },
        }

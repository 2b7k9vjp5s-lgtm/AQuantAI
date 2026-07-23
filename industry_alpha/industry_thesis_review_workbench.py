"""Non-persistent exact review/result projections for Workbench UI Phase 1D."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateIdentity,
    IndustryThesisCandidateRevision,
    IndustryThesisSessionIdentity,
)
from industry_alpha.industry_thesis_query import IndustryThesisQueryService
from industry_alpha.industry_thesis_review import IndustryThesisReviewedPlanQueryService
from industry_alpha.industry_thesis_rules import (
    IndustryThesisError,
    IndustryThesisNotFound,
    stored_utc,
)

_REVIEWABLE_WORKFLOW_STATES = {"candidate_build_ready", "awaiting_review"}
_DECISION_LABELS = {
    "selected_for_acceptance": "纳入后续研究",
    "rejected_by_user": "暂不纳入",
    "unresolved": "待确认",
}
_EXPOSURE_LABELS = {
    "direct": "直接受益",
    "conditional": "条件性受益",
    "indirect": "间接受益",
    "conceptual": "概念相关",
    "unknown": "待确认",
}
_SOURCE_LABELS = {
    "accepted_local_mapping": "已接受本地映射",
    "existing_industry_map_revision": "冻结 Stage 1 候选池",
    "user_seed": "明确公司种子",
    "ai_draft": "AI 草稿",
}


def _display_title(revision: dict[str, Any]) -> str:
    reviewed = str(revision.get("thesis_title_reviewed") or "").strip()
    if reviewed:
        return reviewed
    original = str(revision.get("thesis_text_original") or "").strip()
    first_line = next((line.strip() for line in original.splitlines() if line.strip()), "未命名研究")
    return first_line if len(first_line) <= 80 else f"{first_line[:77]}…"


def _exact_identity(candidate: dict[str, Any]) -> bool:
    stock_id = candidate.get("proposed_stock_basic_record_id")
    instrument_id = candidate.get("proposed_listed_instrument_id")
    return (
        candidate.get("identity_state") == "exact_accepted_identity"
        and ((stock_id is None) != (instrument_id is None))
    )


def _presentation_row(candidate: dict[str, Any]) -> dict[str, Any]:
    rationale = candidate.get("rationale")
    uncertainty = candidate.get("uncertainty")
    source_reference = candidate.get("source_reference")
    return {
        **candidate,
        "source_label": _SOURCE_LABELS.get(
            str(candidate.get("source_kind")), str(candidate.get("source_kind"))
        ),
        "decision_label": _DECISION_LABELS.get(
            str(candidate.get("review_state")), str(candidate.get("review_state"))
        ),
        "exposure_label": _EXPOSURE_LABELS.get(
            str(candidate.get("proposed_exposure_type")),
            str(candidate.get("proposed_exposure_type")),
        ),
        "can_select_for_acceptance": _exact_identity(candidate),
        "rationale": rationale if isinstance(rationale, dict) else {},
        "uncertainty": uncertainty if isinstance(uncertainty, dict) else {},
        "source_reference": (
            source_reference if isinstance(source_reference, dict) else {}
        ),
    }


class IndustryThesisReviewWorkbenchQueryService:
    """Compose exact Phase 1D review/result views without owning state."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._query = IndustryThesisQueryService(session)

    def get_review_view(
        self,
        *,
        session_id: UUID,
        session_revision_id: UUID,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        revision = self._query.get_session_revision(
            session_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=as_of_recorded_at_utc,
        )
        if revision["session_id"] != str(session_id):
            raise IndustryThesisNotFound(
                "industry_thesis_session_revision_not_found",
                "exact route-owned session revision was not found",
            )
        identity = self._session.get(IndustryThesisSessionIdentity, session_id)
        if identity is None:
            raise IndustryThesisNotFound(
                "industry_thesis_session_not_found",
                "exact industry-thesis session was not found",
            )
        if identity.latest_revision_number != revision["revision_number"]:
            raise IndustryThesisError(
                "industry_thesis_revision_conflict",
                "candidate review requires the exact latest session revision",
            )
        if revision["workflow_state"] not in _REVIEWABLE_WORKFLOW_STATES:
            raise IndustryThesisError(
                "industry_thesis_review_invalid",
                "exact session revision is not ready for candidate review",
            )

        universe = self._query.list_candidate_revisions(
            session_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=as_of_recorded_at_utc,
        )
        identities = list(
            self._session.scalars(
                select(IndustryThesisCandidateIdentity)
                .where(IndustryThesisCandidateIdentity.session_id == session_id)
                .order_by(IndustryThesisCandidateIdentity.candidate_key)
            )
        )
        by_id = {str(item.id): item for item in identities}
        if len(by_id) != universe["candidate_count"]:
            raise IndustryThesisError(
                "industry_thesis_review_stale_universe",
                "complete latest candidate universe is not bound to the exact session revision",
            )

        rows: list[dict[str, Any]] = []
        for candidate in universe["candidates"]:
            candidate_identity = by_id.get(candidate["candidate_id"])
            if (
                candidate_identity is None
                or candidate_identity.latest_revision_number
                != candidate["revision_number"]
                or candidate["session_revision_id"] != str(session_revision_id)
                or candidate["review_state"] != "proposed"
            ):
                raise IndustryThesisError(
                    "industry_thesis_review_stale_universe",
                    "candidate review requires every exact latest proposed candidate",
                )
            rows.append(_presentation_row(candidate))

        return {
            "session_id": str(session_id),
            "session_revision_id": str(session_revision_id),
            "session_revision_number": revision["revision_number"],
            "thesis_title": _display_title(revision),
            "thesis_text_original": revision["thesis_text_original"],
            "workflow_state": revision["workflow_state"],
            "coverage_state": revision["coverage_state"],
            "information_cutoff_date": revision["information_cutoff_date"],
            "recorded_at_utc": revision["recorded_at_utc"],
            "as_of_cutoff": as_of_cutoff.isoformat(),
            "as_of_recorded_at_utc": stored_utc(as_of_recorded_at_utc).isoformat(),
            "candidate_count": len(rows),
            "decided_count": 0,
            "undecided_count": len(rows),
            "review_ready": bool(rows),
            "decision_options": [
                {"value": value, "label": label}
                for value, label in _DECISION_LABELS.items()
            ],
            "exposure_options": [
                {"value": value, "label": label}
                for value, label in _EXPOSURE_LABELS.items()
                if value != "unknown"
            ],
            "candidates": rows,
            "notices": {
                "complete_universe_required": True,
                "selected_is_not_accepted_membership": True,
                "owner_acceptance_not_performed": True,
            },
        }

    def get_result_view(
        self,
        *,
        session_id: UUID,
        reviewed_session_revision_id: UUID,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        reviewed = IndustryThesisReviewedPlanQueryService(
            self._session
        ).get_reviewed_plan(
            reviewed_session_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=as_of_recorded_at_utc,
        )
        if reviewed["session_id"] != str(session_id):
            raise IndustryThesisNotFound(
                "industry_thesis_session_revision_not_found",
                "exact route-owned reviewed session revision was not found",
            )
        revision = self._query.get_session_revision(
            reviewed_session_revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=as_of_recorded_at_utc,
        )
        plan = reviewed["acceptance_plan"]

        selected_ids = [
            str(item["candidate_revision_id"])
            for item in plan.get("selected_candidates", [])
        ]
        unresolved_ids = [
            str(value) for value in plan.get("unresolved_candidate_revision_ids", [])
        ]
        rejected_ids = [
            str(value) for value in plan.get("rejected_candidate_revision_ids", [])
        ]
        ordered_ids = selected_ids + unresolved_ids + rejected_ids
        if not ordered_ids or len(ordered_ids) != len(set(ordered_ids)):
            raise IndustryThesisError(
                "industry_thesis_graph_incomplete",
                "reviewed plan does not contain one complete unique candidate universe",
            )

        rows_by_id: dict[str, dict[str, Any]] = {}
        for value in ordered_ids:
            candidate = self._query.get_candidate_revision(
                UUID(value),
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
            if (
                candidate["session_id"] != str(session_id)
                or candidate["session_revision_id"]
                != str(reviewed_session_revision_id)
            ):
                raise IndustryThesisError(
                    "industry_thesis_graph_incomplete",
                    "reviewed candidate is not bound to the exact reviewed session revision",
                )
            rows_by_id[value] = _presentation_row(candidate)

        def group(values: list[str], expected: str) -> list[dict[str, Any]]:
            result: list[dict[str, Any]] = []
            for value in values:
                row = rows_by_id[value]
                if row["review_state"] != expected:
                    raise IndustryThesisError(
                        "industry_thesis_graph_incomplete",
                        "reviewed candidate state does not match the deterministic plan",
                    )
                result.append(row)
            return result

        selected = group(selected_ids, "selected_for_acceptance")
        unresolved = group(unresolved_ids, "unresolved")
        rejected = group(rejected_ids, "rejected_by_user")
        latest_candidate_recorded_at = max(
            stored_utc(datetime.fromisoformat(row["recorded_at_utc"]))
            for row in rows_by_id.values()
        )

        return {
            "session_id": str(session_id),
            "reviewed_session_revision_id": str(reviewed_session_revision_id),
            "reviewed_session_revision_number": revision["revision_number"],
            "thesis_title": _display_title(revision),
            "thesis_text_original": revision["thesis_text_original"],
            "workflow_state": revision["workflow_state"],
            "coverage_state": revision["coverage_state"],
            "information_cutoff_date": revision["information_cutoff_date"],
            "session_recorded_at_utc": revision["recorded_at_utc"],
            "complete_result_recorded_at_utc": latest_candidate_recorded_at.isoformat(),
            "as_of_cutoff": as_of_cutoff.isoformat(),
            "as_of_recorded_at_utc": stored_utc(as_of_recorded_at_utc).isoformat(),
            "candidate_count": len(ordered_ids),
            "selected_count": len(selected),
            "unresolved_count": len(unresolved),
            "rejected_count": len(rejected),
            "selected_candidates": selected,
            "unresolved_candidates": unresolved,
            "rejected_candidates": rejected,
            "candidate_sources": plan.get("candidate_sources", []),
            "acceptance_plan_version": plan.get("acceptance_plan_version"),
            "acceptance_plan_fingerprint_sha256": reviewed[
                "acceptance_plan_fingerprint_sha256"
            ],
            "ownership_notice": (
                "审阅计划已生成，但尚未写入正式产业地图、Stage 1 受益公司或投资候选快照。"
            ),
            "notices": {
                "selected_is_not_accepted_membership": True,
                "owner_acceptance_not_performed": True,
                "output_links_not_written": True,
            },
        }

"""Exact Investment Candidate snapshot options and optional overlay."""

from __future__ import annotations

from collections import Counter
from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from industry_alpha.investment_candidate_models import (
    CANDIDATE_STATUSES,
    InvestmentCandidateMember,
    InvestmentCandidateSnapshot,
    InvestmentCandidateSnapshotRevision,
)
from industry_alpha.investment_candidate_query import InvestmentCandidateQueryService
from industry_alpha.investment_candidate_rules import (
    InvestmentCandidateError,
    InvestmentCandidateNotFound,
    PURPOSE_CODE,
    RULE_VERSION,
)
from industry_alpha.industry_research_result_rules import stored_utc


class CandidateOverlayReader:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._exact_reader = InvestmentCandidateQueryService(session)

    def list_options(
        self,
        candidate_pool_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
        limit: int,
    ) -> dict[str, Any]:
        rows = list(
            self._session.execute(
                select(
                    InvestmentCandidateSnapshotRevision,
                    InvestmentCandidateSnapshot,
                )
                .join(
                    InvestmentCandidateSnapshot,
                    InvestmentCandidateSnapshot.id
                    == InvestmentCandidateSnapshotRevision.snapshot_id,
                )
                .where(
                    InvestmentCandidateSnapshotRevision.candidate_pool_revision_id
                    == candidate_pool_revision_id,
                    InvestmentCandidateSnapshotRevision.purpose_code == PURPOSE_CODE,
                    InvestmentCandidateSnapshotRevision.rule_version == RULE_VERSION,
                    InvestmentCandidateSnapshotRevision.information_cutoff_date
                    <= as_of_cutoff,
                    InvestmentCandidateSnapshotRevision.recorded_at_utc
                    <= as_of_recorded_at_utc,
                )
                .order_by(
                    InvestmentCandidateSnapshotRevision.recorded_at_utc.desc(),
                    InvestmentCandidateSnapshotRevision.information_cutoff_date.desc(),
                    InvestmentCandidateSnapshotRevision.revision_no.desc(),
                    InvestmentCandidateSnapshotRevision.id.asc(),
                )
                .limit(limit + 1)
            )
        )
        has_more = len(rows) > limit
        rows = rows[:limit]
        revision_ids = [revision.id for revision, _snapshot in rows]
        members = (
            list(
                self._session.scalars(
                    select(InvestmentCandidateMember).where(
                        InvestmentCandidateMember.snapshot_revision_id.in_(
                            revision_ids
                        )
                    )
                )
            )
            if revision_ids
            else []
        )
        status_by_revision = {
            revision_id: Counter() for revision_id in revision_ids
        }
        count_by_revision: Counter[UUID] = Counter()
        for member in members:
            status_by_revision[member.snapshot_revision_id][
                member.candidate_status
            ] += 1
            count_by_revision[member.snapshot_revision_id] += 1
        options = []
        for revision, snapshot in rows:
            counts = status_by_revision[revision.id]
            options.append(
                {
                    "snapshot_id": str(snapshot.id),
                    "snapshot_revision_id": str(revision.id),
                    "revision_no": revision.revision_no,
                    "snapshot_key": snapshot.snapshot_key,
                    "candidate_pool_revision_id": str(
                        revision.candidate_pool_revision_id
                    ),
                    "purpose_code": revision.purpose_code,
                    "rule_version": revision.rule_version,
                    "information_cutoff_date": (
                        revision.information_cutoff_date.isoformat()
                    ),
                    "recorded_at_utc": stored_utc(
                        revision.recorded_at_utc
                    ).isoformat(),
                    "recorded_by": revision.recorded_by,
                    "member_count": count_by_revision[revision.id],
                    "candidate_status_counts": {
                        status: counts[status]
                        for status in CANDIDATE_STATUSES
                        if counts[status]
                    },
                }
            )
        return {"options": options, "has_more": has_more}

    def resolve(
        self,
        *,
        accepted_pool_revision_id: UUID | None,
        accepted_beneficiary_revision_ids: set[UUID],
        selected_snapshot_revision_id: UUID | None,
        options: list[dict[str, Any]],
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        if accepted_pool_revision_id is None:
            return {
                "state": "unavailable_zero_supported",
                "snapshot_revision_id": (
                    None
                    if selected_snapshot_revision_id is None
                    else str(selected_snapshot_revision_id)
                ),
                "snapshot": None,
                "blocked_reason": "accepted_output_has_no_supported_pool",
            }
        if selected_snapshot_revision_id is None:
            return {
                "state": "not_selected" if options else "unavailable",
                "snapshot_revision_id": None,
                "snapshot": None,
                "blocked_reason": (
                    None if options else "no_exact_snapshot_for_accepted_pool"
                ),
            }
        try:
            snapshot = self._exact_reader.get_snapshot_revision(
                selected_snapshot_revision_id,
                as_of_cutoff=as_of_cutoff,
                as_of_recorded_at_utc=as_of_recorded_at_utc,
            )
        except InvestmentCandidateNotFound as exc:
            return {
                "state": "blocked_candidate_snapshot_unavailable",
                "snapshot_revision_id": str(selected_snapshot_revision_id),
                "snapshot": None,
                "blocked_reason": exc.code,
            }
        except InvestmentCandidateError as exc:
            return {
                "state": "blocked_candidate_graph_incomplete",
                "snapshot_revision_id": str(selected_snapshot_revision_id),
                "snapshot": None,
                "blocked_reason": exc.code,
            }
        if snapshot["purpose_code"] != PURPOSE_CODE or snapshot[
            "rule_version"
        ] != RULE_VERSION:
            return {
                "state": "blocked_candidate_contract_mismatch",
                "snapshot_revision_id": str(selected_snapshot_revision_id),
                "snapshot": None,
                "blocked_reason": "candidate_snapshot_contract_mismatch",
            }
        if UUID(snapshot["candidate_pool_revision_id"]) != accepted_pool_revision_id:
            return {
                "state": "blocked_exact_pool_mismatch",
                "snapshot_revision_id": str(selected_snapshot_revision_id),
                "snapshot": None,
                "blocked_reason": "exact_pool_mismatch",
            }
        snapshot_revision_ids = {
            UUID(item["beneficiary_revision_id"]) for item in snapshot["members"]
        }
        if not snapshot_revision_ids.issubset(accepted_beneficiary_revision_ids):
            return {
                "state": "blocked_candidate_graph_incomplete",
                "snapshot_revision_id": str(selected_snapshot_revision_id),
                "snapshot": None,
                "blocked_reason": "candidate_member_outside_accepted_result",
            }
        return {
            "state": "selected",
            "snapshot_revision_id": str(selected_snapshot_revision_id),
            "snapshot": snapshot,
            "blocked_reason": None,
        }

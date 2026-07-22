"""Exact-ID, dual-as-of reads for offline Industry Thesis Orchestration v1."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateIdentity,
    IndustryThesisCandidateRevision,
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_rules import (
    IndustryThesisError,
    IndustryThesisNotFound,
    SOURCE_PRECEDENCE,
    json_value,
    stored_utc,
)


def _validate_recorded_boundary(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "as_of_recorded_at_utc must be explicit UTC",
        )
    return value.astimezone(timezone.utc)


def _visible(row: Any, cutoff: date, recorded_at: datetime) -> None:
    if row.information_cutoff_date > cutoff:
        raise IndustryThesisNotFound(
            "industry_thesis_not_visible",
            "record is outside the requested information cutoff",
        )
    if stored_utc(row.recorded_at_utc) > recorded_at:
        raise IndustryThesisNotFound(
            "industry_thesis_not_visible",
            "record is outside the requested recorded-time boundary",
        )


def _session_revision_value(revision: IndustryThesisSessionRevision) -> dict[str, Any]:
    return {
        "session_revision_id": str(revision.id),
        "session_id": str(revision.session_id),
        "revision_number": revision.revision_number,
        "thesis_text_original": revision.thesis_text_original,
        "thesis_title_reviewed": revision.thesis_title_reviewed,
        "driver_type": revision.driver_type,
        "analysis_horizon_kind": revision.analysis_horizon_kind,
        "analysis_start_date": (
            None if revision.analysis_start_date is None else revision.analysis_start_date.isoformat()
        ),
        "analysis_end_date": (
            None if revision.analysis_end_date is None else revision.analysis_end_date.isoformat()
        ),
        "market_scope": json_value(revision.market_scope_json, "market_scope"),
        "chain_boundary": json_value(revision.chain_boundary_json, "chain_boundary"),
        "exclusions": json_value(revision.exclusions_json, "exclusions"),
        "seed_companies": json_value(revision.seed_companies_json, "seed_companies"),
        "seed_products": json_value(revision.seed_products_json, "seed_products"),
        "seed_technologies": json_value(revision.seed_technologies_json, "seed_technologies"),
        "seed_bottlenecks": json_value(revision.seed_bottlenecks_json, "seed_bottlenecks"),
        "draft_graph": json_value(revision.draft_graph_json, "draft_graph"),
        "coverage_state": revision.coverage_state,
        "workflow_state": revision.workflow_state,
        "information_cutoff_date": revision.information_cutoff_date.isoformat(),
        "recorded_at_utc": stored_utc(revision.recorded_at_utc).isoformat(),
        "input_fingerprint_sha256": revision.input_fingerprint_sha256,
        "supersedes_revision_id": (
            None if revision.supersedes_revision_id is None else str(revision.supersedes_revision_id)
        ),
        "revision_note": revision.revision_note,
    }


def _candidate_revision_value(
    identity: IndustryThesisCandidateIdentity,
    revision: IndustryThesisCandidateRevision,
) -> dict[str, Any]:
    return {
        "candidate_id": str(identity.id),
        "candidate_revision_id": str(revision.id),
        "session_id": str(identity.session_id),
        "session_revision_id": str(revision.session_revision_id),
        "candidate_key": identity.candidate_key,
        "revision_number": revision.revision_number,
        "source_kind": revision.source_kind,
        "source_reference": json_value(revision.source_reference_json, "source_reference"),
        "proposed_stock_basic_record_id": revision.proposed_stock_basic_record_id,
        "proposed_listed_instrument_id": (
            None
            if revision.proposed_listed_instrument_id is None
            else str(revision.proposed_listed_instrument_id)
        ),
        "company_label_original": revision.company_label_original,
        "product_or_service_fit": revision.product_or_service_fit,
        "industry_position": revision.industry_position,
        "benefit_path_text": revision.benefit_path_text,
        "proposed_exposure_type": revision.proposed_exposure_type,
        "proposal_confidence": revision.proposal_confidence,
        "identity_state": revision.identity_state,
        "review_state": revision.review_state,
        "rationale": json_value(revision.rationale_json, "rationale"),
        "uncertainty": json_value(revision.uncertainty_json, "uncertainty"),
        "manifest_fingerprint_sha256": revision.manifest_fingerprint_sha256,
        "information_cutoff_date": revision.information_cutoff_date.isoformat(),
        "recorded_at_utc": stored_utc(revision.recorded_at_utc).isoformat(),
        "supersedes_revision_id": (
            None if revision.supersedes_revision_id is None else str(revision.supersedes_revision_id)
        ),
    }


class IndustryThesisQueryService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_session(
        self,
        session_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        recorded_boundary = _validate_recorded_boundary(as_of_recorded_at_utc)
        identity = self._session.get(IndustryThesisSessionIdentity, session_id)
        if identity is None or stored_utc(identity.created_recorded_utc) > recorded_boundary:
            raise IndustryThesisNotFound(
                "industry_thesis_session_not_found",
                "exact industry-thesis session was not found",
            )
        revisions = list(
            self._session.scalars(
                select(IndustryThesisSessionRevision)
                .where(
                    IndustryThesisSessionRevision.session_id == identity.id,
                    IndustryThesisSessionRevision.information_cutoff_date <= as_of_cutoff,
                    IndustryThesisSessionRevision.recorded_at_utc <= recorded_boundary,
                )
                .order_by(IndustryThesisSessionRevision.revision_number)
            )
        )
        return {
            "session_id": str(identity.id),
            "created_recorded_utc": stored_utc(identity.created_recorded_utc).isoformat(),
            "created_by_kind": identity.created_by_kind,
            "state": identity.state,
            "visible_latest_revision_number": (
                None if not revisions else revisions[-1].revision_number
            ),
            "visible_revision_count": len(revisions),
            "visible_revisions": [_session_revision_value(revision) for revision in revisions],
        }

    def get_session_revision(
        self,
        session_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        recorded_boundary = _validate_recorded_boundary(as_of_recorded_at_utc)
        revision = self._session.get(IndustryThesisSessionRevision, session_revision_id)
        if revision is None:
            raise IndustryThesisNotFound(
                "industry_thesis_session_revision_not_found",
                "exact session revision was not found",
            )
        _visible(revision, as_of_cutoff, recorded_boundary)
        return _session_revision_value(revision)

    def get_candidate_revision(
        self,
        candidate_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        recorded_boundary = _validate_recorded_boundary(as_of_recorded_at_utc)
        revision = self._session.get(IndustryThesisCandidateRevision, candidate_revision_id)
        if revision is None:
            raise IndustryThesisNotFound(
                "industry_thesis_candidate_revision_not_found",
                "exact candidate revision was not found",
            )
        _visible(revision, as_of_cutoff, recorded_boundary)
        identity = self._session.get(IndustryThesisCandidateIdentity, revision.candidate_id)
        if identity is None or stored_utc(identity.created_recorded_utc) > stored_utc(revision.recorded_at_utc):
            raise IndustryThesisError(
                "industry_thesis_graph_incomplete",
                "candidate identity graph is incomplete",
            )
        return _candidate_revision_value(identity, revision)

    def list_candidate_revisions(
        self,
        session_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        recorded_boundary = _validate_recorded_boundary(as_of_recorded_at_utc)
        session_revision = self._session.get(
            IndustryThesisSessionRevision,
            session_revision_id,
        )
        if session_revision is None:
            raise IndustryThesisNotFound(
                "industry_thesis_session_revision_not_found",
                "exact session revision was not found",
            )
        _visible(session_revision, as_of_cutoff, recorded_boundary)
        rows = list(
            self._session.execute(
                select(IndustryThesisCandidateIdentity, IndustryThesisCandidateRevision)
                .join(
                    IndustryThesisCandidateRevision,
                    IndustryThesisCandidateRevision.candidate_id
                    == IndustryThesisCandidateIdentity.id,
                )
                .where(
                    IndustryThesisCandidateRevision.session_revision_id == session_revision.id,
                    IndustryThesisCandidateRevision.information_cutoff_date <= as_of_cutoff,
                    IndustryThesisCandidateRevision.recorded_at_utc <= recorded_boundary,
                )
            ).all()
        )
        for identity, revision in rows:
            if stored_utc(identity.created_recorded_utc) > stored_utc(revision.recorded_at_utc):
                raise IndustryThesisError(
                    "industry_thesis_graph_incomplete",
                    "candidate identity chronology is incomplete",
                )
        rows.sort(
            key=lambda pair: (
                SOURCE_PRECEDENCE[pair[1].source_kind],
                pair[0].candidate_key,
                pair[1].revision_number,
                str(pair[1].id),
            )
        )
        candidates = [
            _candidate_revision_value(identity, revision)
            for identity, revision in rows
        ]
        return {
            "session_id": str(session_revision.session_id),
            "session_revision_id": str(session_revision.id),
            "coverage_state": session_revision.coverage_state,
            "information_cutoff_date": session_revision.information_cutoff_date.isoformat(),
            "candidate_count": len(candidates),
            "candidates": candidates,
        }

"""Offline proposal review and deterministic acceptance-plan preview for Industry Thesis v1."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from threading import Lock, RLock
from typing import Any, Callable
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price_models import ListedInstrument
from backend.database.models import StockBasicRecord
from industry_alpha.industry_thesis_models import (
    PROPOSED_EXPOSURE_TYPES,
    IndustryThesisCandidateIdentity,
    IndustryThesisCandidateRevision,
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_rules import (
    IndustryThesisError,
    IndustryThesisNotFound,
    bounded_text,
    canonical_json_text,
    enum_text,
    fingerprint,
    json_value,
    normalize_session_payload,
    parse_integer,
    parse_uuid,
    require_keys,
    session_revision_to_input,
    stored_utc,
    utc_now,
)

ACCEPTANCE_PLAN_VERSION = "aquantai.industry-thesis-acceptance-plan.v1"
REVIEW_DECISIONS = (
    "selected_for_acceptance",
    "rejected_by_user",
    "unresolved",
)
_REVIEWABLE_WORKFLOW_STATES = ("candidate_build_ready", "awaiting_review")
_LOCK_GUARD = Lock()
_LOCKS: dict[str, RLock] = {}


def _lock(key: str) -> RLock:
    with _LOCK_GUARD:
        return _LOCKS.setdefault(key, RLock())


def _next_utc(value: datetime) -> datetime:
    return stored_utc(value) + timedelta(microseconds=1)


def _validate_recorded_boundary(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "as_of_recorded_at_utc must be explicit UTC",
        )
    return value.astimezone(timezone.utc)


def _normalize_review(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "session_revision_id",
        "expected_session_latest_revision_number",
        "acceptance_plan_version",
        "decisions",
        "revision_note",
    }
    require_keys(raw, allowed, allowed)
    version = bounded_text(raw["acceptance_plan_version"], "acceptance_plan_version", 128)
    if version != ACCEPTANCE_PLAN_VERSION:
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "unsupported acceptance-plan version",
        )
    decisions_raw = raw["decisions"]
    if not isinstance(decisions_raw, list) or not decisions_raw:
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "decisions must be a non-empty list",
        )
    decisions = [_normalize_decision(item, index) for index, item in enumerate(decisions_raw)]
    revision_ids = [item["candidate_revision_id"] for item in decisions]
    if len(revision_ids) != len(set(revision_ids)):
        raise IndustryThesisError(
            "industry_thesis_duplicate_review",
            "one review request cannot contain the same candidate revision twice",
        )
    return {
        "session_revision_id": parse_uuid(raw["session_revision_id"], "session_revision_id"),
        "expected_session_latest_revision_number": parse_integer(
            raw["expected_session_latest_revision_number"],
            "expected_session_latest_revision_number",
            minimum=1,
        ),
        "acceptance_plan_version": version,
        "decisions": decisions,
        "revision_note": bounded_text(raw["revision_note"], "revision_note", 1000),
    }


def _normalize_decision(raw: Any, index: int) -> dict[str, Any]:
    allowed = {
        "candidate_revision_id",
        "expected_latest_revision_number",
        "decision",
        "final_proposed_exposure_type",
        "rationale",
        "uncertainty",
    }
    required = allowed - {"final_proposed_exposure_type"}
    require_keys(raw, allowed, required, field=f"decisions[{index}]")
    decision = enum_text(raw["decision"], f"decisions[{index}].decision", REVIEW_DECISIONS)
    exposure = None
    if raw.get("final_proposed_exposure_type") is not None:
        exposure = enum_text(
            raw["final_proposed_exposure_type"],
            f"decisions[{index}].final_proposed_exposure_type",
            PROPOSED_EXPOSURE_TYPES,
        )
    if decision == "selected_for_acceptance" and (exposure is None or exposure == "unknown"):
        raise IndustryThesisError(
            "industry_thesis_review_invalid",
            "selected candidates require an explicit non-unknown final exposure type",
        )
    if decision != "selected_for_acceptance" and exposure is not None:
        raise IndustryThesisError(
            "industry_thesis_review_invalid",
            "only selected candidates may override the final exposure type",
        )
    rationale_json = canonical_json_text(raw["rationale"], "review rationale")
    uncertainty_json = canonical_json_text(raw["uncertainty"], "review uncertainty")
    rationale_value = json_value(rationale_json, "review rationale")
    uncertainty_value = json_value(uncertainty_json, "review uncertainty")
    if not isinstance(rationale_value, dict) or not rationale_value:
        raise IndustryThesisError(
            "industry_thesis_review_invalid",
            "review rationale must be a non-empty JSON object",
        )
    uncertainty_state = (
        uncertainty_value.get("state")
        if isinstance(uncertainty_value, dict)
        else None
    )
    if (
        not isinstance(uncertainty_value, dict)
        or not uncertainty_value
        or not isinstance(uncertainty_state, str)
        or not uncertainty_state.strip()
    ):
        raise IndustryThesisError(
            "industry_thesis_review_invalid",
            "review uncertainty must be a non-empty object with an explicit state",
        )
    return {
        "candidate_revision_id": parse_uuid(
            raw["candidate_revision_id"],
            f"decisions[{index}].candidate_revision_id",
        ),
        "expected_latest_revision_number": parse_integer(
            raw["expected_latest_revision_number"],
            f"decisions[{index}].expected_latest_revision_number",
            minimum=1,
        ),
        "decision": decision,
        "final_proposed_exposure_type": exposure,
        "rationale_json": rationale_json,
        "uncertainty_json": uncertainty_json,
    }


class IndustryThesisProposalReviewService:
    """Append reviewed candidate revisions and freeze a deterministic plan preview."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock

    def review_candidates(
        self,
        raw: dict[str, Any],
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        command = _normalize_review(raw)
        try:
            with _lock(str(command["session_revision_id"])):
                if dry_run:
                    with self._session_factory() as session:
                        return self._review(session, command, dry_run=True)
                with self._session_factory.begin() as session:
                    return self._review(session, command, dry_run=False)
        except IntegrityError as exc:
            raise IndustryThesisError(
                "industry_thesis_revision_conflict",
                "proposal review conflicts with accepted local history",
            ) from exc

    def _review(
        self,
        session: Session,
        command: dict[str, Any],
        *,
        dry_run: bool,
    ) -> dict[str, Any]:
        source_revision = session.scalar(
            select(IndustryThesisSessionRevision)
            .where(IndustryThesisSessionRevision.id == command["session_revision_id"])
            .with_for_update()
        )
        if source_revision is None:
            raise IndustryThesisError(
                "industry_thesis_session_revision_not_found",
                "exact session revision was not found",
            )
        session_identity = session.scalar(
            select(IndustryThesisSessionIdentity)
            .where(IndustryThesisSessionIdentity.id == source_revision.session_id)
            .with_for_update()
        )
        if session_identity is None:
            raise IndustryThesisError(
                "industry_thesis_graph_incomplete",
                "session identity graph is incomplete",
            )
        expected_session = command["expected_session_latest_revision_number"]
        if (
            session_identity.latest_revision_number != expected_session
            or source_revision.revision_number != expected_session
        ):
            raise IndustryThesisError(
                "industry_thesis_revision_conflict",
                "proposal review requires the exact latest session revision",
            )
        if source_revision.workflow_state not in _REVIEWABLE_WORKFLOW_STATES:
            raise IndustryThesisError(
                "industry_thesis_review_invalid",
                "session workflow is not ready for proposal review",
            )

        identities = list(
            session.scalars(
                select(IndustryThesisCandidateIdentity)
                .where(IndustryThesisCandidateIdentity.session_id == session_identity.id)
                .order_by(IndustryThesisCandidateIdentity.candidate_key)
                .with_for_update()
            )
        )
        if not identities:
            raise IndustryThesisError(
                "industry_thesis_review_invalid",
                "proposal review requires a non-empty candidate universe",
            )

        latest_rows: list[tuple[IndustryThesisCandidateIdentity, IndustryThesisCandidateRevision]] = []
        for identity in identities:
            latest = session.scalar(
                select(IndustryThesisCandidateRevision)
                .where(
                    IndustryThesisCandidateRevision.candidate_id == identity.id,
                    IndustryThesisCandidateRevision.revision_number
                    == identity.latest_revision_number,
                )
                .with_for_update()
            )
            if latest is None:
                raise IndustryThesisError(
                    "industry_thesis_graph_incomplete",
                    "candidate latest revision pointer is incomplete",
                )
            if (
                latest.session_revision_id != source_revision.id
                or latest.information_cutoff_date != source_revision.information_cutoff_date
            ):
                raise IndustryThesisError(
                    "industry_thesis_review_stale_universe",
                    "candidate universe must be rebuilt against the exact reviewed session revision",
                )
            latest_rows.append((identity, latest))

        decisions_by_revision = {
            item["candidate_revision_id"]: item for item in command["decisions"]
        }
        latest_revision_ids = {latest.id for _, latest in latest_rows}
        if set(decisions_by_revision) != latest_revision_ids:
            raise IndustryThesisError(
                "industry_thesis_review_incomplete",
                "review decisions must cover the complete exact latest candidate universe",
            )

        selected_identity_keys: set[tuple[str, str]] = set()
        prepared: list[dict[str, Any]] = []
        decision_seed_rows: list[dict[str, Any]] = []
        for identity, latest in latest_rows:
            decision = decisions_by_revision[latest.id]
            if decision["expected_latest_revision_number"] != identity.latest_revision_number:
                raise IndustryThesisError(
                    "industry_thesis_revision_conflict",
                    "expected latest candidate revision does not match",
                )
            if decision["decision"] == "selected_for_acceptance":
                self._validate_selected_identity(session, latest)
                identity_key = self._selected_identity_key(latest)
                if identity_key in selected_identity_keys:
                    raise IndustryThesisError(
                        "industry_thesis_duplicate_selected_identity",
                        "multiple selected candidates resolve to the same exact persisted identity",
                    )
                selected_identity_keys.add(identity_key)
            seed_row = {
                "candidate_id": str(identity.id),
                "candidate_key": identity.candidate_key,
                "source_candidate_revision_id": str(latest.id),
                "next_revision_number": identity.latest_revision_number + 1,
                "decision": decision["decision"],
                "final_proposed_exposure_type": decision[
                    "final_proposed_exposure_type"
                ],
                "rationale": json_value(decision["rationale_json"], "review rationale"),
                "uncertainty": json_value(
                    decision["uncertainty_json"], "review uncertainty"
                ),
            }
            decision_seed_rows.append(seed_row)
            prepared.append(
                {
                    "identity": identity,
                    "latest": latest,
                    "decision": decision,
                    "revision_number": identity.latest_revision_number + 1,
                }
            )

        decision_seed = {
            "acceptance_plan_version": command["acceptance_plan_version"],
            "session_id": str(session_identity.id),
            "source_session_revision_id": str(source_revision.id),
            "next_session_revision_number": expected_session + 1,
            "decisions": decision_seed_rows,
        }
        decision_fingerprint = fingerprint(decision_seed)
        reviewed_session_revision_id = uuid5(
            NAMESPACE_URL,
            (
                f"{ACCEPTANCE_PLAN_VERSION}:session:{session_identity.id}:"
                f"{expected_session + 1}:{decision_fingerprint}"
            ),
        )
        for item in prepared:
            identity = item["identity"]
            item["reviewed_candidate_revision_id"] = uuid5(
                NAMESPACE_URL,
                (
                    f"{ACCEPTANCE_PLAN_VERSION}:candidate:{identity.id}:"
                    f"{item['revision_number']}:{reviewed_session_revision_id}:"
                    f"{decision_fingerprint}"
                ),
            )

        clock_value = stored_utc(self._clock())
        session_recorded_at = max(
            clock_value,
            _next_utc(source_revision.recorded_at_utc),
        )
        latest_candidate_recorded = max(
            stored_utc(item["latest"].recorded_at_utc) for item in prepared
        )
        candidate_recorded_at = max(
            _next_utc(session_recorded_at),
            _next_utc(latest_candidate_recorded),
        )
        if source_revision.information_cutoff_date > session_recorded_at.date():
            raise IndustryThesisError(
                "industry_thesis_chronology_invalid",
                "information cutoff cannot exceed the system-owned recorded UTC date",
            )

        plan = self._build_plan(
            source_revision=source_revision,
            reviewed_session_revision_id=reviewed_session_revision_id,
            candidate_recorded_at=candidate_recorded_at,
            prepared=prepared,
        )
        session_payload = session_revision_to_input(source_revision)
        session_payload["workflow_state"] = "reviewed_plan_ready"
        session_payload["draft_graph"] = {
            "base_draft_graph": session_payload["draft_graph"],
            "acceptance_plan_preview": plan,
        }
        session_payload["revision_note"] = command["revision_note"]
        reviewed_session_data = normalize_session_payload(session_payload)

        result = {
            "dry_run": dry_run,
            "session_id": str(session_identity.id),
            "source_session_revision_id": str(source_revision.id),
            "reviewed_session_revision_id": str(reviewed_session_revision_id),
            "reviewed_session_revision_number": expected_session + 1,
            "workflow_state": "reviewed_plan_ready",
            "information_cutoff_date": source_revision.information_cutoff_date.isoformat(),
            "session_recorded_at_utc": session_recorded_at.isoformat(),
            "candidate_recorded_at_utc": candidate_recorded_at.isoformat(),
            "candidate_count": len(prepared),
            "acceptance_plan": plan,
            "acceptance_plan_fingerprint_sha256": plan[
                "acceptance_plan_fingerprint_sha256"
            ],
        }
        if dry_run:
            return result

        reviewed_session_revision = IndustryThesisSessionRevision(
            id=reviewed_session_revision_id,
            session_id=session_identity.id,
            revision_number=expected_session + 1,
            thesis_text_original=reviewed_session_data["thesis_text_original"],
            thesis_title_reviewed=reviewed_session_data["thesis_title_reviewed"],
            driver_type=reviewed_session_data["driver_type"],
            analysis_horizon_kind=reviewed_session_data["analysis_horizon_kind"],
            analysis_start_date=reviewed_session_data["analysis_start_date"],
            analysis_end_date=reviewed_session_data["analysis_end_date"],
            market_scope_json=reviewed_session_data["market_scope_json"],
            chain_boundary_json=reviewed_session_data["chain_boundary_json"],
            exclusions_json=reviewed_session_data["exclusions_json"],
            seed_companies_json=reviewed_session_data["seed_companies_json"],
            seed_products_json=reviewed_session_data["seed_products_json"],
            seed_technologies_json=reviewed_session_data["seed_technologies_json"],
            seed_bottlenecks_json=reviewed_session_data["seed_bottlenecks_json"],
            draft_graph_json=reviewed_session_data["draft_graph_json"],
            coverage_state=reviewed_session_data["coverage_state"],
            workflow_state=reviewed_session_data["workflow_state"],
            information_cutoff_date=reviewed_session_data[
                "information_cutoff_date"
            ],
            recorded_at_utc=session_recorded_at,
            input_fingerprint_sha256=reviewed_session_data[
                "input_fingerprint_sha256"
            ],
            supersedes_revision_id=source_revision.id,
            revision_note=reviewed_session_data["revision_note"],
        )
        session.add(reviewed_session_revision)
        session.flush()

        for item in prepared:
            latest = item["latest"]
            decision = item["decision"]
            reviewed_revision = IndustryThesisCandidateRevision(
                id=item["reviewed_candidate_revision_id"],
                candidate_id=item["identity"].id,
                session_revision_id=reviewed_session_revision_id,
                revision_number=item["revision_number"],
                source_kind=latest.source_kind,
                source_reference_json=latest.source_reference_json,
                proposed_stock_basic_record_id=latest.proposed_stock_basic_record_id,
                proposed_listed_instrument_id=latest.proposed_listed_instrument_id,
                company_label_original=latest.company_label_original,
                product_or_service_fit=latest.product_or_service_fit,
                industry_position=latest.industry_position,
                benefit_path_text=latest.benefit_path_text,
                proposed_exposure_type=(
                    decision["final_proposed_exposure_type"]
                    if decision["decision"] == "selected_for_acceptance"
                    else latest.proposed_exposure_type
                ),
                proposal_confidence=latest.proposal_confidence,
                identity_state=latest.identity_state,
                review_state=decision["decision"],
                rationale_json=decision["rationale_json"],
                uncertainty_json=decision["uncertainty_json"],
                manifest_fingerprint_sha256=latest.manifest_fingerprint_sha256,
                information_cutoff_date=source_revision.information_cutoff_date,
                recorded_at_utc=candidate_recorded_at,
                supersedes_revision_id=latest.id,
            )
            session.add(reviewed_revision)
            item["identity"].latest_revision_number = item["revision_number"]

        session_identity.latest_revision_number = expected_session + 1
        session.flush()
        return result

    @staticmethod
    def _validate_selected_identity(
        session: Session,
        latest: IndustryThesisCandidateRevision,
    ) -> None:
        if latest.identity_state != "exact_accepted_identity":
            raise IndustryThesisError(
                "industry_thesis_identity_invalid",
                "selected candidates require exact accepted identity",
            )
        stock_id = latest.proposed_stock_basic_record_id
        instrument_id = latest.proposed_listed_instrument_id
        if stock_id is None and instrument_id is None:
            raise IndustryThesisError(
                "industry_thesis_identity_invalid",
                "selected candidates require one exact persisted identity",
            )
        if stock_id is not None and session.get(StockBasicRecord, stock_id) is None:
            raise IndustryThesisError(
                "industry_thesis_identity_not_found",
                "exact stock identity was not found",
            )
        if instrument_id is not None and session.get(ListedInstrument, instrument_id) is None:
            raise IndustryThesisError(
                "industry_thesis_identity_not_found",
                "exact listed-instrument identity was not found",
            )

    @staticmethod
    def _selected_identity_key(
        latest: IndustryThesisCandidateRevision,
    ) -> tuple[str, str]:
        if latest.proposed_stock_basic_record_id is not None:
            return ("stock_basic", str(latest.proposed_stock_basic_record_id))
        return ("listed_instrument", str(latest.proposed_listed_instrument_id))

    @staticmethod
    def _build_plan(
        *,
        source_revision: IndustryThesisSessionRevision,
        reviewed_session_revision_id: UUID,
        candidate_recorded_at: datetime,
        prepared: list[dict[str, Any]],
    ) -> dict[str, Any]:
        selected: list[dict[str, Any]] = []
        rejected: list[str] = []
        unresolved: list[str] = []
        candidate_sources: list[dict[str, str]] = []
        for item in prepared:
            latest = item["latest"]
            decision = item["decision"]
            reviewed_id = str(item["reviewed_candidate_revision_id"])
            source_reference_fingerprint = fingerprint(
                json_value(latest.source_reference_json, "source_reference")
            )
            candidate_sources.append(
                {
                    "candidate_revision_id": reviewed_id,
                    "source_kind": latest.source_kind,
                    "source_reference_fingerprint_sha256": source_reference_fingerprint,
                }
            )
            if decision["decision"] == "selected_for_acceptance":
                selected.append(
                    {
                        "candidate_id": str(item["identity"].id),
                        "candidate_revision_id": reviewed_id,
                        "proposed_stock_basic_record_id": latest.proposed_stock_basic_record_id,
                        "proposed_listed_instrument_id": (
                            None
                            if latest.proposed_listed_instrument_id is None
                            else str(latest.proposed_listed_instrument_id)
                        ),
                        "final_proposed_exposure_type": decision[
                            "final_proposed_exposure_type"
                        ],
                        "source_kind": latest.source_kind,
                        "source_reference_fingerprint_sha256": source_reference_fingerprint,
                    }
                )
            elif decision["decision"] == "rejected_by_user":
                rejected.append(reviewed_id)
            else:
                unresolved.append(reviewed_id)
        selected.sort(
            key=lambda item: (
                str(item["proposed_stock_basic_record_id"] or ""),
                item["proposed_listed_instrument_id"] or "",
                item["candidate_revision_id"],
            )
        )
        rejected.sort()
        unresolved.sort()
        candidate_sources.sort(key=lambda item: item["candidate_revision_id"])
        base = {
            "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
            "session_id": str(source_revision.session_id),
            "source_session_revision_id": str(source_revision.id),
            "reviewed_session_revision_id": str(reviewed_session_revision_id),
            "information_cutoff_date": source_revision.information_cutoff_date.isoformat(),
            "recorded_at_utc_boundary": candidate_recorded_at.isoformat(),
            "coverage_state": source_revision.coverage_state,
            "selected_candidates": selected,
            "rejected_candidate_revision_ids": rejected,
            "unresolved_candidate_revision_ids": unresolved,
            "candidate_sources": candidate_sources,
        }
        return {
            **base,
            "acceptance_plan_fingerprint_sha256": fingerprint(base),
        }


class IndustryThesisReviewedPlanQueryService:
    """Read and verify one exact reviewed-plan preview under dual as-of boundaries."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_reviewed_plan(
        self,
        session_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        recorded_boundary = _validate_recorded_boundary(as_of_recorded_at_utc)
        revision = self._session.get(
            IndustryThesisSessionRevision,
            session_revision_id,
        )
        if revision is None:
            raise IndustryThesisNotFound(
                "industry_thesis_session_revision_not_found",
                "exact reviewed session revision was not found",
            )
        if (
            revision.information_cutoff_date > as_of_cutoff
            or stored_utc(revision.recorded_at_utc) > recorded_boundary
        ):
            raise IndustryThesisNotFound(
                "industry_thesis_not_visible",
                "reviewed plan is outside the requested as-of boundaries",
            )
        if revision.workflow_state != "reviewed_plan_ready":
            raise IndustryThesisError(
                "industry_thesis_review_invalid",
                "exact session revision does not freeze a reviewed plan",
            )
        graph = json_value(revision.draft_graph_json, "draft_graph")
        if not isinstance(graph, dict) or "acceptance_plan_preview" not in graph:
            raise IndustryThesisError(
                "industry_thesis_graph_incomplete",
                "reviewed session revision is missing its acceptance-plan preview",
            )
        plan = graph["acceptance_plan_preview"]
        if not isinstance(plan, dict):
            raise IndustryThesisError(
                "industry_thesis_graph_incomplete",
                "stored acceptance-plan preview is invalid",
            )
        stored_fingerprint = plan.get("acceptance_plan_fingerprint_sha256")
        base = {
            key: value
            for key, value in plan.items()
            if key != "acceptance_plan_fingerprint_sha256"
        }
        if (
            not isinstance(stored_fingerprint, str)
            or fingerprint(base) != stored_fingerprint
            or plan.get("reviewed_session_revision_id") != str(revision.id)
        ):
            raise IndustryThesisError(
                "industry_thesis_graph_incomplete",
                "stored acceptance-plan fingerprint or revision binding is invalid",
            )
        candidate_ids = [
            UUID(item["candidate_revision_id"])
            for item in plan.get("selected_candidates", [])
        ]
        candidate_ids.extend(
            UUID(value)
            for value in plan.get("rejected_candidate_revision_ids", [])
        )
        candidate_ids.extend(
            UUID(value)
            for value in plan.get("unresolved_candidate_revision_ids", [])
        )
        if len(candidate_ids) != len(set(candidate_ids)):
            raise IndustryThesisError(
                "industry_thesis_graph_incomplete",
                "stored acceptance plan contains duplicate candidate revisions",
            )
        rows = list(
            self._session.scalars(
                select(IndustryThesisCandidateRevision).where(
                    IndustryThesisCandidateRevision.id.in_(candidate_ids)
                )
            )
        )
        if len(rows) != len(candidate_ids):
            raise IndustryThesisError(
                "industry_thesis_graph_incomplete",
                "stored acceptance plan references missing candidate revisions",
            )
        source_entries = plan.get("candidate_sources", [])
        if not isinstance(source_entries, list):
            raise IndustryThesisError(
                "industry_thesis_graph_incomplete",
                "stored acceptance plan candidate sources are invalid",
            )
        source_by_id = {
            UUID(item["candidate_revision_id"]): item
            for item in source_entries
            if isinstance(item, dict) and "candidate_revision_id" in item
        }
        if set(source_by_id) != set(candidate_ids):
            raise IndustryThesisError(
                "industry_thesis_graph_incomplete",
                "stored acceptance plan does not freeze every candidate source",
            )
        expected_states = {
            UUID(item["candidate_revision_id"]): "selected_for_acceptance"
            for item in plan.get("selected_candidates", [])
        }
        expected_states.update(
            {
                UUID(value): "rejected_by_user"
                for value in plan.get("rejected_candidate_revision_ids", [])
            }
        )
        expected_states.update(
            {
                UUID(value): "unresolved"
                for value in plan.get("unresolved_candidate_revision_ids", [])
            }
        )
        for row in rows:
            if (
                row.session_revision_id != revision.id
                or row.information_cutoff_date > as_of_cutoff
                or stored_utc(row.recorded_at_utc) > recorded_boundary
                or row.review_state != expected_states[row.id]
                or source_by_id[row.id].get("source_kind") != row.source_kind
                or source_by_id[row.id].get(
                    "source_reference_fingerprint_sha256"
                )
                != fingerprint(json_value(row.source_reference_json, "source_reference"))
            ):
                raise IndustryThesisError(
                    "industry_thesis_graph_incomplete",
                    "stored acceptance-plan candidate binding is invalid",
                )
        return {
            "session_revision_id": str(revision.id),
            "session_id": str(revision.session_id),
            "workflow_state": revision.workflow_state,
            "information_cutoff_date": revision.information_cutoff_date.isoformat(),
            "recorded_at_utc": stored_utc(revision.recorded_at_utc).isoformat(),
            "acceptance_plan": plan,
            "acceptance_plan_fingerprint_sha256": stored_fingerprint,
        }

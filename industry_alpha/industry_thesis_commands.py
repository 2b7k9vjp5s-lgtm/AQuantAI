"""Transactional local-only commands for offline Industry Thesis Orchestration v1."""

from __future__ import annotations

from datetime import date, datetime
from threading import Lock, RLock
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price_models import ListedInstrument
from backend.database.models import StockBasicRecord
from industry_alpha.chain_map_models import IndustryMapRevision
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateIdentity,
    IndustryThesisCandidateRevision,
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_rules import (
    IndustryThesisError,
    apply_session_patch,
    json_value,
    normalize_candidate_build,
    normalize_session_payload,
    parse_integer,
    parse_uuid,
    require_keys,
    stored_utc,
    utc_now,
)

_LOCK_GUARD = Lock()
_LOCKS: dict[tuple[str, str], RLock] = {}


def _lock(kind: str, key: str) -> RLock:
    with _LOCK_GUARD:
        return _LOCKS.setdefault((kind, key), RLock())


def _chronology(cutoff: date, recorded_at: datetime, latest: Any | None = None) -> None:
    if cutoff > recorded_at.date():
        raise IndustryThesisError(
            "industry_thesis_chronology_invalid",
            "information cutoff cannot exceed the system-owned recorded UTC date",
        )
    if latest is not None and (
        cutoff < latest.information_cutoff_date
        or recorded_at <= stored_utc(latest.recorded_at_utc)
    ):
        raise IndustryThesisError(
            "industry_thesis_chronology_invalid",
            "append-only chronology must not move backward",
        )


def _session_payload(raw: dict[str, Any]) -> dict[str, Any]:
    return normalize_session_payload(raw)


def _revise_payload(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {"session_id", "expected_latest_revision_number", "changes", "revision_note"}
    require_keys(raw, allowed, allowed)
    return {
        "session_id": parse_uuid(raw["session_id"], "session_id"),
        "expected_latest_revision_number": parse_integer(
            raw["expected_latest_revision_number"],
            "expected_latest_revision_number",
            minimum=1,
        ),
        "changes": raw["changes"],
        "revision_note": raw["revision_note"],
    }


def _session_result(
    identity: IndustryThesisSessionIdentity | None,
    revision: IndustryThesisSessionRevision | None,
    data: dict[str, Any],
    *,
    dry_run: bool,
    revision_number: int,
    recorded_at: datetime,
) -> dict[str, Any]:
    return {
        "dry_run": dry_run,
        "session_id": None if identity is None else str(identity.id),
        "session_revision_id": None if revision is None else str(revision.id),
        "revision_number": revision_number,
        "state": "active" if identity is None else identity.state,
        "workflow_state": data["workflow_state"],
        "coverage_state": data["coverage_state"],
        "information_cutoff_date": data["information_cutoff_date"].isoformat(),
        "recorded_at_utc": recorded_at.isoformat(),
        "input_fingerprint_sha256": data["input_fingerprint_sha256"],
    }


class IndustryThesisCommandService:
    """Local, deterministic, dry-run-capable implementation command surface."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock

    def create_session(self, raw: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
        data = _session_payload(raw)
        key = data["input_fingerprint_sha256"]
        return self._execute(
            "session-create",
            key,
            dry_run,
            lambda session: self._create_session(session, data, dry_run),
        )

    def revise_session(self, raw: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
        command = _revise_payload(raw)
        return self._execute(
            "session-revise",
            str(command["session_id"]),
            dry_run,
            lambda session: self._revise_session(session, command, dry_run),
        )

    def build_candidates(self, raw: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
        data = normalize_candidate_build(raw)
        return self._execute(
            "candidate-build",
            str(data["session_revision_id"]),
            dry_run,
            lambda session: self._build_candidates(session, data, dry_run),
        )

    def _execute(
        self,
        kind: str,
        key: str,
        dry_run: bool,
        action: Callable[[Session], dict[str, Any]],
    ) -> dict[str, Any]:
        try:
            with _lock(kind, key):
                if dry_run:
                    with self._session_factory() as session:
                        return action(session)
                with self._session_factory.begin() as session:
                    return action(session)
        except IntegrityError as exc:
            raise IndustryThesisError(
                "industry_thesis_revision_conflict",
                "industry-thesis history conflicts with accepted local history",
            ) from exc

    def _recorded_now(self) -> datetime:
        return stored_utc(self._clock())

    def _create_session(
        self,
        session: Session,
        data: dict[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
        recorded_at = self._recorded_now()
        _chronology(data["information_cutoff_date"], recorded_at)
        if dry_run:
            return _session_result(
                None,
                None,
                data,
                dry_run=True,
                revision_number=1,
                recorded_at=recorded_at,
            )
        identity = IndustryThesisSessionIdentity(
            created_recorded_utc=recorded_at,
            created_by_kind="local_user",
            state="active",
            latest_revision_number=0,
        )
        session.add(identity)
        session.flush()
        revision = self._append_session_revision(
            session,
            identity=identity,
            data=data,
            revision_number=1,
            recorded_at=recorded_at,
            supersedes_revision_id=None,
        )
        identity.latest_revision_number = 1
        session.flush()
        return _session_result(
            identity,
            revision,
            data,
            dry_run=False,
            revision_number=1,
            recorded_at=recorded_at,
        )

    def _revise_session(
        self,
        session: Session,
        command: dict[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
        identity = session.scalar(
            select(IndustryThesisSessionIdentity)
            .where(IndustryThesisSessionIdentity.id == command["session_id"])
            .with_for_update()
        )
        if identity is None:
            raise IndustryThesisError(
                "industry_thesis_session_not_found",
                "exact industry-thesis session was not found",
            )
        expected = command["expected_latest_revision_number"]
        if identity.latest_revision_number != expected:
            raise IndustryThesisError(
                "industry_thesis_revision_conflict",
                "expected latest session revision does not match",
            )
        latest = session.scalar(
            select(IndustryThesisSessionRevision)
            .where(
                IndustryThesisSessionRevision.session_id == identity.id,
                IndustryThesisSessionRevision.revision_number == expected,
            )
            .with_for_update()
        )
        if latest is None:
            raise IndustryThesisError(
                "industry_thesis_graph_incomplete",
                "latest session revision pointer is incomplete",
            )
        data = apply_session_patch(latest, command["changes"], command["revision_note"])
        if data["input_fingerprint_sha256"] == latest.input_fingerprint_sha256:
            raise IndustryThesisError(
                "industry_thesis_no_change",
                "session revision must change the fingerprinted research input",
            )
        recorded_at = self._recorded_now()
        _chronology(data["information_cutoff_date"], recorded_at, latest)
        revision_number = expected + 1
        if dry_run:
            return _session_result(
                identity,
                None,
                data,
                dry_run=True,
                revision_number=revision_number,
                recorded_at=recorded_at,
            )
        revision = self._append_session_revision(
            session,
            identity=identity,
            data=data,
            revision_number=revision_number,
            recorded_at=recorded_at,
            supersedes_revision_id=latest.id,
        )
        identity.latest_revision_number = revision_number
        session.flush()
        return _session_result(
            identity,
            revision,
            data,
            dry_run=False,
            revision_number=revision_number,
            recorded_at=recorded_at,
        )

    @staticmethod
    def _append_session_revision(
        session: Session,
        *,
        identity: IndustryThesisSessionIdentity,
        data: dict[str, Any],
        revision_number: int,
        recorded_at: datetime,
        supersedes_revision_id: UUID | None,
    ) -> IndustryThesisSessionRevision:
        revision = IndustryThesisSessionRevision(
            session_id=identity.id,
            revision_number=revision_number,
            thesis_text_original=data["thesis_text_original"],
            thesis_title_reviewed=data["thesis_title_reviewed"],
            driver_type=data["driver_type"],
            analysis_horizon_kind=data["analysis_horizon_kind"],
            analysis_start_date=data["analysis_start_date"],
            analysis_end_date=data["analysis_end_date"],
            market_scope_json=data["market_scope_json"],
            chain_boundary_json=data["chain_boundary_json"],
            exclusions_json=data["exclusions_json"],
            seed_companies_json=data["seed_companies_json"],
            seed_products_json=data["seed_products_json"],
            seed_technologies_json=data["seed_technologies_json"],
            seed_bottlenecks_json=data["seed_bottlenecks_json"],
            draft_graph_json=data["draft_graph_json"],
            coverage_state=data["coverage_state"],
            workflow_state=data["workflow_state"],
            information_cutoff_date=data["information_cutoff_date"],
            recorded_at_utc=recorded_at,
            input_fingerprint_sha256=data["input_fingerprint_sha256"],
            supersedes_revision_id=supersedes_revision_id,
            revision_note=data["revision_note"],
        )
        session.add(revision)
        session.flush()
        return revision

    def _build_candidates(
        self,
        session: Session,
        data: dict[str, Any],
        dry_run: bool,
    ) -> dict[str, Any]:
        session_revision = session.get(
            IndustryThesisSessionRevision,
            data["session_revision_id"],
        )
        if session_revision is None:
            raise IndustryThesisError(
                "industry_thesis_session_revision_not_found",
                "exact session revision was not found",
            )
        identity = session.scalar(
            select(IndustryThesisSessionIdentity)
            .where(IndustryThesisSessionIdentity.id == session_revision.session_id)
            .with_for_update()
        )
        if identity is None:
            raise IndustryThesisError(
                "industry_thesis_graph_incomplete",
                "session identity graph is incomplete",
            )
        expected = data["expected_session_latest_revision_number"]
        if identity.latest_revision_number != expected or session_revision.revision_number != expected:
            raise IndustryThesisError(
                "industry_thesis_revision_conflict",
                "candidate build requires the exact latest session revision",
            )
        recorded_at = self._recorded_now()
        _chronology(session_revision.information_cutoff_date, recorded_at)
        planned: list[dict[str, Any]] = []
        for proposal in data["proposals"]:
            self._validate_candidate_source(
                session,
                proposal,
                session_revision.information_cutoff_date,
                recorded_at,
            )
            candidate = session.scalar(
                select(IndustryThesisCandidateIdentity)
                .where(
                    IndustryThesisCandidateIdentity.session_id == identity.id,
                    IndustryThesisCandidateIdentity.candidate_key == proposal["candidate_key"],
                )
                .with_for_update()
            )
            current = 0 if candidate is None else candidate.latest_revision_number
            explicit_expected = proposal["expected_latest_revision_number"]
            if candidate is None:
                if explicit_expected not in {None, 0}:
                    raise IndustryThesisError(
                        "industry_thesis_revision_conflict",
                        "new candidate source requires expected latest revision 0 or omission",
                    )
                latest_revision = None
            else:
                if explicit_expected is None or explicit_expected != current:
                    raise IndustryThesisError(
                        "industry_thesis_revision_conflict",
                        "existing candidate source requires the exact latest revision number",
                    )
                latest_revision = session.scalar(
                    select(IndustryThesisCandidateRevision)
                    .where(
                        IndustryThesisCandidateRevision.candidate_id == candidate.id,
                        IndustryThesisCandidateRevision.revision_number == current,
                    )
                    .with_for_update()
                )
                if latest_revision is None:
                    raise IndustryThesisError(
                        "industry_thesis_graph_incomplete",
                        "candidate latest revision pointer is incomplete",
                    )
                _chronology(
                    session_revision.information_cutoff_date,
                    recorded_at,
                    latest_revision,
                )
            planned.append(
                {
                    "proposal": proposal,
                    "candidate": candidate,
                    "latest_revision": latest_revision,
                    "revision_number": current + 1,
                }
            )
        if dry_run:
            return self._candidate_result(
                session_revision,
                planned,
                dry_run=True,
                recorded_at=recorded_at,
            )
        for item in planned:
            proposal = item["proposal"]
            candidate = item["candidate"]
            if candidate is None:
                candidate = IndustryThesisCandidateIdentity(
                    session_id=identity.id,
                    candidate_key=proposal["candidate_key"],
                    created_recorded_utc=recorded_at,
                    latest_revision_number=0,
                )
                session.add(candidate)
                session.flush()
                item["candidate"] = candidate
            revision = IndustryThesisCandidateRevision(
                candidate_id=candidate.id,
                session_revision_id=session_revision.id,
                revision_number=item["revision_number"],
                source_kind=proposal["source_kind"],
                source_reference_json=proposal["source_reference_json"],
                proposed_stock_basic_record_id=proposal["proposed_stock_basic_record_id"],
                proposed_listed_instrument_id=proposal["proposed_listed_instrument_id"],
                company_label_original=proposal["company_label_original"],
                product_or_service_fit=proposal["product_or_service_fit"],
                industry_position=proposal["industry_position"],
                benefit_path_text=proposal["benefit_path_text"],
                proposed_exposure_type=proposal["proposed_exposure_type"],
                proposal_confidence=proposal["proposal_confidence"],
                identity_state=proposal["identity_state"],
                review_state=proposal["review_state"],
                rationale_json=proposal["rationale_json"],
                uncertainty_json=proposal["uncertainty_json"],
                manifest_fingerprint_sha256=proposal["manifest_fingerprint_sha256"],
                information_cutoff_date=session_revision.information_cutoff_date,
                recorded_at_utc=recorded_at,
                supersedes_revision_id=(
                    None if item["latest_revision"] is None else item["latest_revision"].id
                ),
            )
            session.add(revision)
            session.flush()
            candidate.latest_revision_number = item["revision_number"]
            item["revision"] = revision
        session.flush()
        return self._candidate_result(
            session_revision,
            planned,
            dry_run=False,
            recorded_at=recorded_at,
        )

    @staticmethod
    def _validate_candidate_source(
        session: Session,
        proposal: dict[str, Any],
        cutoff: date,
        recorded_at: datetime,
    ) -> None:
        stock_id = proposal["proposed_stock_basic_record_id"]
        instrument_id = proposal["proposed_listed_instrument_id"]
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
        source_reference = json_value(proposal["source_reference_json"], "source_reference")
        if not isinstance(source_reference, dict) or not source_reference:
            raise IndustryThesisError(
                "industry_thesis_source_invalid",
                "candidate source reference must be an explicit non-empty object",
            )
        source_kind = proposal["source_kind"]
        if source_kind == "accepted_local_mapping" and proposal["identity_state"] != "exact_accepted_identity":
            raise IndustryThesisError(
                "industry_thesis_identity_invalid",
                "accepted local mapping requires exact accepted identity",
            )
        if source_kind == "existing_industry_map_revision":
            require_keys(
                source_reference,
                {"industry_map_revision_id"},
                {"industry_map_revision_id"},
                field="source_reference",
            )
            revision_id = parse_uuid(
                source_reference["industry_map_revision_id"],
                "source_reference.industry_map_revision_id",
            )
            map_revision = session.get(IndustryMapRevision, revision_id)
            if map_revision is None:
                raise IndustryThesisError(
                    "industry_thesis_source_not_found",
                    "exact industry-map revision was not found",
                )
            if (
                map_revision.information_cutoff_date > cutoff
                or stored_utc(map_revision.recorded_at_utc) > recorded_at
            ):
                raise IndustryThesisError(
                    "industry_thesis_later_information",
                    "industry-map source exceeds the thesis as-of boundary",
                )

    @staticmethod
    def _candidate_result(
        session_revision: IndustryThesisSessionRevision,
        planned: list[dict[str, Any]],
        *,
        dry_run: bool,
        recorded_at: datetime,
    ) -> dict[str, Any]:
        candidates = []
        for item in planned:
            proposal = item["proposal"]
            candidate = item["candidate"]
            revision = item.get("revision")
            candidates.append(
                {
                    "candidate_id": None if candidate is None else str(candidate.id),
                    "candidate_revision_id": None if revision is None else str(revision.id),
                    "candidate_key": proposal["candidate_key"],
                    "revision_number": item["revision_number"],
                    "source_kind": proposal["source_kind"],
                    "company_label_original": proposal["company_label_original"],
                    "identity_state": proposal["identity_state"],
                    "review_state": proposal["review_state"],
                    "proposed_exposure_type": proposal["proposed_exposure_type"],
                }
            )
        return {
            "dry_run": dry_run,
            "session_id": str(session_revision.session_id),
            "session_revision_id": str(session_revision.id),
            "session_revision_number": session_revision.revision_number,
            "coverage_state": session_revision.coverage_state,
            "information_cutoff_date": session_revision.information_cutoff_date.isoformat(),
            "recorded_at_utc": recorded_at.isoformat(),
            "candidate_count": len(candidates),
            "candidates": candidates,
        }

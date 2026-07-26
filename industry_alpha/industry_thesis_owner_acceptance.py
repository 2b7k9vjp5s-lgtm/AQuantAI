"""Atomic Industry Thesis owner-acceptance coordinator."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from threading import Lock, RLock
from typing import Any, Callable
from uuid import UUID, uuid5

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticProfile,
    Stage1BeneficiarySemanticProfileRevision,
)
from industry_alpha.beneficiary_semantics_owner_port import (
    BeneficiarySemanticOwnerResult,
    BeneficiarySemanticOwnerWritePort,
)
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.errors import (
    EvidenceLedgerConflictError,
    EvidenceLedgerNotFound,
    EvidenceLedgerValidationError,
)
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateRevision,
    IndustryThesisOutputLinkIdentity,
    IndustryThesisOutputLinkRevision,
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_owner_acceptance_contracts import (
    OUTPUT_CONTRACT_VERSION,
    TRANSACTION_NAMESPACE,
    IndustryThesisOwnerAcceptanceError,
    normalize_owner_acceptance_plan,
    output_key,
    owner_plan_canonical_value,
    owner_transaction_id,
    reason_payload,
)
from industry_alpha.industry_thesis_review import (
    ACCEPTANCE_PLAN_VERSION,
    HISTORICAL_ACCEPTANCE_PLAN_VERSION,
    OWNER_CONTEXT_VERSION,
    OWNER_MAP_MODE,
)
from industry_alpha.industry_thesis_rules import (
    IndustryThesisError,
    canonical_json_text,
    fingerprint,
    json_value,
    normalize_session_payload,
    session_revision_to_input,
    stored_utc,
    utc_now,
)
from industry_alpha.models import ResearchCase
from industry_alpha.stage1_commands import MapAssertionRevisionInput
from industry_alpha.stage1_models import (
    Stage1BeneficiaryRevision,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
from industry_alpha.stage1_owner_port import (
    Stage1BeneficiaryOwnerResult,
    Stage1CandidatePoolOwnerResult,
    Stage1OwnerWritePort,
)

_LOCK_GUARD = Lock()
_LOCKS: dict[str, RLock] = {}


def _lock(key: str) -> RLock:
    with _LOCK_GUARD:
        return _LOCKS.setdefault(key, RLock())


class IndustryThesisOwnerAcceptanceService:
    """Preview and commit one exact cross-owner acceptance transaction."""

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock
        self._stage1 = Stage1OwnerWritePort(session_factory)
        self._semantics = BeneficiarySemanticOwnerWritePort(session_factory)

    def preview(self, raw: dict[str, Any]) -> dict[str, Any]:
        try:
            normalized = normalize_owner_acceptance_plan(raw)
            with _lock(normalized["reviewed_session_revision_id"]):
                with self._session_factory() as session:
                    try:
                        result = self._run(session, normalized, dry_run=True)
                    finally:
                        session.rollback()
            return result
        except IndustryThesisOwnerAcceptanceError as exc:
            return self._blocked_preview(raw, exc.code, exc.detail)
        except IndustryThesisError as exc:
            return self._blocked_preview(raw, exc.code, str(exc))
        except EvidenceLedgerConflictError as exc:
            return self._blocked_preview(
                raw,
                "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT",
                str(exc),
            )
        except (EvidenceLedgerNotFound, EvidenceLedgerValidationError) as exc:
            return self._blocked_preview(
                raw,
                "INDUSTRY_THESIS_ACCEPTANCE_STAGE1_BINDINGS_REQUIRED",
                str(exc),
            )

    def commit(self, raw: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_owner_acceptance_plan(
            raw,
            require_preview_fingerprint=True,
        )
        if (
            normalized["preview_fingerprint_sha256"]
            != normalized["owner_acceptance_plan_fingerprint_sha256"]
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE",
                "preview fingerprint does not match the normalized owner plan",
            )
        try:
            with _lock(normalized["reviewed_session_revision_id"]):
                with self._session_factory.begin() as session:
                    return self._run(session, normalized, dry_run=False)
        except IntegrityError as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT",
                "database uniqueness or foreign-key conflict",
            ) from exc
        except EvidenceLedgerConflictError as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT",
                str(exc),
            ) from exc
        except EvidenceLedgerNotFound as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_STAGE1_BINDINGS_REQUIRED",
                str(exc),
            ) from exc
        except EvidenceLedgerValidationError as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_STAGE1_BINDINGS_REQUIRED",
                str(exc),
            ) from exc

    @staticmethod
    def _blocked_preview(
        raw: dict[str, Any],
        code: str,
        detail: str | None,
    ) -> dict[str, Any]:
        return {
            "dry_run": True,
            "commit_ready": False,
            "reviewed_session_revision_id": (
                raw.get("reviewed_session_revision_id")
                if isinstance(raw, dict)
                else None
            ),
            "preview_fingerprint_sha256": None,
            "blocked_reasons": [reason_payload(code, detail=detail)],
        }

    def _run(
        self,
        session: Session,
        normalized: dict[str, Any],
        *,
        dry_run: bool,
    ) -> dict[str, Any]:
        reviewed, identity, latest, reviewed_plan = self._lock_and_validate_reviewed(
            session,
            normalized,
        )
        existing_output = self._lock_existing_output(
            session,
            identity=identity,
            normalized=normalized,
        )
        if existing_output is not None:
            self._validate_existing_output_replay(
                existing_output,
                normalized,
                reviewed_plan,
            )
            return self._idempotent_result(
                existing_output,
                normalized,
                dry_run=dry_run,
            )

        owner_context = self._validate_reviewed_owner_context(reviewed_plan)
        self._validate_submitted_owner_context(normalized, owner_context)
        research_case, industry_map, map_revision = self._validate_case_and_map(
            session,
            normalized,
            reviewed,
            owner_context,
        )
        if (
            latest.id != reviewed.id
            or identity.latest_revision_number
            != normalized["expected_session_latest_revision_number"]
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE"
            )

        reviewed_candidates = self._validate_candidate_bindings(
            session,
            normalized,
            reviewed,
            reviewed_plan,
        )
        recorded_at = self._recorded_boundary(
            session,
            normalized,
            reviewed,
            map_revision,
        )
        self._lock_owner_targets(session, normalized)

        owner_rows: list[
            tuple[
                dict[str, Any],
                IndustryThesisCandidateRevision,
                Stage1BeneficiaryOwnerResult,
                BeneficiarySemanticOwnerResult | None,
            ]
        ] = []
        seen_beneficiaries: set[UUID] = set()
        for binding in normalized["candidate_owner_bindings"]:
            reviewed_candidate = reviewed_candidates[
                UUID(binding["reviewed_candidate_revision_id"])
            ]
            beneficiary_result = self._apply_stage1(
                session,
                normalized,
                binding,
                recorded_at,
            )
            if beneficiary_result.beneficiary.id in seen_beneficiaries:
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_DUPLICATE_OWNER_IDENTITY"
                )
            seen_beneficiaries.add(beneficiary_result.beneficiary.id)
            semantic_result = self._apply_semantics(
                session,
                normalized,
                binding,
                beneficiary_result,
                recorded_at,
            )
            owner_rows.append(
                (
                    binding,
                    reviewed_candidate,
                    beneficiary_result,
                    semantic_result,
                )
            )

        supported_ids = tuple(
            row[2].revision.id
            for row in owner_rows
            if row[2].revision.assessment_status == "supported"
        )
        pool_result = self._apply_candidate_pool(
            session,
            normalized,
            supported_ids,
            recorded_at,
        )
        output_bindings = self._output_bindings(owner_rows)
        accepted_result = {
            "complete_member_count": len(output_bindings),
            "supported_handoff_count": len(supported_ids),
            "candidate_pool_mode": normalized["candidate_pool_operation"]["mode"],
            "accepted_candidate_pool_revision_id": (
                None if pool_result is None else str(pool_result.revision.id)
            ),
            "ordered_owner_output_bindings": output_bindings,
            "no_supported_handoff_members": not supported_ids,
        }

        transaction_id = owner_transaction_id(normalized)
        accepted_session_id = uuid5(
            TRANSACTION_NAMESPACE,
            f"accepted-session:{transaction_id}",
        )
        output_identity_id = uuid5(
            TRANSACTION_NAMESPACE,
            f"output-identity:{transaction_id}",
        )
        output_revision_id = uuid5(
            TRANSACTION_NAMESPACE,
            f"output-revision:{transaction_id}",
        )
        accepted_session = self._append_accepted_session(
            session,
            identity=identity,
            reviewed=reviewed,
            normalized=normalized,
            accepted_result=accepted_result,
            accepted_session_id=accepted_session_id,
            output_revision_id=output_revision_id,
            recorded_at=recorded_at,
        )
        output_identity, output_revision = self._append_output_link(
            session,
            identity=identity,
            reviewed=reviewed,
            accepted_session=accepted_session,
            normalized=normalized,
            accepted_result=accepted_result,
            output_identity_id=output_identity_id,
            output_revision_id=output_revision_id,
            transaction_id=transaction_id,
            pool_result=pool_result,
            recorded_at=recorded_at,
        )
        session.flush()

        return {
            "dry_run": dry_run,
            "commit_ready": True,
            "idempotent_replay": False,
            "owner_acceptance_plan_version": normalized[
                "owner_acceptance_plan_version"
            ],
            "owner_acceptance_plan_fingerprint_sha256": normalized[
                "owner_acceptance_plan_fingerprint_sha256"
            ],
            "preview_fingerprint_sha256": normalized[
                "owner_acceptance_plan_fingerprint_sha256"
            ],
            "reviewed_session_revision_id": str(reviewed.id),
            "accepted_session_revision_id": (
                None if dry_run else str(accepted_session.id)
            ),
            "output_link_id": None if dry_run else str(output_identity.id),
            "output_link_revision_id": None if dry_run else str(output_revision.id),
            "owner_transaction_id": str(transaction_id),
            "research_case_id": str(research_case.id),
            "industry_map_id": str(industry_map.id),
            "industry_map_revision_id": str(map_revision.id),
            "complete_universe_count": len(output_bindings),
            "supported_handoff_count": len(supported_ids),
            "candidate_pool_mode": normalized["candidate_pool_operation"]["mode"],
            "accepted_candidate_pool_revision_id": (
                None
                if dry_run or pool_result is None
                else str(pool_result.revision.id)
            ),
            "operation_summaries": [
                self._preview_operation_summary(row, dry_run=dry_run)
                for row in owner_rows
            ],
            "blocked_reasons": [],
            "recorded_at_utc": recorded_at.isoformat(),
        }

    def _lock_and_validate_reviewed(
        self,
        session: Session,
        normalized: dict[str, Any],
    ) -> tuple[
        IndustryThesisSessionRevision,
        IndustryThesisSessionIdentity,
        IndustryThesisSessionRevision,
        dict[str, Any],
    ]:
        reviewed_id = UUID(normalized["reviewed_session_revision_id"])
        probe = session.get(IndustryThesisSessionRevision, reviewed_id)
        if probe is None:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_NOT_READY"
            )
        identity = session.scalar(
            select(IndustryThesisSessionIdentity)
            .where(IndustryThesisSessionIdentity.id == probe.session_id)
            .with_for_update()
        )
        if identity is None:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )
        reviewed = session.scalar(
            select(IndustryThesisSessionRevision)
            .where(IndustryThesisSessionRevision.id == reviewed_id)
            .with_for_update()
        )
        expected = normalized["expected_session_latest_revision_number"]
        latest = session.scalar(
            select(IndustryThesisSessionRevision)
            .where(
                IndustryThesisSessionRevision.session_id == identity.id,
                IndustryThesisSessionRevision.revision_number
                == identity.latest_revision_number,
            )
            .with_for_update()
        )
        if (
            reviewed is None
            or latest is None
            or reviewed.revision_number != expected
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE"
            )
        if latest.id != reviewed.id and not (
            latest.workflow_state == "accepted_outputs_linked"
            and latest.supersedes_revision_id == reviewed.id
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE"
            )
        if reviewed.workflow_state != "reviewed_plan_ready":
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_NOT_READY"
            )
        graph = json_value(reviewed.draft_graph_json, "draft_graph")
        if not isinstance(graph, dict):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )
        reviewed_plan = graph.get("acceptance_plan_preview")
        if not isinstance(reviewed_plan, dict):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )
        stored_fingerprint = reviewed_plan.get(
            "acceptance_plan_fingerprint_sha256"
        )
        base = {
            key: value
            for key, value in reviewed_plan.items()
            if key != "acceptance_plan_fingerprint_sha256"
        }
        if (
            stored_fingerprint != normalized["reviewed_plan_fingerprint_sha256"]
            or fingerprint(base) != stored_fingerprint
            or reviewed_plan.get("reviewed_session_revision_id") != str(reviewed.id)
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_FINGERPRINT_MISMATCH"
            )
        return reviewed, identity, latest, reviewed_plan

    @staticmethod
    def _validate_reviewed_owner_context(
        reviewed_plan: dict[str, Any],
    ) -> dict[str, str]:
        version = reviewed_plan.get("acceptance_plan_version")
        if version == HISTORICAL_ACCEPTANCE_PLAN_VERSION:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_NOT_READY",
                "reviewed Owner Context is required; explicitly re-review the v1 plan",
            )
        if version != ACCEPTANCE_PLAN_VERSION:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "reviewed acceptance-plan version is unsupported",
            )
        raw = reviewed_plan.get("owner_context")
        allowed = {
            "owner_context_contract_version",
            "map_mode",
            "research_case_id",
            "industry_map_id",
            "industry_map_revision_id",
        }
        if not isinstance(raw, dict) or set(raw) != allowed:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "reviewed Owner Context shape is invalid",
            )
        if (
            raw.get("owner_context_contract_version") != OWNER_CONTEXT_VERSION
            or raw.get("map_mode") != OWNER_MAP_MODE
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "reviewed Owner Context contract is unsupported",
            )
        try:
            case_id = UUID(str(raw["research_case_id"]))
            map_id = UUID(str(raw["industry_map_id"]))
            map_revision_id = UUID(str(raw["industry_map_revision_id"]))
        except (TypeError, ValueError, AttributeError) as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE",
                "reviewed Owner Context identifiers are invalid",
            ) from exc
        return {
            "owner_context_contract_version": OWNER_CONTEXT_VERSION,
            "map_mode": OWNER_MAP_MODE,
            "research_case_id": str(case_id),
            "industry_map_id": str(map_id),
            "industry_map_revision_id": str(map_revision_id),
        }

    @staticmethod
    def _validate_submitted_owner_context(
        normalized: dict[str, Any],
        owner_context: dict[str, str],
    ) -> None:
        if (
            normalized["map_mode"] != owner_context["map_mode"]
            or normalized["research_case_id"]
            != owner_context["research_case_id"]
            or normalized["industry_map_id"] != owner_context["industry_map_id"]
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED",
                "submitted Case, Map or map mode does not match reviewed authority",
            )
        if (
            normalized["industry_map_revision_id"]
            != owner_context["industry_map_revision_id"]
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_MAP_REVISION_MISMATCH",
                "submitted Map Revision does not match reviewed authority",
            )

    @classmethod
    def _validate_existing_output_replay(
        cls,
        output: IndustryThesisOutputLinkRevision,
        normalized: dict[str, Any],
        reviewed_plan: dict[str, Any],
    ) -> None:
        if (
            output.reviewed_plan_fingerprint_sha256
            != normalized["reviewed_plan_fingerprint_sha256"]
            or output.research_case_id != UUID(normalized["research_case_id"])
            or output.accepted_industry_map_identity_id
            != UUID(normalized["industry_map_id"])
            or output.accepted_industry_map_revision_id
            != UUID(normalized["industry_map_revision_id"])
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_CONFLICT"
            )
        version = reviewed_plan.get("acceptance_plan_version")
        if version == HISTORICAL_ACCEPTANCE_PLAN_VERSION:
            return
        owner_context = cls._validate_reviewed_owner_context(reviewed_plan)
        cls._validate_submitted_owner_context(normalized, owner_context)
        if (
            output.research_case_id != UUID(owner_context["research_case_id"])
            or output.accepted_industry_map_identity_id
            != UUID(owner_context["industry_map_id"])
            or output.accepted_industry_map_revision_id
            != UUID(owner_context["industry_map_revision_id"])
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_CONFLICT"
            )

    @staticmethod
    def _validate_case_and_map(
        session: Session,
        normalized: dict[str, Any],
        reviewed: IndustryThesisSessionRevision,
        owner_context: dict[str, str],
    ) -> tuple[ResearchCase, IndustryMap, IndustryMapRevision]:
        case_id = UUID(owner_context["research_case_id"])
        map_id = UUID(owner_context["industry_map_id"])
        map_revision_id = UUID(owner_context["industry_map_revision_id"])
        research_case = session.get(ResearchCase, case_id)
        industry_map = session.get(IndustryMap, map_id)
        map_revision = session.get(IndustryMapRevision, map_revision_id)
        if research_case is None or industry_map is None or map_revision is None:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED"
            )
        if industry_map.case_id != research_case.id or map_revision.map_id != industry_map.id:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_MAP_REVISION_MISMATCH"
            )
        cutoff = date.fromisoformat(normalized["information_cutoff_date"])
        if cutoff != reviewed.information_cutoff_date:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_CHRONOLOGY_INVALID",
                "owner-acceptance cutoff must equal the exact reviewed cutoff",
            )
        if map_revision.information_cutoff_date > cutoff:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_CHRONOLOGY_INVALID"
            )
        return research_case, industry_map, map_revision

    @staticmethod
    def _lock_existing_output(
        session: Session,
        *,
        identity: IndustryThesisSessionIdentity,
        normalized: dict[str, Any],
    ) -> IndustryThesisOutputLinkRevision | None:
        key = output_key(normalized)
        output_identity = session.scalar(
            select(IndustryThesisOutputLinkIdentity)
            .where(
                IndustryThesisOutputLinkIdentity.session_id == identity.id,
                IndustryThesisOutputLinkIdentity.output_key == key,
            )
            .with_for_update()
        )
        competing = session.scalar(
            select(IndustryThesisOutputLinkRevision)
            .where(
                IndustryThesisOutputLinkRevision.reviewed_session_revision_id
                == UUID(normalized["reviewed_session_revision_id"])
            )
            .with_for_update()
        )
        if competing is not None:
            if (
                competing.acceptance_plan_fingerprint_sha256
                != normalized["owner_acceptance_plan_fingerprint_sha256"]
                or competing.output_contract_version != OUTPUT_CONTRACT_VERSION
            ):
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_CONFLICT"
                )
            return competing
        if output_identity is None:
            return None
        revision = session.scalar(
            select(IndustryThesisOutputLinkRevision)
            .where(
                IndustryThesisOutputLinkRevision.output_link_id
                == output_identity.id,
                IndustryThesisOutputLinkRevision.revision_number
                == output_identity.latest_revision_number,
            )
            .with_for_update()
        )
        if revision is None:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )
        if (
            revision.reviewed_session_revision_id
            != UUID(normalized["reviewed_session_revision_id"])
            or revision.acceptance_plan_fingerprint_sha256
            != normalized["owner_acceptance_plan_fingerprint_sha256"]
        ):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_CONFLICT"
            )
        return revision

    @staticmethod
    def _validate_candidate_bindings(
        session: Session,
        normalized: dict[str, Any],
        reviewed: IndustryThesisSessionRevision,
        reviewed_plan: dict[str, Any],
    ) -> dict[UUID, IndustryThesisCandidateRevision]:
        selected = reviewed_plan.get("selected_candidates")
        if not isinstance(selected, list):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
            )
        selected_ids = {
            UUID(item["candidate_revision_id"])
            for item in selected
            if isinstance(item, dict)
            and isinstance(item.get("candidate_revision_id"), str)
        }
        binding_ids = {
            UUID(item["reviewed_candidate_revision_id"])
            for item in normalized["candidate_owner_bindings"]
        }
        if selected_ids != binding_ids or len(selected_ids) != len(selected):
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE"
            )
        rows = {
            row.id: row
            for row in session.scalars(
                select(IndustryThesisCandidateRevision)
                .where(IndustryThesisCandidateRevision.id.in_(selected_ids))
                .order_by(IndustryThesisCandidateRevision.id)
                .with_for_update()
            )
        }
        if set(rows) != selected_ids:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE"
            )
        stock_ids: set[int] = set()
        for binding in normalized["candidate_owner_bindings"]:
            row = rows[UUID(binding["reviewed_candidate_revision_id"])]
            if (
                row.session_revision_id != reviewed.id
                or row.review_state != "selected_for_acceptance"
            ):
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE"
                )
            if row.proposed_stock_basic_record_id is None:
                if row.proposed_listed_instrument_id is not None:
                    raise IndustryThesisOwnerAcceptanceError(
                        "INDUSTRY_THESIS_ACCEPTANCE_LISTED_INSTRUMENT_ONLY"
                    )
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_STOCK_IDENTITY_REQUIRED"
                )
            submitted_stock = binding["stage1"]["stock_basic_record_id"]
            if submitted_stock != row.proposed_stock_basic_record_id:
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_STOCK_IDENTITY_REQUIRED"
                )
            if submitted_stock in stock_ids:
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_DUPLICATE_OWNER_IDENTITY"
                )
            stock_ids.add(submitted_stock)
        return rows

    def _recorded_boundary(
        self,
        session: Session,
        normalized: dict[str, Any],
        reviewed: IndustryThesisSessionRevision,
        map_revision: IndustryMapRevision,
    ) -> datetime:
        boundaries = [
            stored_utc(reviewed.recorded_at_utc),
            stored_utc(map_revision.recorded_at_utc),
        ]
        for binding in normalized["candidate_owner_bindings"]:
            stage1 = binding["stage1"]
            expected = stage1.get("expected_latest_revision_id")
            if expected is not None:
                row = session.get(Stage1BeneficiaryRevision, UUID(expected))
                if row is not None:
                    boundaries.append(stored_utc(row.recorded_at_utc))
            semantic = binding["semantic"]
            if (
                binding["semantic_operation"]
                == "append_complete_semantic_profile"
                and semantic["expected_latest_revision_id"] is not None
            ):
                row = session.get(
                    Stage1BeneficiarySemanticProfileRevision,
                    UUID(semantic["expected_latest_revision_id"]),
                )
                if row is not None:
                    boundaries.append(stored_utc(row.recorded_at_utc))
        pool = normalized["candidate_pool_operation"]
        expected_pool = pool.get("expected_latest_revision_id")
        if expected_pool is not None:
            row = session.get(Stage1CandidatePoolRevision, UUID(expected_pool))
            if row is not None:
                boundaries.append(stored_utc(row.recorded_at_utc))
        recorded = max(stored_utc(self._clock()), max(boundaries) + timedelta(microseconds=1))
        if date.fromisoformat(normalized["information_cutoff_date"]) > recorded.date():
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_CHRONOLOGY_INVALID"
            )
        return recorded

    def _lock_owner_targets(
        self,
        session: Session,
        normalized: dict[str, Any],
    ) -> None:
        beneficiary_ids = tuple(
            UUID(binding["stage1"]["beneficiary_id"])
            for binding in normalized["candidate_owner_bindings"]
            if "beneficiary_id" in binding["stage1"]
        )
        self._stage1.lock_identities(
            session,
            beneficiary_ids=beneficiary_ids,
        )
        profile_ids: list[UUID] = []
        for binding in normalized["candidate_owner_bindings"]:
            semantic = binding["semantic"]
            if binding["semantic_operation"] == "reuse_exact_semantic_revision":
                profile_ids.append(UUID(semantic["profile_id"]))
            elif (
                binding["semantic_operation"]
                == "append_complete_semantic_profile"
                and "beneficiary_id" in binding["stage1"]
            ):
                profile = session.scalar(
                    select(Stage1BeneficiarySemanticProfile).where(
                        Stage1BeneficiarySemanticProfile.beneficiary_id
                        == UUID(binding["stage1"]["beneficiary_id"])
                    )
                )
                if profile is not None:
                    profile_ids.append(profile.id)
        self._semantics.lock_profiles(session, tuple(profile_ids))
        pool = normalized["candidate_pool_operation"]
        pool_id = pool.get("candidate_pool_id")
        if pool_id is not None:
            self._stage1.lock_identities(
                session,
                candidate_pool_id=UUID(pool_id),
            )

    def _apply_stage1(
        self,
        session: Session,
        normalized: dict[str, Any],
        binding: dict[str, Any],
        recorded_at: datetime,
    ) -> Stage1BeneficiaryOwnerResult:
        operation = binding["stage1_operation"]
        stage1 = binding["stage1"]
        common = {
            "session": session,
            "selected_map_revision_id": UUID(
                normalized["industry_map_revision_id"]
            ),
            "stock_basic_record_id": stage1["stock_basic_record_id"],
            "information_cutoff_date": date.fromisoformat(
                normalized["information_cutoff_date"]
            ),
            "recorded_at_utc": recorded_at,
        }
        try:
            if operation == "reuse_exact_beneficiary_revision":
                return self._stage1.reuse_beneficiary_revision(
                    **common,
                    beneficiary_id=UUID(stage1["beneficiary_id"]),
                    beneficiary_revision_id=UUID(
                        stage1["beneficiary_revision_id"]
                    ),
                    case_id=UUID(normalized["research_case_id"]),
                    map_id=UUID(normalized["industry_map_id"]),
                )
            assertions = tuple(
                MapAssertionRevisionInput(
                    assertion_kind=item["assertion_kind"],
                    assertion_revision_id=UUID(item["assertion_revision_id"]),
                )
                for item in stage1["map_assertion_revisions"]
            )
            owner_common = {
                **common,
                "beneficiary_kind": stage1["legacy_beneficiary_kind"],
                "assessment_status": stage1["assessment_status"],
                "rationale_summary": stage1["rationale_summary"],
                "assertion_revisions": assertions,
                "claim_revision_ids": tuple(
                    UUID(value) for value in stage1["claim_revision_ids"]
                ),
            }
            if operation == "create_beneficiary_identity_and_revision":
                return self._stage1.create_beneficiary(
                    **owner_common,
                    case_id=UUID(normalized["research_case_id"]),
                    map_id=UUID(normalized["industry_map_id"]),
                    source=stage1["source"],
                    stock_code=stage1["stock_code"],
                )
            return self._stage1.append_beneficiary_revision(
                **owner_common,
                beneficiary_id=UUID(stage1["beneficiary_id"]),
                expected_latest_revision_id=UUID(
                    stage1["expected_latest_revision_id"]
                ),
            )
        except EvidenceLedgerConflictError as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT",
                str(exc),
            ) from exc
        except (EvidenceLedgerNotFound, EvidenceLedgerValidationError) as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_STAGE1_BINDINGS_REQUIRED",
                str(exc),
            ) from exc

    def _apply_semantics(
        self,
        session: Session,
        normalized: dict[str, Any],
        binding: dict[str, Any],
        beneficiary: Stage1BeneficiaryOwnerResult,
        recorded_at: datetime,
    ) -> BeneficiarySemanticOwnerResult | None:
        operation = binding["semantic_operation"]
        if operation == "none":
            return None
        semantic = binding["semantic"]
        try:
            if operation == "reuse_exact_semantic_revision":
                return self._semantics.reuse_exact_revision(
                    session,
                    profile_id=UUID(semantic["profile_id"]),
                    profile_revision_id=UUID(semantic["profile_revision_id"]),
                    beneficiary_id=beneficiary.beneficiary.id,
                    beneficiary_revision_id=beneficiary.revision.id,
                    selected_map_revision_id=UUID(
                        normalized["industry_map_revision_id"]
                    ),
                    information_cutoff_date=date.fromisoformat(
                        normalized["information_cutoff_date"]
                    ),
                    recorded_at_utc=recorded_at,
                )
            payload = {
                **semantic,
                "beneficiary_id": str(beneficiary.beneficiary.id),
                "beneficiary_revision_id": str(beneficiary.revision.id),
                "selected_map_revision_id": normalized[
                    "industry_map_revision_id"
                ],
                "information_cutoff_date": normalized[
                    "information_cutoff_date"
                ],
                "recorded_at_utc": recorded_at.isoformat(),
            }
            return self._semantics.append_complete_profile(session, payload)
        except EvidenceLedgerConflictError as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT",
                str(exc),
            ) from exc
        except (EvidenceLedgerNotFound, EvidenceLedgerValidationError) as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_PAYLOAD_INCOMPLETE",
                str(exc),
            ) from exc

    def _apply_candidate_pool(
        self,
        session: Session,
        normalized: dict[str, Any],
        supported_ids: tuple[UUID, ...],
        recorded_at: datetime,
    ) -> Stage1CandidatePoolOwnerResult | None:
        operation = normalized["candidate_pool_operation"]
        mode = operation["mode"]
        if not supported_ids:
            if mode != "none_no_supported_members":
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH"
                )
            return None
        if mode == "none_no_supported_members":
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH"
            )
        common = {
            "session": session,
            "selected_map_revision_id": UUID(
                normalized["industry_map_revision_id"]
            ),
            "information_cutoff_date": date.fromisoformat(
                normalized["information_cutoff_date"]
            ),
            "beneficiary_revision_ids": supported_ids,
            "recorded_at_utc": recorded_at,
        }
        try:
            if mode == "create_supported_handoff":
                return self._stage1.create_candidate_pool(
                    **common,
                    case_id=UUID(normalized["research_case_id"]),
                    map_id=UUID(normalized["industry_map_id"]),
                    pool_key=operation["pool_key"],
                    title=operation["title"],
                    scope=operation["scope"],
                )
            if mode == "append_supported_handoff":
                return self._stage1.append_candidate_pool_revision(
                    **common,
                    candidate_pool_id=UUID(operation["candidate_pool_id"]),
                    expected_latest_revision_id=UUID(
                        operation["expected_latest_revision_id"]
                    ),
                    title=operation["title"],
                    scope=operation["scope"],
                )
            return self._stage1.reuse_candidate_pool_revision(
                **common,
                candidate_pool_id=UUID(operation["candidate_pool_id"]),
                candidate_pool_revision_id=UUID(
                    operation["candidate_pool_revision_id"]
                ),
                case_id=UUID(normalized["research_case_id"]),
                map_id=UUID(normalized["industry_map_id"]),
            )
        except (EvidenceLedgerConflictError, EvidenceLedgerNotFound) as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT",
                str(exc),
            ) from exc
        except EvidenceLedgerValidationError as exc:
            raise IndustryThesisOwnerAcceptanceError(
                "INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH",
                str(exc),
            ) from exc

    @staticmethod
    def _output_bindings(
        owner_rows: list[
            tuple[
                dict[str, Any],
                IndustryThesisCandidateRevision,
                Stage1BeneficiaryOwnerResult,
                BeneficiarySemanticOwnerResult | None,
            ]
        ],
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for binding, _reviewed, beneficiary, semantic in owner_rows:
            supported = beneficiary.revision.assessment_status == "supported"
            reasons: list[str] = []
            if semantic is None:
                reasons.append("typed_semantics_missing")
            if not supported:
                reasons.append(
                    f"stage1_status_{beneficiary.revision.assessment_status}"
                )
            result.append(
                {
                    "sequence": binding["sequence"],
                    "reviewed_candidate_revision_id": binding[
                        "reviewed_candidate_revision_id"
                    ],
                    "operation_key_sha256": binding["operation_key_sha256"],
                    "stage1_operation": binding["stage1_operation"],
                    "beneficiary_id": str(beneficiary.beneficiary.id),
                    "beneficiary_revision_id": str(beneficiary.revision.id),
                    "stock_basic_record_id": beneficiary.revision.stock_basic_record_id,
                    "legacy_beneficiary_kind": beneficiary.revision.beneficiary_kind,
                    "assessment_status": beneficiary.revision.assessment_status,
                    "semantic_operation": binding["semantic_operation"],
                    "semantic_profile_id": (
                        None if semantic is None else str(semantic.profile.id)
                    ),
                    "semantic_profile_revision_id": (
                        None if semantic is None else str(semantic.revision.id)
                    ),
                    "included_in_supported_handoff": supported,
                    "supported_handoff_reason": (
                        "stage1_supported"
                        if supported
                        else f"stage1_{beneficiary.revision.assessment_status}"
                    ),
                    "readiness_reason_codes": reasons,
                    "readiness_note": binding["readiness_note"],
                }
            )
        result.sort(
            key=lambda item: (
                item["sequence"],
                item["reviewed_candidate_revision_id"],
            )
        )
        return result

    @staticmethod
    def _append_accepted_session(
        session: Session,
        *,
        identity: IndustryThesisSessionIdentity,
        reviewed: IndustryThesisSessionRevision,
        normalized: dict[str, Any],
        accepted_result: dict[str, Any],
        accepted_session_id: UUID,
        output_revision_id: UUID,
        recorded_at: datetime,
    ) -> IndustryThesisSessionRevision:
        reviewed_graph = json_value(reviewed.draft_graph_json, "draft_graph")
        reviewed_plan = reviewed_graph["acceptance_plan_preview"]
        payload = session_revision_to_input(reviewed)
        payload["workflow_state"] = "accepted_outputs_linked"
        payload["draft_graph"] = {
            "base_draft_graph": reviewed_graph.get("base_draft_graph", {}),
            "reviewed_acceptance_plan": reviewed_plan,
            "owner_acceptance_plan": owner_plan_canonical_value(normalized),
            "owner_acceptance_result": accepted_result,
            "output_link_revision_id": str(output_revision_id),
        }
        payload["revision_note"] = normalized["revision_note"]
        data = normalize_session_payload(payload)
        accepted = IndustryThesisSessionRevision(
            id=accepted_session_id,
            session_id=identity.id,
            revision_number=identity.latest_revision_number + 1,
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
            supersedes_revision_id=reviewed.id,
            revision_note=data["revision_note"],
        )
        session.add(accepted)
        session.flush()
        identity.latest_revision_number = accepted.revision_number
        session.flush()
        return accepted

    @staticmethod
    def _append_output_link(
        session: Session,
        *,
        identity: IndustryThesisSessionIdentity,
        reviewed: IndustryThesisSessionRevision,
        accepted_session: IndustryThesisSessionRevision,
        normalized: dict[str, Any],
        accepted_result: dict[str, Any],
        output_identity_id: UUID,
        output_revision_id: UUID,
        transaction_id: UUID,
        pool_result: Stage1CandidatePoolOwnerResult | None,
        recorded_at: datetime,
    ) -> tuple[IndustryThesisOutputLinkIdentity, IndustryThesisOutputLinkRevision]:
        output_identity = IndustryThesisOutputLinkIdentity(
            id=output_identity_id,
            session_id=identity.id,
            output_key=output_key(normalized),
            created_recorded_utc=recorded_at,
            latest_revision_number=0,
        )
        session.add(output_identity)
        session.flush()
        bindings = accepted_result["ordered_owner_output_bindings"]
        revision = IndustryThesisOutputLinkRevision(
            id=output_revision_id,
            output_link_id=output_identity.id,
            revision_number=1,
            session_revision_id=accepted_session.id,
            accepted_session_revision_id=accepted_session.id,
            reviewed_session_revision_id=reviewed.id,
            research_case_id=UUID(normalized["research_case_id"]),
            accepted_industry_map_identity_id=UUID(
                normalized["industry_map_id"]
            ),
            accepted_industry_map_revision_id=UUID(
                normalized["industry_map_revision_id"]
            ),
            accepted_candidate_pool_revision_id=(
                None if pool_result is None else pool_result.revision.id
            ),
            output_contract_version=OUTPUT_CONTRACT_VERSION,
            reviewed_plan_fingerprint_sha256=normalized[
                "reviewed_plan_fingerprint_sha256"
            ],
            ordered_beneficiary_revision_ids_json=canonical_json_text(
                [item["beneficiary_revision_id"] for item in bindings],
                "ordered beneficiary revision IDs",
            ),
            ordered_owner_output_bindings_json=canonical_json_text(
                bindings,
                "ordered owner output bindings",
            ),
            coverage_state=reviewed.coverage_state,
            acceptance_plan_fingerprint_sha256=normalized[
                "owner_acceptance_plan_fingerprint_sha256"
            ],
            owner_transaction_id=str(transaction_id),
            information_cutoff_date=date.fromisoformat(
                normalized["information_cutoff_date"]
            ),
            recorded_at_utc=recorded_at,
            supersedes_output_link_revision_id=None,
        )
        session.add(revision)
        output_identity.latest_revision_number = 1
        session.flush()
        return output_identity, revision

    @staticmethod
    def _preview_operation_summary(
        row: tuple[
            dict[str, Any],
            IndustryThesisCandidateRevision,
            Stage1BeneficiaryOwnerResult,
            BeneficiarySemanticOwnerResult | None,
        ],
        *,
        dry_run: bool,
    ) -> dict[str, Any]:
        binding, _reviewed, beneficiary, semantic = row
        reused_stage1 = (
            binding["stage1_operation"] == "reuse_exact_beneficiary_revision"
        )
        reused_semantic = (
            binding["semantic_operation"] == "reuse_exact_semantic_revision"
        )
        return {
            "sequence": binding["sequence"],
            "reviewed_candidate_revision_id": binding[
                "reviewed_candidate_revision_id"
            ],
            "operation_key_sha256": binding["operation_key_sha256"],
            "stage1_operation": binding["stage1_operation"],
            "beneficiary_id": (
                str(beneficiary.beneficiary.id)
                if not dry_run or reused_stage1
                else None
            ),
            "beneficiary_revision_id": (
                str(beneficiary.revision.id)
                if not dry_run or reused_stage1
                else None
            ),
            "assessment_status": beneficiary.revision.assessment_status,
            "semantic_operation": binding["semantic_operation"],
            "semantic_profile_id": (
                None
                if semantic is None or (dry_run and not reused_semantic)
                else str(semantic.profile.id)
            ),
            "semantic_profile_revision_id": (
                None
                if semantic is None or (dry_run and not reused_semantic)
                else str(semantic.revision.id)
            ),
            "included_in_supported_handoff": (
                beneficiary.revision.assessment_status == "supported"
            ),
        }

    @staticmethod
    def _idempotent_result(
        output: IndustryThesisOutputLinkRevision,
        normalized: dict[str, Any],
        *,
        dry_run: bool,
    ) -> dict[str, Any]:
        bindings = json_value(
            output.ordered_owner_output_bindings_json,
            "ordered owner output bindings",
        )
        return {
            "dry_run": dry_run,
            "commit_ready": True,
            "idempotent_replay": True,
            "owner_acceptance_plan_version": normalized[
                "owner_acceptance_plan_version"
            ],
            "owner_acceptance_plan_fingerprint_sha256": normalized[
                "owner_acceptance_plan_fingerprint_sha256"
            ],
            "preview_fingerprint_sha256": normalized[
                "owner_acceptance_plan_fingerprint_sha256"
            ],
            "reviewed_session_revision_id": str(
                output.reviewed_session_revision_id
            ),
            "accepted_session_revision_id": str(
                output.accepted_session_revision_id
            ),
            "output_link_id": str(output.output_link_id),
            "output_link_revision_id": str(output.id),
            "owner_transaction_id": output.owner_transaction_id,
            "research_case_id": str(output.research_case_id),
            "industry_map_id": str(output.accepted_industry_map_identity_id),
            "industry_map_revision_id": str(
                output.accepted_industry_map_revision_id
            ),
            "complete_universe_count": len(bindings),
            "supported_handoff_count": sum(
                bool(item["included_in_supported_handoff"])
                for item in bindings
            ),
            "candidate_pool_mode": normalized["candidate_pool_operation"]["mode"],
            "accepted_candidate_pool_revision_id": (
                None
                if output.accepted_candidate_pool_revision_id is None
                else str(output.accepted_candidate_pool_revision_id)
            ),
            "operation_summaries": bindings,
            "blocked_reasons": [],
            "recorded_at_utc": stored_utc(output.recorded_at_utc).isoformat(),
        }

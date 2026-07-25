"""Session-bound write port for typed beneficiary evidence semantics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.beneficiary_semantics_commands import (
    BeneficiarySemanticCommandService,
    _normalize_input,
    _stored_utc,
)
from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticAssertion,
    Stage1BeneficiarySemanticAssertionClaimLink,
    Stage1BeneficiarySemanticProfile,
    Stage1BeneficiarySemanticProfileRevision,
    Stage1BeneficiarySemanticVerificationItem,
)
from industry_alpha.errors import (
    EvidenceLedgerNotFound,
    EvidenceLedgerValidationError,
)


@dataclass(frozen=True)
class BeneficiarySemanticOwnerResult:
    profile: Stage1BeneficiarySemanticProfile
    revision: Stage1BeneficiarySemanticProfileRevision
    assertion_count: int
    claim_link_count: int
    verification_item_count: int


class _ExistingSessionScope:
    """Yield one caller-owned session without ending its transaction."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def __enter__(self) -> Session:
        return self._session

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _traceback: TracebackType | None,
    ) -> bool:
        return False


class _ExistingSessionFactory:
    """Adapt a caller-owned session to the public command's transaction scope.

    ``begin`` intentionally returns a no-op context over the existing session.
    The outer Industry Thesis coordinator remains the only transaction owner;
    this adapter performs no commit, rollback, close, or nested transaction.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def begin(self) -> _ExistingSessionScope:
        return _ExistingSessionScope(self._session)


class BeneficiarySemanticOwnerWritePort:
    """Apply semantic owner operations inside a caller-owned transaction."""

    def __init__(self, _session_factory: sessionmaker[Session]) -> None:
        # The public constructor shape remains aligned with other owner ports.
        # Application writes always receive the explicit caller-owned session.
        pass

    @staticmethod
    def normalize(raw: dict[str, object]) -> dict[str, object]:
        return _normalize_input(raw)

    def lock_profiles(
        self,
        session: Session,
        profile_ids: tuple[UUID, ...],
    ) -> None:
        for profile_id in sorted(set(profile_ids), key=str):
            profile = session.scalar(
                select(Stage1BeneficiarySemanticProfile)
                .where(Stage1BeneficiarySemanticProfile.id == profile_id)
                .with_for_update()
            )
            if profile is None:
                raise EvidenceLedgerNotFound(
                    f"typed beneficiary semantic profile {profile_id} was not found"
                )

    def reuse_exact_revision(
        self,
        session: Session,
        *,
        profile_id: UUID,
        profile_revision_id: UUID,
        beneficiary_id: UUID,
        beneficiary_revision_id: UUID,
        selected_map_revision_id: UUID,
        information_cutoff_date: date,
        recorded_at_utc: datetime,
    ) -> BeneficiarySemanticOwnerResult:
        profile = session.scalar(
            select(Stage1BeneficiarySemanticProfile)
            .where(Stage1BeneficiarySemanticProfile.id == profile_id)
            .with_for_update()
        )
        if profile is None or profile.beneficiary_id != beneficiary_id:
            raise EvidenceLedgerNotFound(
                "exact typed beneficiary semantic profile was not found"
            )
        revision = session.get(
            Stage1BeneficiarySemanticProfileRevision,
            profile_revision_id,
        )
        if revision is None or revision.profile_id != profile.id:
            raise EvidenceLedgerNotFound(
                "exact typed beneficiary semantic profile revision was not found"
            )
        if revision.beneficiary_revision_id != beneficiary_revision_id:
            raise EvidenceLedgerValidationError(
                "semantic revision must freeze the exact accepted beneficiary revision"
            )
        if revision.selected_map_revision_id != selected_map_revision_id:
            raise EvidenceLedgerValidationError(
                "semantic revision must freeze the exact selected map revision"
            )
        if revision.information_cutoff_date > information_cutoff_date:
            raise EvidenceLedgerValidationError(
                "semantic revision exceeds the owner-acceptance cutoff"
            )
        if _stored_utc(revision.recorded_at_utc) > _stored_utc(recorded_at_utc):
            raise EvidenceLedgerValidationError(
                "semantic revision exceeds the owner-acceptance recorded boundary"
            )
        assertions = list(
            session.scalars(
                select(Stage1BeneficiarySemanticAssertion).where(
                    Stage1BeneficiarySemanticAssertion.profile_revision_id
                    == revision.id
                )
            )
        )
        assertion_ids = [item.id for item in assertions]
        claim_link_count = 0
        if assertion_ids:
            claim_link_count = len(
                list(
                    session.scalars(
                        select(Stage1BeneficiarySemanticAssertionClaimLink).where(
                            Stage1BeneficiarySemanticAssertionClaimLink.assertion_id.in_(
                                assertion_ids
                            )
                        )
                    )
                )
            )
        verification_count = len(
            list(
                session.scalars(
                    select(Stage1BeneficiarySemanticVerificationItem).where(
                        Stage1BeneficiarySemanticVerificationItem.profile_revision_id
                        == revision.id
                    )
                )
            )
        )
        return BeneficiarySemanticOwnerResult(
            profile=profile,
            revision=revision,
            assertion_count=len(assertions),
            claim_link_count=claim_link_count,
            verification_item_count=verification_count,
        )

    def append_complete_profile(
        self,
        session: Session,
        raw: dict[str, object],
    ) -> BeneficiarySemanticOwnerResult:
        """Reuse the public owner's exact normalize/validate/apply path.

        The adapter supplies the existing SQLAlchemy session and deliberately
        performs no transaction-finalization behavior. This keeps public command
        behavior and cross-owner application logic identical while preserving
        one outer atomic Industry Thesis transaction.
        """

        result = BeneficiarySemanticCommandService(
            _ExistingSessionFactory(session)  # type: ignore[arg-type]
        ).record(raw)
        profile = session.get(
            Stage1BeneficiarySemanticProfile,
            UUID(result["profile_id"]),
        )
        revision = session.get(
            Stage1BeneficiarySemanticProfileRevision,
            UUID(result["profile_revision_id"]),
        )
        if profile is None or revision is None or revision.profile_id != profile.id:
            raise EvidenceLedgerValidationError(
                "typed semantic owner result is incomplete after application"
            )
        return BeneficiarySemanticOwnerResult(
            profile=profile,
            revision=revision,
            assertion_count=result["assertion_count"],
            claim_link_count=result["claim_link_count"],
            verification_item_count=result["verification_item_count"],
        )

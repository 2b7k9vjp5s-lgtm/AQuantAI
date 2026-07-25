"""Session-bound write port for typed beneficiary evidence semantics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.beneficiary_semantics_commands import (
    BeneficiarySemanticCommandService,
    _normalize_input,
    _stored_utc,
)
from industry_alpha.beneficiary_semantics_contracts import TAXONOMY_VERSION
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


class BeneficiarySemanticOwnerWritePort:
    """Apply semantic owner operations inside a caller-owned transaction."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._owner = BeneficiarySemanticCommandService(session_factory)

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
        normalized = _normalize_input(raw)
        context = self._owner._validate_database(session, normalized, lock=True)
        profile = context["profile"]
        latest = context["latest_revision"]
        recorded = normalized["recorded_at_utc"]
        if profile is None:
            profile = Stage1BeneficiarySemanticProfile(
                beneficiary_id=normalized["beneficiary_id"],
                created_at_utc=recorded,
            )
            session.add(profile)
            session.flush()
        revision = Stage1BeneficiarySemanticProfileRevision(
            profile_id=profile.id,
            revision_no=1 if latest is None else latest.revision_no + 1,
            beneficiary_revision_id=normalized["beneficiary_revision_id"],
            selected_map_revision_id=normalized["selected_map_revision_id"],
            taxonomy_version=TAXONOMY_VERSION,
            overall_status=normalized["overall_status"],
            summary=normalized["summary"],
            recorded_by=normalized["recorded_by"],
            information_cutoff_date=normalized["information_cutoff_date"],
            recorded_at_utc=recorded,
            supersedes_revision_id=None if latest is None else latest.id,
        )
        session.add(revision)
        session.flush()

        assertion_by_key: dict[str, Stage1BeneficiarySemanticAssertion] = {}
        claim_link_count = 0
        for item in normalized["assertions"]:
            assertion = Stage1BeneficiarySemanticAssertion(
                profile_revision_id=revision.id,
                assertion_key=item["assertion_key"],
                field_kind=item["field_kind"],
                state_code=item["state_code"],
                evidence_state=item["evidence_state"],
                subject_text=item["subject_text"],
                rationale=item["rationale"],
                map_observation_revision_id=item["map_observation_revision_id"],
                position=item["position"],
            )
            session.add(assertion)
            session.flush()
            assertion_by_key[item["assertion_key"]] = assertion
            for claim_link in item["claim_links"]:
                session.add(
                    Stage1BeneficiarySemanticAssertionClaimLink(
                        assertion_id=assertion.id,
                        claim_revision_id=claim_link["claim_revision_id"],
                        relation=claim_link["relation"],
                        recorded_at_utc=recorded,
                    )
                )
                claim_link_count += 1

        for item in normalized["verification_items"]:
            assertion = (
                None
                if item["assertion_key"] is None
                else assertion_by_key[item["assertion_key"]]
            )
            session.add(
                Stage1BeneficiarySemanticVerificationItem(
                    profile_revision_id=revision.id,
                    assertion_id=None if assertion is None else assertion.id,
                    verification_question=item["verification_question"],
                    expected_evidence_type=item["expected_evidence_type"],
                    status="open",
                    recorded_at_utc=recorded,
                )
            )
        session.flush()
        return BeneficiarySemanticOwnerResult(
            profile=profile,
            revision=revision,
            assertion_count=len(normalized["assertions"]),
            claim_link_count=claim_link_count,
            verification_item_count=len(normalized["verification_items"]),
        )

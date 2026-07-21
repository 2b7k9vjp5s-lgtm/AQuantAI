"""Read-only repository for typed beneficiary semantic history."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticAssertion,
    Stage1BeneficiarySemanticAssertionClaimLink,
    Stage1BeneficiarySemanticProfile,
    Stage1BeneficiarySemanticProfileRevision,
    Stage1BeneficiarySemanticVerificationItem,
)
from industry_alpha.chain_map_models import (
    IndustryMapObservation,
    IndustryMapObservationRevision,
    IndustryMapRevision,
)
from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem
from industry_alpha.stage1_models import Stage1Beneficiary, Stage1BeneficiaryRevision


@dataclass(frozen=True)
class BeneficiarySemanticRows:
    beneficiary: Stage1Beneficiary
    profile: Stage1BeneficiarySemanticProfile
    profile_revisions: tuple
    beneficiary_revisions: tuple
    map_revisions: tuple
    assertions: tuple
    assertion_claim_links: tuple
    verification_items: tuple
    observation_revisions: tuple
    observations: tuple
    claim_revisions: tuple
    claims: tuple
    claim_evidence_links: tuple
    evidence_items: tuple


class BeneficiarySemanticRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def beneficiary_exists(self, beneficiary_id: UUID) -> bool:
        return self._session.get(Stage1Beneficiary, beneficiary_id) is not None

    def load(self, beneficiary_id: UUID) -> BeneficiarySemanticRows | None:
        beneficiary = self._session.get(Stage1Beneficiary, beneficiary_id)
        if beneficiary is None:
            return None
        profile = self._session.scalar(
            select(Stage1BeneficiarySemanticProfile).where(
                Stage1BeneficiarySemanticProfile.beneficiary_id == beneficiary_id
            )
        )
        if profile is None:
            return None
        revisions = tuple(
            self._session.scalars(
                select(Stage1BeneficiarySemanticProfileRevision)
                .where(Stage1BeneficiarySemanticProfileRevision.profile_id == profile.id)
                .order_by(Stage1BeneficiarySemanticProfileRevision.revision_no)
            )
        )
        revision_ids = [item.id for item in revisions]
        assertions = self._rows(
            Stage1BeneficiarySemanticAssertion,
            Stage1BeneficiarySemanticAssertion.profile_revision_id,
            revision_ids,
            Stage1BeneficiarySemanticAssertion.profile_revision_id,
            Stage1BeneficiarySemanticAssertion.field_kind,
            Stage1BeneficiarySemanticAssertion.position,
            Stage1BeneficiarySemanticAssertion.assertion_key,
        )
        assertion_ids = [item.id for item in assertions]
        assertion_claim_links = self._rows(
            Stage1BeneficiarySemanticAssertionClaimLink,
            Stage1BeneficiarySemanticAssertionClaimLink.assertion_id,
            assertion_ids,
            Stage1BeneficiarySemanticAssertionClaimLink.assertion_id,
            Stage1BeneficiarySemanticAssertionClaimLink.relation,
            Stage1BeneficiarySemanticAssertionClaimLink.claim_revision_id,
        )
        verification_items = self._rows(
            Stage1BeneficiarySemanticVerificationItem,
            Stage1BeneficiarySemanticVerificationItem.profile_revision_id,
            revision_ids,
            Stage1BeneficiarySemanticVerificationItem.profile_revision_id,
            Stage1BeneficiarySemanticVerificationItem.recorded_at_utc,
            Stage1BeneficiarySemanticVerificationItem.id,
        )
        beneficiary_revisions = self._identities(
            Stage1BeneficiaryRevision,
            {item.beneficiary_revision_id for item in revisions},
            Stage1BeneficiaryRevision.revision_no,
        )
        map_revisions = self._identities(
            IndustryMapRevision,
            {item.selected_map_revision_id for item in revisions},
            IndustryMapRevision.revision_no,
        )
        observation_revisions = self._identities(
            IndustryMapObservationRevision,
            {
                item.map_observation_revision_id
                for item in assertions
                if item.map_observation_revision_id is not None
            },
            IndustryMapObservationRevision.observation_id,
            IndustryMapObservationRevision.revision_no,
        )
        observations = self._identities(
            IndustryMapObservation,
            {item.observation_id for item in observation_revisions},
            IndustryMapObservation.observation_kind,
            IndustryMapObservation.observation_key,
        )
        claim_revisions = self._identities(
            ClaimRevision,
            {item.claim_revision_id for item in assertion_claim_links},
            ClaimRevision.claim_id,
            ClaimRevision.revision_no,
        )
        claims = self._identities(
            Claim,
            {item.claim_id for item in claim_revisions},
            Claim.claim_key,
        )
        claim_evidence_links = self._rows(
            ClaimEvidenceLink,
            ClaimEvidenceLink.claim_revision_id,
            [item.id for item in claim_revisions],
            ClaimEvidenceLink.claim_revision_id,
            ClaimEvidenceLink.relation,
            ClaimEvidenceLink.evidence_id,
        )
        evidence_items = self._identities(
            EvidenceItem,
            {item.evidence_id for item in claim_evidence_links},
            EvidenceItem.information_date,
            EvidenceItem.recorded_at_utc,
            EvidenceItem.id,
        )
        return BeneficiarySemanticRows(
            beneficiary,
            profile,
            revisions,
            beneficiary_revisions,
            map_revisions,
            assertions,
            assertion_claim_links,
            verification_items,
            observation_revisions,
            observations,
            claim_revisions,
            claims,
            claim_evidence_links,
            evidence_items,
        )

    def _rows(self, model, column, ids, *order_by):
        if not ids:
            return ()
        return tuple(
            self._session.scalars(
                select(model).where(column.in_(ids)).order_by(*order_by)
            )
        )

    def _identities(self, model, ids, *order_by):
        return self._rows(model, model.id, sorted(ids, key=str), *order_by)

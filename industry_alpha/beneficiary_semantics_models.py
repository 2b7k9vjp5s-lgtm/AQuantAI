"""Append-only persistence models for typed beneficiary evidence semantics v1."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    event,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.database.models import Base
from industry_alpha.errors import EvidenceLedgerImmutableError


class Stage1BeneficiarySemanticProfile(Base):
    __tablename__ = "stage1_beneficiary_semantic_profiles"
    __table_args__ = (
        UniqueConstraint("beneficiary_id", name="uq_stage1_beneficiary_semantic_profile"),
        Index("ix_stage1_beneficiary_semantic_profile", "beneficiary_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    beneficiary_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiaries.id", ondelete="RESTRICT"), nullable=False
    )
    created_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage1BeneficiarySemanticProfileRevision(Base):
    __tablename__ = "stage1_beneficiary_semantic_profile_revisions"
    __table_args__ = (
        UniqueConstraint(
            "profile_id", "revision_no", name="uq_stage1_beneficiary_semantic_revision_no"
        ),
        CheckConstraint(
            "revision_no > 0", name="ck_stage1_beneficiary_semantic_revision_positive"
        ),
        CheckConstraint(
            "taxonomy_version = 'aquantai.typed-beneficiary-evidence-semantics.v1'",
            name="ck_stage1_beneficiary_semantic_taxonomy_version",
        ),
        CheckConstraint(
            "overall_status IN ('draft','supported','disputed','rejected')",
            name="ck_stage1_beneficiary_semantic_overall_status",
        ),
        Index(
            "ix_stage1_beneficiary_semantic_revision", "profile_id", "revision_no"
        ),
        Index(
            "ix_stage1_beneficiary_semantic_frozen",
            "beneficiary_revision_id",
            "selected_map_revision_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiary_semantic_profiles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    beneficiary_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiary_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    selected_map_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_map_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    taxonomy_version: Mapped[str] = mapped_column(String(96), nullable=False)
    overall_status: Mapped[str] = mapped_column(String(16), nullable=False)
    summary: Mapped[str] = mapped_column(String(4000), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(100), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "stage1_beneficiary_semantic_profile_revisions.id", ondelete="RESTRICT"
        )
    )


class Stage1BeneficiarySemanticAssertion(Base):
    __tablename__ = "stage1_beneficiary_semantic_assertions"
    __table_args__ = (
        UniqueConstraint(
            "profile_revision_id",
            "assertion_key",
            name="uq_stage1_beneficiary_semantic_assertion_key",
        ),
        CheckConstraint(
            "field_kind IN ('exposure','driver','offering','customer','certification','capacity','production','order')",
            name="ck_stage1_beneficiary_semantic_field_kind",
        ),
        CheckConstraint(
            "evidence_state IN ('supported','disputed','missing','not_applicable')",
            name="ck_stage1_beneficiary_semantic_evidence_state",
        ),
        CheckConstraint("position >= 0", name="ck_stage1_beneficiary_semantic_position"),
        CheckConstraint(
            "(field_kind = 'driver' AND map_observation_revision_id IS NOT NULL) OR "
            "(field_kind <> 'driver' AND map_observation_revision_id IS NULL)",
            name="ck_stage1_beneficiary_semantic_driver_observation",
        ),
        Index(
            "ix_stage1_beneficiary_semantic_assertion",
            "profile_revision_id",
            "field_kind",
            "position",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    profile_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "stage1_beneficiary_semantic_profile_revisions.id", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    assertion_key: Mapped[str] = mapped_column(String(96), nullable=False)
    field_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    state_code: Mapped[str] = mapped_column(String(96), nullable=False)
    evidence_state: Mapped[str] = mapped_column(String(24), nullable=False)
    subject_text: Mapped[str | None] = mapped_column(String(500))
    rationale: Mapped[str] = mapped_column(String(4000), nullable=False)
    map_observation_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_map_observation_revisions.id", ondelete="RESTRICT")
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class Stage1BeneficiarySemanticAssertionClaimLink(Base):
    __tablename__ = "stage1_beneficiary_semantic_assertion_claim_links"
    __table_args__ = (
        UniqueConstraint(
            "assertion_id",
            "claim_revision_id",
            "relation",
            name="uq_stage1_beneficiary_semantic_assertion_claim",
        ),
        CheckConstraint(
            "relation IN ('support','contradict','context')",
            name="ck_stage1_beneficiary_semantic_claim_relation",
        ),
        Index(
            "ix_stage1_beneficiary_semantic_assertion_claim",
            "assertion_id",
            "relation",
            "claim_revision_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    assertion_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiary_semantic_assertions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    claim_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    relation: Mapped[str] = mapped_column(String(16), nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Stage1BeneficiarySemanticVerificationItem(Base):
    __tablename__ = "stage1_beneficiary_semantic_verification_items"
    __table_args__ = (
        CheckConstraint(
            "status = 'open'", name="ck_stage1_beneficiary_semantic_verification_open"
        ),
        Index(
            "ix_stage1_beneficiary_semantic_verification",
            "profile_revision_id",
            "assertion_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    profile_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "stage1_beneficiary_semantic_profile_revisions.id", ondelete="RESTRICT"
        ),
        nullable=False,
    )
    assertion_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage1_beneficiary_semantic_assertions.id", ondelete="RESTRICT")
    )
    verification_question: Mapped[str] = mapped_column(String(2000), nullable=False)
    expected_evidence_type: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


BENEFICIARY_SEMANTIC_MODELS = (
    Stage1BeneficiarySemanticProfile,
    Stage1BeneficiarySemanticProfileRevision,
    Stage1BeneficiarySemanticAssertion,
    Stage1BeneficiarySemanticAssertionClaimLink,
    Stage1BeneficiarySemanticVerificationItem,
)


@event.listens_for(Session, "before_flush")
def reject_beneficiary_semantic_mutation(
    session: Session, _flush_context: object, _instances: object
) -> None:
    """Reject ordinary ORM updates and deletes for accepted semantic history."""
    for row in session.deleted:
        if isinstance(row, BENEFICIARY_SEMANTIC_MODELS):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be deleted."
            )
    for row in session.dirty:
        if isinstance(row, BENEFICIARY_SEMANTIC_MODELS) and session.is_modified(
            row, include_collections=False
        ):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be updated."
            )

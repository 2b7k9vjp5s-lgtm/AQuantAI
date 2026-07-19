"""Append-only Stage 1 beneficiary and candidate-pool persistence models."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
    event,
    text,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.database.models import Base, IDENTITY_TYPE
from industry_alpha.errors import EvidenceLedgerImmutableError


class Stage1Beneficiary(Base):
    __tablename__ = "stage1_beneficiaries"
    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "map_id",
            "source",
            "stock_code",
            name="uq_stage1_beneficiary_identity",
        ),
        Index(
            "ix_stage1_beneficiary_map_stock",
            "map_id",
            "source",
            "stock_code",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_cases.id", ondelete="RESTRICT"), nullable=False
    )
    map_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_maps.id", ondelete="RESTRICT"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class Stage1BeneficiaryRevision(Base):
    __tablename__ = "stage1_beneficiary_revisions"
    __table_args__ = (
        UniqueConstraint(
            "beneficiary_id", "revision_no", name="uq_stage1_beneficiary_revision_no"
        ),
        UniqueConstraint(
            "id", "beneficiary_id", name="uq_stage1_beneficiary_revision_identity"
        ),
        CheckConstraint(
            "revision_no > 0", name="ck_stage1_beneficiary_revision_positive"
        ),
        CheckConstraint(
            "beneficiary_kind IN ('direct','secondary','potential')",
            name="ck_stage1_beneficiary_kind",
        ),
        CheckConstraint(
            "assessment_status IN ('draft','supported','disputed','rejected')",
            name="ck_stage1_beneficiary_status",
        ),
        Index(
            "ix_stage1_beneficiary_revision",
            "beneficiary_id",
            "revision_no",
        ),
        Index(
            "ix_stage1_beneficiary_map_snapshot",
            "selected_map_revision_id",
            "stock_basic_record_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    beneficiary_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiaries.id", ondelete="RESTRICT"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_map_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_map_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    stock_basic_record_id: Mapped[int] = mapped_column(
        IDENTITY_TYPE,
        ForeignKey("stock_basic.id", ondelete="RESTRICT"),
        nullable=False,
    )
    beneficiary_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    assessment_status: Mapped[str] = mapped_column(String(16), nullable=False)
    rationale_summary: Mapped[str] = mapped_column(String(4000), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage1_beneficiary_revisions.id", ondelete="RESTRICT")
    )


class Stage1BeneficiaryAssertionLink(Base):
    __tablename__ = "stage1_beneficiary_assertion_links"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN node_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN relationship_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN observation_revision_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_stage1_assertion_link_one_target",
        ),
        Index(
            "uq_stage1_node_assertion_link",
            "beneficiary_revision_id",
            "node_revision_id",
            unique=True,
            postgresql_where=text("node_revision_id IS NOT NULL"),
            sqlite_where=text("node_revision_id IS NOT NULL"),
        ),
        Index(
            "uq_stage1_relationship_assertion_link",
            "beneficiary_revision_id",
            "relationship_revision_id",
            unique=True,
            postgresql_where=text("relationship_revision_id IS NOT NULL"),
            sqlite_where=text("relationship_revision_id IS NOT NULL"),
        ),
        Index(
            "uq_stage1_observation_assertion_link",
            "beneficiary_revision_id",
            "observation_revision_id",
            unique=True,
            postgresql_where=text("observation_revision_id IS NOT NULL"),
            sqlite_where=text("observation_revision_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    beneficiary_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiary_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    node_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_map_node_revisions.id", ondelete="RESTRICT")
    )
    relationship_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_map_relationship_revisions.id", ondelete="RESTRICT")
    )
    observation_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_map_observation_revisions.id", ondelete="RESTRICT")
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class Stage1BeneficiaryClaimLink(Base):
    __tablename__ = "stage1_beneficiary_claim_links"
    __table_args__ = (
        UniqueConstraint(
            "beneficiary_revision_id",
            "claim_revision_id",
            name="uq_stage1_beneficiary_claim_link",
        ),
        Index(
            "ix_stage1_beneficiary_claim_link",
            "beneficiary_revision_id",
            "claim_revision_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    beneficiary_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_beneficiary_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    claim_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class Stage1CandidatePool(Base):
    __tablename__ = "stage1_candidate_pools"
    __table_args__ = (
        UniqueConstraint(
            "case_id", "map_id", "pool_key", name="uq_stage1_candidate_pool_key"
        ),
        Index("ix_stage1_candidate_pool_map", "map_id", "pool_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_cases.id", ondelete="RESTRICT"), nullable=False
    )
    map_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_maps.id", ondelete="RESTRICT"), nullable=False
    )
    pool_key: Mapped[str] = mapped_column(String(96), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class Stage1CandidatePoolRevision(Base):
    __tablename__ = "stage1_candidate_pool_revisions"
    __table_args__ = (
        UniqueConstraint(
            "candidate_pool_id",
            "revision_no",
            name="uq_stage1_candidate_pool_revision_no",
        ),
        CheckConstraint(
            "revision_no > 0", name="ck_stage1_candidate_pool_revision_positive"
        ),
        Index(
            "ix_stage1_candidate_pool_revision",
            "candidate_pool_id",
            "revision_no",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    candidate_pool_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_candidate_pools.id", ondelete="RESTRICT"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    selected_map_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_map_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    scope: Mapped[str] = mapped_column(String(4000), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("stage1_candidate_pool_revisions.id", ondelete="RESTRICT")
    )


class Stage1CandidatePoolMembership(Base):
    __tablename__ = "stage1_candidate_pool_memberships"
    __table_args__ = (
        UniqueConstraint(
            "candidate_pool_revision_id",
            "beneficiary_id",
            name="uq_stage1_pool_beneficiary_identity",
        ),
        UniqueConstraint(
            "candidate_pool_revision_id",
            "beneficiary_revision_id",
            name="uq_stage1_pool_beneficiary_revision",
        ),
        ForeignKeyConstraint(
            ["beneficiary_revision_id", "beneficiary_id"],
            ["stage1_beneficiary_revisions.id", "stage1_beneficiary_revisions.beneficiary_id"],
            name="fk_stage1_pool_membership_exact_revision",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_stage1_candidate_pool_membership",
            "candidate_pool_revision_id",
            "beneficiary_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    candidate_pool_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_candidate_pool_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    beneficiary_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    beneficiary_revision_id: Mapped[UUID] = mapped_column(Uuid, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


STAGE1_MODELS = (
    Stage1Beneficiary,
    Stage1BeneficiaryRevision,
    Stage1BeneficiaryAssertionLink,
    Stage1BeneficiaryClaimLink,
    Stage1CandidatePool,
    Stage1CandidatePoolRevision,
    Stage1CandidatePoolMembership,
)


@event.listens_for(Session, "before_flush")
def reject_stage1_mutation(
    session: Session, _flush_context: object, _instances: object
) -> None:
    """Reject ordinary ORM updates and deletes for accepted Stage 1 rows."""
    for row in session.deleted:
        if isinstance(row, STAGE1_MODELS):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be deleted."
            )
    for row in session.dirty:
        if isinstance(row, STAGE1_MODELS) and session.is_modified(
            row, include_collections=False
        ):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be updated."
            )

"""Append-only ORM models for evidence-backed industry chain maps."""

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
    text,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.database.models import Base
from industry_alpha.errors import EvidenceLedgerImmutableError


class IndustryMap(Base):
    __tablename__ = "industry_maps"
    __table_args__ = (
        UniqueConstraint("case_id", "map_key", name="uq_industry_map_case_key"),
        Index("ix_industry_map_case_key", "case_id", "map_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    case_id: Mapped[UUID] = mapped_column(
        ForeignKey("research_cases.id", ondelete="RESTRICT"), nullable=False
    )
    map_key: Mapped[str] = mapped_column(String(96), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class IndustryMapRevision(Base):
    __tablename__ = "industry_map_revisions"
    __table_args__ = (
        UniqueConstraint("map_id", "revision_no", name="uq_industry_map_revision_no"),
        CheckConstraint("revision_no > 0", name="ck_industry_map_revision_positive"),
        Index("ix_industry_map_revision", "map_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    map_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_maps.id", ondelete="RESTRICT"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    scope: Mapped[str] = mapped_column(String(4000), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_map_revisions.id", ondelete="RESTRICT")
    )


class IndustryMapNode(Base):
    __tablename__ = "industry_map_nodes"
    __table_args__ = (
        UniqueConstraint("map_id", "node_key", name="uq_industry_map_node_key"),
        Index("ix_industry_map_node", "map_id", "node_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    map_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_maps.id", ondelete="RESTRICT"), nullable=False
    )
    node_key: Mapped[str] = mapped_column(String(96), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class IndustryMapNodeRevision(Base):
    __tablename__ = "industry_map_node_revisions"
    __table_args__ = (
        UniqueConstraint("node_id", "revision_no", name="uq_industry_node_revision_no"),
        CheckConstraint("revision_no > 0", name="ck_industry_node_revision_positive"),
        CheckConstraint(
            "node_kind IN ('upstream_input','equipment','component','manufacturing',"
            "'distribution','service','customer_end_market',"
            "'regulation_infrastructure','other')",
            name="ck_industry_node_kind",
        ),
        CheckConstraint(
            "assertion_status IN ('draft','supported','disputed','rejected')",
            name="ck_industry_node_status",
        ),
        Index("ix_industry_node_revision", "node_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    node_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_map_nodes.id", ondelete="RESTRICT"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000))
    node_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    assertion_status: Mapped[str] = mapped_column(String(16), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_map_node_revisions.id", ondelete="RESTRICT")
    )


class IndustryMapRelationship(Base):
    __tablename__ = "industry_map_relationships"
    __table_args__ = (
        UniqueConstraint(
            "map_id", "relationship_key", name="uq_industry_map_relationship_key"
        ),
        CheckConstraint(
            "source_node_id <> target_node_id", name="ck_industry_relationship_distinct_nodes"
        ),
        Index("ix_industry_map_relationship", "map_id", "relationship_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    map_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_maps.id", ondelete="RESTRICT"), nullable=False
    )
    relationship_key: Mapped[str] = mapped_column(String(96), nullable=False)
    source_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_map_nodes.id", ondelete="RESTRICT"), nullable=False
    )
    target_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_map_nodes.id", ondelete="RESTRICT"), nullable=False
    )
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class IndustryMapRelationshipRevision(Base):
    __tablename__ = "industry_map_relationship_revisions"
    __table_args__ = (
        UniqueConstraint(
            "relationship_id", "revision_no", name="uq_industry_relationship_revision_no"
        ),
        CheckConstraint(
            "revision_no > 0", name="ck_industry_relationship_revision_positive"
        ),
        CheckConstraint(
            "relation_kind IN ('supplies','enables','depends_on','substitutes',"
            "'competes_with','distributes_to','regulates','other')",
            name="ck_industry_relationship_kind",
        ),
        CheckConstraint(
            "assertion_status IN ('draft','supported','disputed','rejected')",
            name="ck_industry_relationship_status",
        ),
        Index("ix_industry_relationship_revision", "relationship_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    relationship_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_map_relationships.id", ondelete="RESTRICT"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    relation_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000))
    assertion_status: Mapped[str] = mapped_column(String(16), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_map_relationship_revisions.id", ondelete="RESTRICT")
    )


class IndustryMapObservation(Base):
    __tablename__ = "industry_map_observations"
    __table_args__ = (
        UniqueConstraint(
            "map_id", "observation_key", name="uq_industry_map_observation_key"
        ),
        CheckConstraint(
            "observation_kind IN ('driver','bottleneck','value_pool_shift')",
            name="ck_industry_observation_kind",
        ),
        Index("ix_industry_map_observation", "map_id", "observation_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    map_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_maps.id", ondelete="RESTRICT"), nullable=False
    )
    observation_key: Mapped[str] = mapped_column(String(96), nullable=False)
    observation_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class IndustryMapObservationRevision(Base):
    __tablename__ = "industry_map_observation_revisions"
    __table_args__ = (
        UniqueConstraint(
            "observation_id", "revision_no", name="uq_industry_observation_revision_no"
        ),
        CheckConstraint(
            "revision_no > 0", name="ck_industry_observation_revision_positive"
        ),
        CheckConstraint(
            "assertion_status IN ('draft','supported','disputed','rejected')",
            name="ck_industry_observation_status",
        ),
        Index("ix_industry_observation_revision", "observation_id", "revision_no"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    observation_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_map_observations.id", ondelete="RESTRICT"), nullable=False
    )
    revision_no: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000))
    assertion_status: Mapped[str] = mapped_column(String(16), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_map_observation_revisions.id", ondelete="RESTRICT")
    )


class IndustryMapAssertionClaimLink(Base):
    __tablename__ = "industry_map_assertion_claim_links"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN node_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN relationship_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN observation_revision_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_industry_assertion_link_one_target",
        ),
        Index(
            "uq_industry_node_claim_link",
            "node_revision_id",
            "claim_revision_id",
            unique=True,
            postgresql_where=text("node_revision_id IS NOT NULL"),
            sqlite_where=text("node_revision_id IS NOT NULL"),
        ),
        Index(
            "uq_industry_relationship_claim_link",
            "relationship_revision_id",
            "claim_revision_id",
            unique=True,
            postgresql_where=text("relationship_revision_id IS NOT NULL"),
            sqlite_where=text("relationship_revision_id IS NOT NULL"),
        ),
        Index(
            "uq_industry_observation_claim_link",
            "observation_revision_id",
            "claim_revision_id",
            unique=True,
            postgresql_where=text("observation_revision_id IS NOT NULL"),
            sqlite_where=text("observation_revision_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    node_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_map_node_revisions.id", ondelete="RESTRICT")
    )
    relationship_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_map_relationship_revisions.id", ondelete="RESTRICT")
    )
    observation_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_map_observation_revisions.id", ondelete="RESTRICT")
    )
    claim_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("claim_revisions.id", ondelete="RESTRICT"), nullable=False
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class IndustryMapRevisionMembership(Base):
    __tablename__ = "industry_map_revision_memberships"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN node_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN relationship_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN observation_revision_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_industry_membership_one_target",
        ),
        Index(
            "uq_industry_map_node_membership",
            "map_revision_id",
            "node_revision_id",
            unique=True,
            postgresql_where=text("node_revision_id IS NOT NULL"),
            sqlite_where=text("node_revision_id IS NOT NULL"),
        ),
        Index(
            "uq_industry_map_relationship_membership",
            "map_revision_id",
            "relationship_revision_id",
            unique=True,
            postgresql_where=text("relationship_revision_id IS NOT NULL"),
            sqlite_where=text("relationship_revision_id IS NOT NULL"),
        ),
        Index(
            "uq_industry_map_observation_membership",
            "map_revision_id",
            "observation_revision_id",
            unique=True,
            postgresql_where=text("observation_revision_id IS NOT NULL"),
            sqlite_where=text("observation_revision_id IS NOT NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    map_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_map_revisions.id", ondelete="RESTRICT"), nullable=False
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


CHAIN_MAP_MODELS = (
    IndustryMap,
    IndustryMapRevision,
    IndustryMapNode,
    IndustryMapNodeRevision,
    IndustryMapRelationship,
    IndustryMapRelationshipRevision,
    IndustryMapObservation,
    IndustryMapObservationRevision,
    IndustryMapAssertionClaimLink,
    IndustryMapRevisionMembership,
)


@event.listens_for(Session, "before_flush")
def reject_chain_map_mutation(
    session: Session, _flush_context: object, _instances: object
) -> None:
    """Reject ordinary ORM updates and deletes for accepted map history."""
    for row in session.deleted:
        if isinstance(row, CHAIN_MAP_MODELS):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be deleted."
            )
    for row in session.dirty:
        if isinstance(row, CHAIN_MAP_MODELS) and session.is_modified(
            row, include_collections=False
        ):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be updated."
            )

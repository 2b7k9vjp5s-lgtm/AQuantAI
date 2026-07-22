"""Offline Industry Thesis Orchestration v1 persistence models."""

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
    Text,
    UniqueConstraint,
    Uuid,
    event,
    inspect,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from backend.database.models import Base, IDENTITY_TYPE
from industry_alpha.errors import EvidenceLedgerImmutableError


DRIVER_TYPES = (
    "demand_expansion",
    "supply_contraction_or_pricing",
    "policy_or_institutional_change",
    "technology_substitution",
    "event_shock",
    "mixed",
    "other",
    "unknown",
)
ANALYSIS_HORIZONS = ("near_term", "medium_term", "long_term", "custom", "unknown")
COVERAGE_STATES = ("reviewed_local_scope", "partial_local_coverage", "coverage_unknown")
SESSION_STATES = ("active", "completed", "abandoned", "retired")
WORKFLOW_STATES = (
    "draft",
    "candidate_build_ready",
    "awaiting_review",
    "reviewed_plan_ready",
    "accepted_outputs_linked",
    "superseded",
    "abandoned",
)
CANDIDATE_SOURCE_KINDS = (
    "accepted_local_mapping",
    "existing_industry_map_revision",
    "user_seed",
    "ai_draft",
)
IDENTITY_STATES = (
    "exact_accepted_identity",
    "candidate_identity_only",
    "ambiguous_identity",
    "unresolved_identity",
    "rejected_identity",
)
REVIEW_STATES = (
    "proposed",
    "selected_for_acceptance",
    "rejected_by_user",
    "unresolved",
    "superseded",
)
PROPOSED_EXPOSURE_TYPES = ("direct", "conditional", "indirect", "conceptual", "unknown")
PROPOSAL_CONFIDENCE_STATES = ("high", "medium", "low", "unknown")


def _sql_values(values: tuple[str, ...]) -> str:
    return ",".join(f"'{item}'" for item in values)


class IndustryThesisSessionIdentity(Base):
    __tablename__ = "industry_thesis_session_identities"
    __table_args__ = (
        CheckConstraint(
            f"state IN ({_sql_values(SESSION_STATES)})",
            name="ck_industry_thesis_session_state",
        ),
        CheckConstraint(
            "created_by_kind = 'local_user'",
            name="ck_industry_thesis_session_creator",
        ),
        CheckConstraint(
            "latest_revision_number >= 0",
            name="ck_industry_thesis_session_latest_nonnegative",
        ),
        Index("ix_industry_thesis_session_state", "state", "created_recorded_utc"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    created_recorded_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    latest_revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class IndustryThesisSessionRevision(Base):
    __tablename__ = "industry_thesis_session_revisions"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "revision_number",
            name="uq_industry_thesis_session_revision_number",
        ),
        CheckConstraint(
            "revision_number > 0",
            name="ck_industry_thesis_session_revision_positive",
        ),
        CheckConstraint(
            f"driver_type IN ({_sql_values(DRIVER_TYPES)})",
            name="ck_industry_thesis_driver_type",
        ),
        CheckConstraint(
            f"analysis_horizon_kind IN ({_sql_values(ANALYSIS_HORIZONS)})",
            name="ck_industry_thesis_horizon",
        ),
        CheckConstraint(
            f"coverage_state IN ({_sql_values(COVERAGE_STATES)})",
            name="ck_industry_thesis_coverage",
        ),
        CheckConstraint(
            f"workflow_state IN ({_sql_values(WORKFLOW_STATES)})",
            name="ck_industry_thesis_workflow_state",
        ),
        CheckConstraint(
            "(analysis_horizon_kind = 'custom' "
            "AND analysis_start_date IS NOT NULL "
            "AND analysis_end_date IS NOT NULL "
            "AND analysis_end_date >= analysis_start_date) OR "
            "(analysis_horizon_kind <> 'custom' "
            "AND ((analysis_start_date IS NULL AND analysis_end_date IS NULL) "
            "OR (analysis_start_date IS NOT NULL AND analysis_end_date IS NOT NULL "
            "AND analysis_end_date >= analysis_start_date)))",
            name="ck_industry_thesis_horizon_dates",
        ),
        CheckConstraint(
            "length(input_fingerprint_sha256) = 64",
            name="ck_industry_thesis_input_fingerprint",
        ),
        CheckConstraint(
            "length(trim(thesis_text_original)) > 0",
            name="ck_industry_thesis_text_nonempty",
        ),
        CheckConstraint(
            "length(market_scope_json) > 2",
            name="ck_industry_thesis_market_scope_nonempty",
        ),
        Index(
            "ix_industry_thesis_session_revision",
            "session_id",
            "revision_number",
        ),
        Index(
            "ix_industry_thesis_session_visibility",
            "information_cutoff_date",
            "recorded_at_utc",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_thesis_session_identities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    thesis_text_original: Mapped[str] = mapped_column(String(4000), nullable=False)
    thesis_title_reviewed: Mapped[str | None] = mapped_column(String(300))
    driver_type: Mapped[str] = mapped_column(String(48), nullable=False)
    analysis_horizon_kind: Mapped[str] = mapped_column(String(24), nullable=False)
    analysis_start_date: Mapped[date | None] = mapped_column(Date)
    analysis_end_date: Mapped[date | None] = mapped_column(Date)
    market_scope_json: Mapped[str] = mapped_column(Text, nullable=False)
    chain_boundary_json: Mapped[str] = mapped_column(Text, nullable=False)
    exclusions_json: Mapped[str] = mapped_column(Text, nullable=False)
    seed_companies_json: Mapped[str] = mapped_column(Text, nullable=False)
    seed_products_json: Mapped[str] = mapped_column(Text, nullable=False)
    seed_technologies_json: Mapped[str] = mapped_column(Text, nullable=False)
    seed_bottlenecks_json: Mapped[str] = mapped_column(Text, nullable=False)
    draft_graph_json: Mapped[str] = mapped_column(Text, nullable=False)
    coverage_state: Mapped[str] = mapped_column(String(32), nullable=False)
    workflow_state: Mapped[str] = mapped_column(String(32), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    input_fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_thesis_session_revisions.id", ondelete="RESTRICT")
    )
    revision_note: Mapped[str] = mapped_column(String(1000), nullable=False)


class IndustryThesisCandidateIdentity(Base):
    __tablename__ = "industry_thesis_candidate_identities"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "candidate_key",
            name="uq_industry_thesis_candidate_key",
        ),
        CheckConstraint(
            "length(candidate_key) = 64",
            name="ck_industry_thesis_candidate_key_length",
        ),
        CheckConstraint(
            "latest_revision_number >= 0",
            name="ck_industry_thesis_candidate_latest_nonnegative",
        ),
        Index("ix_industry_thesis_candidate_session", "session_id", "candidate_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_thesis_session_identities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    candidate_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_recorded_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latest_revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class IndustryThesisCandidateRevision(Base):
    __tablename__ = "industry_thesis_candidate_revisions"
    __table_args__ = (
        UniqueConstraint(
            "candidate_id",
            "revision_number",
            name="uq_industry_thesis_candidate_revision_number",
        ),
        CheckConstraint(
            "revision_number > 0",
            name="ck_industry_thesis_candidate_revision_positive",
        ),
        CheckConstraint(
            f"source_kind IN ({_sql_values(CANDIDATE_SOURCE_KINDS)})",
            name="ck_industry_thesis_candidate_source_kind",
        ),
        CheckConstraint(
            f"identity_state IN ({_sql_values(IDENTITY_STATES)})",
            name="ck_industry_thesis_candidate_identity_state",
        ),
        CheckConstraint(
            f"review_state IN ({_sql_values(REVIEW_STATES)})",
            name="ck_industry_thesis_candidate_review_state",
        ),
        CheckConstraint(
            f"proposed_exposure_type IN ({_sql_values(PROPOSED_EXPOSURE_TYPES)})",
            name="ck_industry_thesis_candidate_exposure",
        ),
        CheckConstraint(
            f"proposal_confidence IN ({_sql_values(PROPOSAL_CONFIDENCE_STATES)})",
            name="ck_industry_thesis_candidate_confidence",
        ),
        CheckConstraint(
            "identity_state <> 'exact_accepted_identity' "
            "OR proposed_stock_basic_record_id IS NOT NULL "
            "OR proposed_listed_instrument_id IS NOT NULL",
            name="ck_industry_thesis_candidate_exact_identity",
        ),
        CheckConstraint(
            "manifest_fingerprint_sha256 IS NULL "
            "OR length(manifest_fingerprint_sha256) = 64",
            name="ck_industry_thesis_candidate_manifest_fingerprint",
        ),
        CheckConstraint(
            "source_kind <> 'ai_draft' OR manifest_fingerprint_sha256 IS NOT NULL",
            name="ck_industry_thesis_candidate_ai_manifest",
        ),
        CheckConstraint(
            "length(trim(company_label_original)) > 0",
            name="ck_industry_thesis_candidate_label_nonempty",
        ),
        Index(
            "ix_industry_thesis_candidate_revision",
            "candidate_id",
            "revision_number",
        ),
        Index(
            "ix_industry_thesis_candidate_session_revision",
            "session_revision_id",
            "source_kind",
            "identity_state",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_thesis_candidate_identities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    session_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_thesis_session_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    source_reference_json: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_stock_basic_record_id: Mapped[int | None] = mapped_column(
        IDENTITY_TYPE,
        ForeignKey("stock_basic.id", ondelete="RESTRICT"),
    )
    proposed_listed_instrument_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("listed_instruments.id", ondelete="RESTRICT")
    )
    company_label_original: Mapped[str] = mapped_column(String(300), nullable=False)
    product_or_service_fit: Mapped[str | None] = mapped_column(String(2000))
    industry_position: Mapped[str | None] = mapped_column(String(1000))
    benefit_path_text: Mapped[str] = mapped_column(String(4000), nullable=False)
    proposed_exposure_type: Mapped[str] = mapped_column(String(24), nullable=False)
    proposal_confidence: Mapped[str] = mapped_column(String(16), nullable=False)
    identity_state: Mapped[str] = mapped_column(String(32), nullable=False)
    review_state: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale_json: Mapped[str] = mapped_column(Text, nullable=False)
    uncertainty_json: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_fingerprint_sha256: Mapped[str | None] = mapped_column(String(64))
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_thesis_candidate_revisions.id", ondelete="RESTRICT")
    )


class IndustryThesisOutputLinkIdentity(Base):
    __tablename__ = "industry_thesis_output_link_identities"
    __table_args__ = (
        UniqueConstraint(
            "session_id",
            "output_key",
            name="uq_industry_thesis_output_link_key",
        ),
        CheckConstraint(
            "length(output_key) = 64",
            name="ck_industry_thesis_output_key_length",
        ),
        CheckConstraint(
            "latest_revision_number >= 0",
            name="ck_industry_thesis_output_latest_nonnegative",
        ),
        Index("ix_industry_thesis_output_session", "session_id", "output_key"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_thesis_session_identities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    output_key: Mapped[str] = mapped_column(String(64), nullable=False)
    created_recorded_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latest_revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class IndustryThesisOutputLinkRevision(Base):
    __tablename__ = "industry_thesis_output_link_revisions"
    __table_args__ = (
        UniqueConstraint(
            "output_link_id",
            "revision_number",
            name="uq_industry_thesis_output_link_revision_number",
        ),
        CheckConstraint(
            "revision_number > 0",
            name="ck_industry_thesis_output_revision_positive",
        ),
        CheckConstraint(
            f"coverage_state IN ({_sql_values(COVERAGE_STATES)})",
            name="ck_industry_thesis_output_coverage",
        ),
        CheckConstraint(
            "length(acceptance_plan_fingerprint_sha256) = 64",
            name="ck_industry_thesis_output_plan_fingerprint",
        ),
        Index(
            "ix_industry_thesis_output_revision",
            "output_link_id",
            "revision_number",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    output_link_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_thesis_output_link_identities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    session_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_thesis_session_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    accepted_industry_map_identity_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_maps.id", ondelete="RESTRICT"),
        nullable=False,
    )
    accepted_industry_map_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("industry_map_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    accepted_candidate_pool_revision_id: Mapped[UUID] = mapped_column(
        ForeignKey("stage1_candidate_pool_revisions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    ordered_beneficiary_revision_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    coverage_state: Mapped[str] = mapped_column(String(32), nullable=False)
    acceptance_plan_fingerprint_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_transaction_id: Mapped[str] = mapped_column(String(128), nullable=False)
    information_cutoff_date: Mapped[date] = mapped_column(Date, nullable=False)
    recorded_at_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    supersedes_output_link_revision_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("industry_thesis_output_link_revisions.id", ondelete="RESTRICT")
    )


INDUSTRY_THESIS_MODELS = (
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
    IndustryThesisCandidateIdentity,
    IndustryThesisCandidateRevision,
    IndustryThesisOutputLinkIdentity,
    IndustryThesisOutputLinkRevision,
)

_STRICT_APPEND_ONLY_MODELS = (
    IndustryThesisSessionRevision,
    IndustryThesisCandidateRevision,
    IndustryThesisOutputLinkRevision,
)
_IDENTITY_MODELS = (
    IndustryThesisSessionIdentity,
    IndustryThesisCandidateIdentity,
    IndustryThesisOutputLinkIdentity,
)


@event.listens_for(Session, "before_flush")
def reject_industry_thesis_mutation(
    session: Session,
    _flush_context: object,
    _instances: object,
) -> None:
    """Preserve append-only history and immutable identity fields."""

    for row in session.deleted:
        if isinstance(row, INDUSTRY_THESIS_MODELS):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows cannot be deleted."
            )
    for row in session.dirty:
        if isinstance(row, _STRICT_APPEND_ONLY_MODELS) and session.is_modified(
            row, include_collections=False
        ):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be updated."
            )
        if not isinstance(row, _IDENTITY_MODELS):
            continue
        changed = {
            attribute.key
            for attribute in inspect(row).attrs
            if attribute.history.has_changes()
        }
        if changed - {"latest_revision_number"}:
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} identity fields are immutable."
            )

"""Add append-only Stage 2 expectations and valuation snapshots.

Revision ID: 20260719_0009
Revises: 20260719_0008
Create Date: 2026-07-19
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260719_0009"
down_revision: str | None = "20260719_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid = sa.Uuid()
    identity = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "stage2_market_expectations",
        sa.Column("id", uuid, nullable=False),
        sa.Column("company_research_id", uuid, nullable=False),
        sa.Column("expectation_key", sa.String(96), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_research_id"], ["stage2_company_research.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_research_id", "expectation_key", name="uq_stage2_expectation_key"),
    )
    op.create_index("ix_stage2_expectation_research", "stage2_market_expectations", ["company_research_id", "expectation_key"])
    op.create_table(
        "stage2_market_expectation_revisions",
        sa.Column("id", uuid, nullable=False),
        sa.Column("expectation_id", uuid, nullable=False),
        sa.Column("company_research_revision_id", uuid, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
        sa.Column("period_horizon", sa.String(300), nullable=False),
        sa.Column("expectation_kind", sa.String(32), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("basis", sa.String(4000), nullable=False),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid, nullable=True),
        sa.CheckConstraint("revision_no > 0", name="ck_stage2_expectation_revision_positive"),
        sa.CheckConstraint("expectation_kind IN ('consensus','guidance','market_implied','research_assumption','unknown')", name="ck_stage2_expectation_kind"),
        sa.CheckConstraint("direction IN ('positive','negative','mixed','uncertain')", name="ck_stage2_expectation_direction"),
        sa.CheckConstraint("status IN ('draft','supported','disputed','rejected')", name="ck_stage2_expectation_status"),
        sa.CheckConstraint("confidence IN ('low','medium','high')", name="ck_stage2_expectation_confidence"),
        sa.ForeignKeyConstraint(["expectation_id"], ["stage2_market_expectations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["company_research_revision_id"], ["stage2_company_research_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], ["stage2_market_expectation_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("expectation_id", "revision_no", name="uq_stage2_expectation_revision_no"),
    )
    op.create_index("ix_stage2_expectation_revision", "stage2_market_expectation_revisions", ["expectation_id", "revision_no"])
    op.create_table(
        "stage2_expectation_hypothesis_links",
        sa.Column("id", uuid, nullable=False),
        sa.Column("expectation_revision_id", uuid, nullable=False),
        sa.Column("hypothesis_revision_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["expectation_revision_id"], ["stage2_market_expectation_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["hypothesis_revision_id"], ["stage2_financial_hypothesis_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("expectation_revision_id", "hypothesis_revision_id", name="uq_stage2_expectation_hypothesis_link"),
    )
    op.create_index("ix_stage2_expectation_hypothesis", "stage2_expectation_hypothesis_links", ["expectation_revision_id", "hypothesis_revision_id"])
    op.create_table(
        "stage2_expectation_claim_links",
        sa.Column("id", uuid, nullable=False),
        sa.Column("expectation_revision_id", uuid, nullable=False),
        sa.Column("claim_revision_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["expectation_revision_id"], ["stage2_market_expectation_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("expectation_revision_id", "claim_revision_id", name="uq_stage2_expectation_claim_link"),
    )
    op.create_index("ix_stage2_expectation_claim", "stage2_expectation_claim_links", ["expectation_revision_id", "claim_revision_id"])
    op.create_table(
        "stage2_expectation_evidence_links",
        sa.Column("id", uuid, nullable=False),
        sa.Column("expectation_revision_id", uuid, nullable=False),
        sa.Column("claim_revision_id", uuid, nullable=False),
        sa.Column("claim_evidence_link_id", uuid, nullable=False),
        sa.Column("evidence_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["expectation_revision_id"], ["stage2_market_expectation_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_evidence_link_id"], ["claim_evidence_links.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("expectation_revision_id", "claim_evidence_link_id", name="uq_stage2_expectation_evidence_link"),
    )
    op.create_index("ix_stage2_expectation_evidence", "stage2_expectation_evidence_links", ["expectation_revision_id", "claim_revision_id"])

    op.create_table(
        "stage2_valuation_snapshots",
        sa.Column("id", uuid, nullable=False),
        sa.Column("company_research_id", uuid, nullable=False),
        sa.Column("valuation_key", sa.String(96), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_research_id"], ["stage2_company_research.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_research_id", "valuation_key", name="uq_stage2_valuation_key"),
    )
    op.create_index("ix_stage2_valuation_research", "stage2_valuation_snapshots", ["company_research_id", "valuation_key"])
    op.create_table(
        "stage2_valuation_snapshot_revisions",
        sa.Column("id", uuid, nullable=False),
        sa.Column("valuation_id", uuid, nullable=False),
        sa.Column("company_research_revision_id", uuid, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("valuation_method", sa.String(32), nullable=False),
        sa.Column("metric_context", sa.String(1000), nullable=False),
        sa.Column("observed_value", sa.String(64), nullable=True),
        sa.Column("missing_data_reason", sa.String(500), nullable=True),
        sa.Column("unit", sa.String(64), nullable=True),
        sa.Column("currency", sa.String(16), nullable=True),
        sa.Column("comparison_basis", sa.String(1000), nullable=False),
        sa.Column("assumptions", sa.String(4000), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("daily_price_id", identity, nullable=True),
        sa.Column("supersedes_revision_id", uuid, nullable=True),
        sa.CheckConstraint("revision_no > 0", name="ck_stage2_valuation_revision_positive"),
        sa.CheckConstraint("valuation_method IN ('multiple_observation','asset_reference','historical_range','market_price_context','missing_data')", name="ck_stage2_valuation_method"),
        sa.CheckConstraint("status IN ('draft','supported','disputed','rejected')", name="ck_stage2_valuation_status"),
        sa.CheckConstraint("confidence IN ('low','medium','high')", name="ck_stage2_valuation_confidence"),
        sa.ForeignKeyConstraint(["valuation_id"], ["stage2_valuation_snapshots.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["company_research_revision_id"], ["stage2_company_research_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["daily_price_id"], ["daily_price.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], ["stage2_valuation_snapshot_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("valuation_id", "revision_no", name="uq_stage2_valuation_revision_no"),
    )
    op.create_index("ix_stage2_valuation_revision", "stage2_valuation_snapshot_revisions", ["valuation_id", "revision_no"])
    op.create_table(
        "stage2_valuation_hypothesis_links",
        sa.Column("id", uuid, nullable=False),
        sa.Column("valuation_revision_id", uuid, nullable=False),
        sa.Column("hypothesis_revision_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["valuation_revision_id"], ["stage2_valuation_snapshot_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["hypothesis_revision_id"], ["stage2_financial_hypothesis_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("valuation_revision_id", "hypothesis_revision_id", name="uq_stage2_valuation_hypothesis_link"),
    )
    op.create_index("ix_stage2_valuation_hypothesis", "stage2_valuation_hypothesis_links", ["valuation_revision_id", "hypothesis_revision_id"])
    op.create_table(
        "stage2_valuation_claim_links",
        sa.Column("id", uuid, nullable=False),
        sa.Column("valuation_revision_id", uuid, nullable=False),
        sa.Column("claim_revision_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["valuation_revision_id"], ["stage2_valuation_snapshot_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("valuation_revision_id", "claim_revision_id", name="uq_stage2_valuation_claim_link"),
    )
    op.create_index("ix_stage2_valuation_claim", "stage2_valuation_claim_links", ["valuation_revision_id", "claim_revision_id"])
    op.create_table(
        "stage2_valuation_evidence_links",
        sa.Column("id", uuid, nullable=False),
        sa.Column("valuation_revision_id", uuid, nullable=False),
        sa.Column("claim_revision_id", uuid, nullable=False),
        sa.Column("claim_evidence_link_id", uuid, nullable=False),
        sa.Column("evidence_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["valuation_revision_id"], ["stage2_valuation_snapshot_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_evidence_link_id"], ["claim_evidence_links.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("valuation_revision_id", "claim_evidence_link_id", name="uq_stage2_valuation_evidence_link"),
    )
    op.create_index("ix_stage2_valuation_evidence", "stage2_valuation_evidence_links", ["valuation_revision_id", "claim_revision_id"])


def downgrade() -> None:
    for table, index in (
        ("stage2_valuation_evidence_links", "ix_stage2_valuation_evidence"),
        ("stage2_valuation_claim_links", "ix_stage2_valuation_claim"),
        ("stage2_valuation_hypothesis_links", "ix_stage2_valuation_hypothesis"),
        ("stage2_valuation_snapshot_revisions", "ix_stage2_valuation_revision"),
        ("stage2_valuation_snapshots", "ix_stage2_valuation_research"),
        ("stage2_expectation_evidence_links", "ix_stage2_expectation_evidence"),
        ("stage2_expectation_claim_links", "ix_stage2_expectation_claim"),
        ("stage2_expectation_hypothesis_links", "ix_stage2_expectation_hypothesis"),
        ("stage2_market_expectation_revisions", "ix_stage2_expectation_revision"),
        ("stage2_market_expectations", "ix_stage2_expectation_research"),
    ):
        op.drop_index(index, table_name=table)
        op.drop_table(table)

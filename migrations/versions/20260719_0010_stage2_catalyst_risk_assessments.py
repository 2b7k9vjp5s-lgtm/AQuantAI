"""Add append-only Stage 2 catalyst and risk assessments.

Revision ID: 20260719_0010
Revises: 20260719_0009
Create Date: 2026-07-19
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260719_0010"
down_revision: str | None = "20260719_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_identity(kind: str, key: str) -> None:
    uuid = sa.Uuid()
    table = f"stage2_{kind}_assessments"
    op.create_table(
        table,
        sa.Column("id", uuid, nullable=False),
        sa.Column("company_research_id", uuid, nullable=False),
        sa.Column(key, sa.String(96), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_research_id"], ["stage2_company_research.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_research_id", key, name=f"uq_stage2_{kind}_key"),
    )
    op.create_index(f"ix_stage2_{kind}_research", table, ["company_research_id", key])


def _create_revision(kind: str) -> None:
    uuid = sa.Uuid()
    identity = f"stage2_{kind}_assessments"
    table = f"stage2_{kind}_assessment_revisions"
    columns = [
        sa.Column("id", uuid, nullable=False),
        sa.Column(f"{kind}_id", uuid, nullable=False),
        sa.Column("company_research_revision_id", uuid, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column(f"{kind}_category", sa.String(32), nullable=False),
        sa.Column("subject", sa.String(500), nullable=False),
    ]
    if kind == "catalyst":
        columns.extend((
            sa.Column("expected_observation_window", sa.String(300), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("confidence", sa.String(16), nullable=False),
            sa.Column("trigger_observation_criteria", sa.String(2000), nullable=False),
            sa.Column("basis", sa.String(4000), nullable=False),
            sa.Column("uncertainty", sa.String(2000), nullable=False),
        ))
        categories = "'demand','supply','product','customer','certification','capacity','policy','financial','operational','other'"
    else:
        columns.extend((
            sa.Column("downside_path", sa.String(2000), nullable=False),
            sa.Column("thesis_invalidation_condition", sa.String(2000), nullable=False),
            sa.Column("mitigants", sa.String(2000), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("confidence", sa.String(16), nullable=False),
            sa.Column("basis", sa.String(4000), nullable=False),
            sa.Column("uncertainty", sa.String(2000), nullable=False),
        ))
        categories = "'demand','supply','execution','competition','customer','policy','financial','governance','operational','other'"
    columns.extend((
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid, nullable=True),
        sa.CheckConstraint("revision_no > 0", name=f"ck_stage2_{kind}_revision_positive"),
        sa.CheckConstraint(f"{kind}_category IN ({categories})", name=f"ck_stage2_{kind}_category"),
        sa.CheckConstraint("status IN ('draft','supported','disputed','rejected')", name=f"ck_stage2_{kind}_status"),
        sa.CheckConstraint("confidence IN ('low','medium','high')", name=f"ck_stage2_{kind}_confidence"),
        sa.ForeignKeyConstraint([f"{kind}_id"], [f"{identity}.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["company_research_revision_id"], ["stage2_company_research_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], [f"{table}.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(f"{kind}_id", "revision_no", name=f"uq_stage2_{kind}_revision_no"),
    ))
    op.create_table(table, *columns)
    op.create_index(f"ix_stage2_{kind}_revision", table, [f"{kind}_id", "revision_no"])


def _create_simple_link(kind: str, upstream: str, upstream_table: str) -> None:
    uuid = sa.Uuid()
    table = f"stage2_{kind}_{upstream}_links"
    revision_field = f"{kind}_revision_id"
    upstream_field = f"{upstream}_revision_id"
    op.create_table(
        table,
        sa.Column("id", uuid, nullable=False),
        sa.Column(revision_field, uuid, nullable=False),
        sa.Column(upstream_field, uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint([revision_field], [f"stage2_{kind}_assessment_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint([upstream_field], [f"{upstream_table}.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(revision_field, upstream_field, name=f"uq_{table}"),
    )
    op.create_index(f"ix_stage2_{kind}_{upstream}", table, [revision_field, upstream_field])


def _create_evidence_link(kind: str) -> None:
    uuid = sa.Uuid()
    table = f"stage2_{kind}_evidence_links"
    revision_field = f"{kind}_revision_id"
    op.create_table(
        table,
        sa.Column("id", uuid, nullable=False),
        sa.Column(revision_field, uuid, nullable=False),
        sa.Column("claim_revision_id", uuid, nullable=False),
        sa.Column("claim_evidence_link_id", uuid, nullable=False),
        sa.Column("evidence_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint([revision_field], [f"stage2_{kind}_assessment_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_evidence_link_id"], ["claim_evidence_links.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(revision_field, "claim_evidence_link_id", name=f"uq_stage2_{kind}_evidence_link"),
    )
    op.create_index(f"ix_stage2_{kind}_evidence", table, [revision_field, "claim_revision_id"])


def upgrade() -> None:
    for kind, key in (("catalyst", "catalyst_key"), ("risk", "risk_key")):
        _create_identity(kind, key)
        _create_revision(kind)
        _create_simple_link(kind, "hypothesis", "stage2_financial_hypothesis_revisions")
        _create_simple_link(kind, "expectation", "stage2_market_expectation_revisions")
        _create_simple_link(kind, "valuation", "stage2_valuation_snapshot_revisions")
        _create_simple_link(kind, "claim", "claim_revisions")
        _create_evidence_link(kind)


def downgrade() -> None:
    for kind in ("risk", "catalyst"):
        for upstream in ("evidence", "claim", "valuation", "expectation", "hypothesis"):
            table = f"stage2_{kind}_{upstream}_links"
            op.drop_index(f"ix_stage2_{kind}_{upstream}", table_name=table)
            op.drop_table(table)
        revision_table = f"stage2_{kind}_assessment_revisions"
        op.drop_index(f"ix_stage2_{kind}_revision", table_name=revision_table)
        op.drop_table(revision_table)
        identity_table = f"stage2_{kind}_assessments"
        op.drop_index(f"ix_stage2_{kind}_research", table_name=identity_table)
        op.drop_table(identity_table)

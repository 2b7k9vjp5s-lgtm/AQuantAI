"""Add append-only Stage 2 industry and company judgments.

Revision ID: 20260719_0011
Revises: 20260719_0010
Create Date: 2026-07-19
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260719_0011"
down_revision: str | None = "20260719_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _create_kind(kind: str) -> None:
    uuid = sa.Uuid()
    identity = f"stage2_{kind}_judgments"
    revisions = f"stage2_{kind}_judgment_revisions"
    op.create_table(
        identity,
        sa.Column("id", uuid, nullable=False),
        sa.Column("company_research_id", uuid, nullable=False),
        sa.Column("judgment_key", sa.String(96), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_research_id"], ["stage2_company_research.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_research_id", "judgment_key", name=f"uq_stage2_{kind}_judgment_key"),
    )
    op.create_index(f"ix_stage2_{kind}_judgment_research", identity, ["company_research_id", "judgment_key"])
    columns = [
        sa.Column("id", uuid, nullable=False),
        sa.Column("judgment_id", uuid, nullable=False),
        sa.Column("company_research_revision_id", uuid, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("outcome", sa.String(24), nullable=False),
        sa.Column("evidence_state", sa.String(32), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("decision_criteria", sa.String(2000), nullable=False),
        sa.Column("rationale", sa.String(4000), nullable=False),
        sa.Column("uncertainty", sa.String(2000), nullable=False),
        sa.Column("follow_up_verification", sa.String(3000), nullable=False),
    ]
    if kind == "industry":
        columns.extend((
            sa.Column("driver_durability", sa.String(2000), nullable=False),
            sa.Column("value_pool_direction", sa.String(2000), nullable=False),
            sa.Column("chain_bottleneck_support", sa.String(2000), nullable=False),
        ))
    else:
        columns.extend((
            sa.Column("beneficiary_credibility", sa.String(2000), nullable=False),
            sa.Column("financial_transmission_credibility", sa.String(2000), nullable=False),
            sa.Column("execution_risks", sa.String(2000), nullable=False),
        ))
    columns.extend((
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid, nullable=True),
        sa.CheckConstraint("revision_no > 0", name=f"ck_stage2_{kind}_judgment_revision_positive"),
        sa.CheckConstraint("outcome IN ('affirmed','not_affirmed','uncertain','not_assessed')", name=f"ck_stage2_{kind}_judgment_outcome"),
        sa.CheckConstraint("evidence_state IN ('supported','disputed','insufficient_evidence')", name=f"ck_stage2_{kind}_judgment_evidence_state"),
        sa.CheckConstraint("confidence IN ('low','medium','high')", name=f"ck_stage2_{kind}_judgment_confidence"),
        sa.ForeignKeyConstraint(["judgment_id"], [f"{identity}.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["company_research_revision_id"], ["stage2_company_research_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], [f"{revisions}.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("judgment_id", "revision_no", name=f"uq_stage2_{kind}_judgment_revision_no"),
    ))
    op.create_table(revisions, *columns)
    op.create_index(f"ix_stage2_{kind}_judgment_revision", revisions, ["judgment_id", "revision_no"])

    upstream = {
        "hypothesis": "stage2_financial_hypothesis_revisions",
        "expectation": "stage2_market_expectation_revisions",
        "valuation": "stage2_valuation_snapshot_revisions",
        "catalyst": "stage2_catalyst_assessment_revisions",
        "risk": "stage2_risk_assessment_revisions",
        "claim": "claim_revisions",
    }
    for name, table in upstream.items():
        link_table = f"stage2_{kind}_judgment_{name}_links"
        field = f"{name}_revision_id"
        op.create_table(
            link_table,
            sa.Column("id", uuid, nullable=False),
            sa.Column("judgment_revision_id", uuid, nullable=False),
            sa.Column(field, uuid, nullable=False),
            sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["judgment_revision_id"], [f"{revisions}.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint([field], [f"{table}.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("judgment_revision_id", field, name=f"uq_{link_table}"),
        )
        op.create_index(f"ix_stage2_{kind}_judgment_{name}", link_table, ["judgment_revision_id", field])
    evidence_table = f"stage2_{kind}_judgment_evidence_links"
    op.create_table(
        evidence_table,
        sa.Column("id", uuid, nullable=False),
        sa.Column("judgment_revision_id", uuid, nullable=False),
        sa.Column("claim_revision_id", uuid, nullable=False),
        sa.Column("claim_evidence_link_id", uuid, nullable=False),
        sa.Column("evidence_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["judgment_revision_id"], [f"{revisions}.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_evidence_link_id"], ["claim_evidence_links.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("judgment_revision_id", "claim_evidence_link_id", name=f"uq_stage2_{kind}_judgment_evidence_link"),
    )
    op.create_index(f"ix_stage2_{kind}_judgment_evidence", evidence_table, ["judgment_revision_id", "claim_revision_id"])


def upgrade() -> None:
    _create_kind("industry")
    _create_kind("company")


def downgrade() -> None:
    for kind in ("company", "industry"):
        evidence = f"stage2_{kind}_judgment_evidence_links"
        op.drop_index(f"ix_stage2_{kind}_judgment_evidence", table_name=evidence)
        op.drop_table(evidence)
        for name in ("claim", "risk", "catalyst", "valuation", "expectation", "hypothesis"):
            table = f"stage2_{kind}_judgment_{name}_links"
            op.drop_index(f"ix_stage2_{kind}_judgment_{name}", table_name=table)
            op.drop_table(table)
        revisions = f"stage2_{kind}_judgment_revisions"
        op.drop_index(f"ix_stage2_{kind}_judgment_revision", table_name=revisions)
        op.drop_table(revisions)
        identity = f"stage2_{kind}_judgments"
        op.drop_index(f"ix_stage2_{kind}_judgment_research", table_name=identity)
        op.drop_table(identity)

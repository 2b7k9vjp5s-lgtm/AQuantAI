"""Add append-only Stage 2 company research and hypotheses.

Revision ID: 20260719_0008
Revises: 20260719_0007
Create Date: 2026-07-19
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260719_0008"
down_revision: str | None = "20260719_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid = sa.Uuid()
    identity = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "stage2_company_research",
        sa.Column("id", uuid, nullable=False),
        sa.Column("case_id", uuid, nullable=False),
        sa.Column("map_id", uuid, nullable=False),
        sa.Column("candidate_pool_id", uuid, nullable=False),
        sa.Column("candidate_pool_revision_id", uuid, nullable=False),
        sa.Column("candidate_pool_membership_id", uuid, nullable=False),
        sa.Column("beneficiary_id", uuid, nullable=False),
        sa.Column("beneficiary_revision_id", uuid, nullable=False),
        sa.Column("selected_map_revision_id", uuid, nullable=False),
        sa.Column("stock_basic_record_id", identity, nullable=False),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("stock_code", sa.String(16), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["research_cases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["map_id"], ["industry_maps.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["candidate_pool_id"], ["stage1_candidate_pools.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["candidate_pool_revision_id"], ["stage1_candidate_pool_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["candidate_pool_membership_id"], ["stage1_candidate_pool_memberships.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["beneficiary_id"], ["stage1_beneficiaries.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["beneficiary_revision_id"], ["stage1_beneficiary_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["selected_map_revision_id"], ["industry_map_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["stock_basic_record_id"], ["stock_basic.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("candidate_pool_revision_id", "candidate_pool_membership_id", name="uq_stage2_research_exact_membership"),
        sa.UniqueConstraint("case_id", "map_id", "source", "stock_code", name="uq_stage2_research_company"),
    )
    op.create_index("ix_stage2_research_pool", "stage2_company_research", ["candidate_pool_revision_id", "stock_code"])

    op.create_table(
        "stage2_handoff_assertion_links",
        sa.Column("id", uuid, nullable=False),
        sa.Column("company_research_id", uuid, nullable=False),
        sa.Column("stage1_beneficiary_assertion_link_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_research_id"], ["stage2_company_research.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["stage1_beneficiary_assertion_link_id"], ["stage1_beneficiary_assertion_links.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_research_id", "stage1_beneficiary_assertion_link_id", name="uq_stage2_handoff_assertion_link"),
    )
    op.create_index(
        "ix_stage2_handoff_assertion",
        "stage2_handoff_assertion_links",
        ["company_research_id", "stage1_beneficiary_assertion_link_id"],
    )

    op.create_table(
        "stage2_handoff_claim_links",
        sa.Column("id", uuid, nullable=False),
        sa.Column("company_research_id", uuid, nullable=False),
        sa.Column("stage1_beneficiary_claim_link_id", uuid, nullable=False),
        sa.Column("claim_revision_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_research_id"], ["stage2_company_research.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["stage1_beneficiary_claim_link_id"], ["stage1_beneficiary_claim_links.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_research_id", "stage1_beneficiary_claim_link_id", name="uq_stage2_handoff_claim_link"),
    )
    op.create_index("ix_stage2_handoff_claim", "stage2_handoff_claim_links", ["company_research_id", "claim_revision_id"])

    op.create_table(
        "stage2_handoff_evidence_links",
        sa.Column("id", uuid, nullable=False),
        sa.Column("company_research_id", uuid, nullable=False),
        sa.Column("claim_revision_id", uuid, nullable=False),
        sa.Column("claim_evidence_link_id", uuid, nullable=False),
        sa.Column("evidence_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_research_id"], ["stage2_company_research.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_evidence_link_id"], ["claim_evidence_links.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_research_id", "claim_evidence_link_id", name="uq_stage2_handoff_evidence_link"),
    )
    op.create_index("ix_stage2_handoff_evidence", "stage2_handoff_evidence_links", ["company_research_id", "claim_revision_id"])

    op.create_table(
        "stage2_company_research_revisions",
        sa.Column("id", uuid, nullable=False),
        sa.Column("company_research_id", uuid, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("workflow_state", sa.String(16), nullable=False),
        sa.Column("conclusion_status", sa.String(32), nullable=False),
        sa.Column("research_question", sa.String(2000), nullable=False),
        sa.Column("summary", sa.String(4000), nullable=True),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid, nullable=True),
        sa.CheckConstraint("revision_no > 0", name="ck_stage2_research_revision_positive"),
        sa.CheckConstraint("workflow_state IN ('open','paused','completed','archived')", name="ck_stage2_research_workflow"),
        sa.CheckConstraint("conclusion_status IN ('unassessed','insufficient_evidence','supported','disputed','rejected')", name="ck_stage2_research_conclusion"),
        sa.ForeignKeyConstraint(["company_research_id"], ["stage2_company_research.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], ["stage2_company_research_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_research_id", "revision_no", name="uq_stage2_research_revision_no"),
    )
    op.create_index("ix_stage2_research_revision", "stage2_company_research_revisions", ["company_research_id", "revision_no"])

    op.create_table(
        "stage2_financial_hypotheses",
        sa.Column("id", uuid, nullable=False),
        sa.Column("company_research_id", uuid, nullable=False),
        sa.Column("hypothesis_key", sa.String(96), nullable=False),
        sa.Column("stage1_assertion_link_id", uuid, nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_research_id"], ["stage2_company_research.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["stage1_assertion_link_id"], ["stage1_beneficiary_assertion_links.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_research_id", "hypothesis_key", name="uq_stage2_hypothesis_key"),
    )
    op.create_index("ix_stage2_hypothesis_research", "stage2_financial_hypotheses", ["company_research_id", "hypothesis_key"])

    op.create_table(
        "stage2_financial_hypothesis_revisions",
        sa.Column("id", uuid, nullable=False),
        sa.Column("hypothesis_id", uuid, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("hypothesis_status", sa.String(16), nullable=False),
        sa.Column("mechanism", sa.String(4000), nullable=False),
        sa.Column("direction", sa.String(16), nullable=False),
        sa.Column("operating_metric", sa.String(300), nullable=False),
        sa.Column("financial_statement_line", sa.String(300), nullable=False),
        sa.Column("expected_lag_horizon", sa.String(300), nullable=False),
        sa.Column("confidence", sa.String(16), nullable=False),
        sa.Column("basis", sa.String(4000), nullable=False),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid, nullable=True),
        sa.CheckConstraint("revision_no > 0", name="ck_stage2_hypothesis_revision_positive"),
        sa.CheckConstraint("hypothesis_status IN ('draft','supported','disputed','rejected')", name="ck_stage2_hypothesis_status"),
        sa.CheckConstraint("direction IN ('positive','negative','mixed','uncertain')", name="ck_stage2_hypothesis_direction"),
        sa.CheckConstraint("confidence IN ('low','medium','high')", name="ck_stage2_hypothesis_confidence"),
        sa.ForeignKeyConstraint(["hypothesis_id"], ["stage2_financial_hypotheses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], ["stage2_financial_hypothesis_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hypothesis_id", "revision_no", name="uq_stage2_hypothesis_revision_no"),
        sa.UniqueConstraint("id", "hypothesis_id", name="uq_stage2_hypothesis_revision_identity"),
    )
    op.create_index("ix_stage2_hypothesis_revision", "stage2_financial_hypothesis_revisions", ["hypothesis_id", "revision_no"])

    op.create_table(
        "stage2_hypothesis_claim_links",
        sa.Column("id", uuid, nullable=False),
        sa.Column("hypothesis_revision_id", uuid, nullable=False),
        sa.Column("claim_revision_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["hypothesis_revision_id"], ["stage2_financial_hypothesis_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hypothesis_revision_id", "claim_revision_id", name="uq_stage2_hypothesis_claim_link"),
    )
    op.create_index("ix_stage2_hypothesis_claim", "stage2_hypothesis_claim_links", ["hypothesis_revision_id", "claim_revision_id"])

    op.create_table(
        "stage2_hypothesis_evidence_links",
        sa.Column("id", uuid, nullable=False),
        sa.Column("hypothesis_revision_id", uuid, nullable=False),
        sa.Column("claim_revision_id", uuid, nullable=False),
        sa.Column("claim_evidence_link_id", uuid, nullable=False),
        sa.Column("evidence_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["hypothesis_revision_id"], ["stage2_financial_hypothesis_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_evidence_link_id"], ["claim_evidence_links.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hypothesis_revision_id", "claim_evidence_link_id", name="uq_stage2_hypothesis_evidence_link"),
    )
    op.create_index("ix_stage2_hypothesis_evidence", "stage2_hypothesis_evidence_links", ["hypothesis_revision_id", "claim_revision_id"])

    op.create_table(
        "stage2_research_hypothesis_links",
        sa.Column("id", uuid, nullable=False),
        sa.Column("company_research_revision_id", uuid, nullable=False),
        sa.Column("hypothesis_id", uuid, nullable=False),
        sa.Column("hypothesis_revision_id", uuid, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["company_research_revision_id"], ["stage2_company_research_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["hypothesis_id"], ["stage2_financial_hypotheses.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["hypothesis_revision_id", "hypothesis_id"], ["stage2_financial_hypothesis_revisions.id", "stage2_financial_hypothesis_revisions.hypothesis_id"], name="fk_stage2_research_exact_hypothesis_revision", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_research_revision_id", "hypothesis_id", name="uq_stage2_research_hypothesis_identity"),
        sa.UniqueConstraint("company_research_revision_id", "hypothesis_revision_id", name="uq_stage2_research_hypothesis_revision"),
    )
    op.create_index("ix_stage2_research_hypothesis", "stage2_research_hypothesis_links", ["company_research_revision_id", "hypothesis_id"])

    op.create_table(
        "stage2_verification_items",
        sa.Column("id", uuid, nullable=False),
        sa.Column("company_research_revision_id", uuid, nullable=False),
        sa.Column("item_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("item_no > 0", name="ck_stage2_verification_item_positive"),
        sa.CheckConstraint("status IN ('open','completed','deferred')", name="ck_stage2_verification_status"),
        sa.ForeignKeyConstraint(["company_research_revision_id"], ["stage2_company_research_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("company_research_revision_id", "item_no", name="uq_stage2_verification_item_no"),
    )
    op.create_index("ix_stage2_verification_item", "stage2_verification_items", ["company_research_revision_id", "item_no"])


def downgrade() -> None:
    for table, index in (
        ("stage2_verification_items", "ix_stage2_verification_item"),
        ("stage2_research_hypothesis_links", "ix_stage2_research_hypothesis"),
        ("stage2_hypothesis_evidence_links", "ix_stage2_hypothesis_evidence"),
        ("stage2_hypothesis_claim_links", "ix_stage2_hypothesis_claim"),
        ("stage2_financial_hypothesis_revisions", "ix_stage2_hypothesis_revision"),
        ("stage2_financial_hypotheses", "ix_stage2_hypothesis_research"),
        ("stage2_company_research_revisions", "ix_stage2_research_revision"),
        ("stage2_handoff_evidence_links", "ix_stage2_handoff_evidence"),
        ("stage2_handoff_claim_links", "ix_stage2_handoff_claim"),
        ("stage2_handoff_assertion_links", "ix_stage2_handoff_assertion"),
        ("stage2_company_research", "ix_stage2_research_pool"),
    ):
        op.drop_index(index, table_name=table)
        op.drop_table(table)

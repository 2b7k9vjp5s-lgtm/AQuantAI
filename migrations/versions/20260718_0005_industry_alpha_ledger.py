"""Add append-only Industry Alpha research evidence ledger.

Revision ID: 20260718_0005
Revises: 20260718_0004
Create Date: 2026-07-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260718_0005"
down_revision: str | None = "20260718_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = sa.Uuid()
    op.create_table(
        "research_cases",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("case_key", sa.String(length=96), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origin", sa.String(length=16), nullable=False),
        sa.CheckConstraint("origin IN ('manual', 'fixture')", name="ck_research_cases_origin"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_key"),
    )
    op.create_table(
        "research_case_revisions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("case_id", uuid_type, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("research_question", sa.String(length=2000), nullable=False),
        sa.Column("summary", sa.String(length=4000), nullable=True),
        sa.Column("workflow_state", sa.String(length=16), nullable=False),
        sa.Column("conclusion_status", sa.String(length=32), nullable=False),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid_type, nullable=True),
        sa.CheckConstraint("revision_no > 0", name="ck_case_revision_number_positive"),
        sa.CheckConstraint("workflow_state IN ('open','paused','completed','archived')", name="ck_case_revision_workflow"),
        sa.CheckConstraint("conclusion_status IN ('unassessed','insufficient_evidence','supported','disputed','rejected')", name="ck_case_revision_conclusion"),
        sa.ForeignKeyConstraint(["case_id"], ["research_cases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], ["research_case_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "revision_no", name="uq_case_revision_number"),
    )
    op.create_index("ix_case_revision_case_number", "research_case_revisions", ["case_id", "revision_no"])
    op.create_table(
        "evidence_items",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("case_id", uuid_type, nullable=False),
        sa.Column("evidence_grade", sa.String(length=1), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False),
        sa.Column("source_title", sa.String(length=500), nullable=False),
        sa.Column("publisher_or_author", sa.String(length=300), nullable=True),
        sa.Column("source_locator", sa.String(length=1500), nullable=True),
        sa.Column("information_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.String(length=4000), nullable=False),
        sa.Column("content_fingerprint", sa.String(length=128), nullable=True),
        sa.Column("supersedes_evidence_id", uuid_type, nullable=True),
        sa.CheckConstraint("evidence_grade IN ('A','B','C','D')", name="ck_evidence_grade"),
        sa.CheckConstraint("source_kind IN ('official','regulatory','filing','statistics','company','research','media','industry','community','other')", name="ck_evidence_source_kind"),
        sa.ForeignKeyConstraint(["case_id"], ["research_cases.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_evidence_id"], ["evidence_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "content_fingerprint", name="uq_evidence_case_fingerprint"),
    )
    op.create_index("ix_evidence_case_information", "evidence_items", ["case_id", "information_date", "recorded_at_utc"])
    op.create_table(
        "claims",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("case_id", uuid_type, nullable=False),
        sa.Column("claim_key", sa.String(length=96), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["research_cases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "claim_key", name="uq_claim_case_key"),
    )
    op.create_table(
        "claim_revisions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("claim_id", uuid_type, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("statement", sa.String(length=4000), nullable=False),
        sa.Column("claim_kind", sa.String(length=16), nullable=False),
        sa.Column("claim_status", sa.String(length=16), nullable=False),
        sa.Column("inference_confidence", sa.String(length=16), nullable=True),
        sa.Column("inference_basis", sa.String(length=4000), nullable=True),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid_type, nullable=True),
        sa.CheckConstraint("revision_no > 0", name="ck_claim_revision_number_positive"),
        sa.CheckConstraint("claim_kind IN ('fact','inference')", name="ck_claim_revision_kind"),
        sa.CheckConstraint("claim_status IN ('draft','supported','disputed','rejected')", name="ck_claim_revision_status"),
        sa.CheckConstraint("inference_confidence IS NULL OR inference_confidence IN ('low','medium','high')", name="ck_claim_revision_confidence"),
        sa.CheckConstraint("(claim_kind = 'fact' AND inference_confidence IS NULL AND inference_basis IS NULL) OR (claim_kind = 'inference' AND inference_confidence IS NOT NULL AND length(trim(inference_basis)) > 0)", name="ck_claim_revision_inference_fields"),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["supersedes_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_id", "revision_no", name="uq_claim_revision_number"),
    )
    op.create_index("ix_claim_revision_claim_number", "claim_revisions", ["claim_id", "revision_no"])
    op.create_table(
        "claim_evidence_links",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("claim_revision_id", uuid_type, nullable=False),
        sa.Column("evidence_id", uuid_type, nullable=False),
        sa.Column("relation", sa.String(length=16), nullable=False),
        sa.Column("link_note", sa.String(length=1000), nullable=True),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("relation IN ('supports','contradicts','context')", name="ck_claim_evidence_relation"),
        sa.ForeignKeyConstraint(["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_items.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("claim_revision_id", "evidence_id", "relation", name="uq_claim_evidence_relation"),
    )
    op.create_index("ix_claim_evidence_revision", "claim_evidence_links", ["claim_revision_id", "relation", "evidence_id"])
    op.create_table(
        "case_revision_claim_links",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("case_revision_id", uuid_type, nullable=False),
        sa.Column("claim_revision_id", uuid_type, nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('conclusion','context','risk')", name="ck_case_revision_claim_role"),
        sa.ForeignKeyConstraint(["case_revision_id"], ["research_case_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_revision_id", "claim_revision_id", "role", name="uq_case_revision_claim_role"),
    )
    op.create_index("ix_case_revision_claim", "case_revision_claim_links", ["case_revision_id", "role", "claim_revision_id"])
    op.create_table(
        "verification_items",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("case_revision_id", uuid_type, nullable=False),
        sa.Column("item_no", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=2000), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("item_no > 0", name="ck_verification_item_number_positive"),
        sa.CheckConstraint("status IN ('open','completed','deferred')", name="ck_verification_item_status"),
        sa.ForeignKeyConstraint(["case_revision_id"], ["research_case_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_revision_id", "item_no", name="uq_verification_item_number"),
    )
    op.create_index("ix_verification_case_revision_number", "verification_items", ["case_revision_id", "item_no"])


def downgrade() -> None:
    op.drop_index("ix_verification_case_revision_number", table_name="verification_items")
    op.drop_table("verification_items")
    op.drop_index("ix_case_revision_claim", table_name="case_revision_claim_links")
    op.drop_table("case_revision_claim_links")
    op.drop_index("ix_claim_evidence_revision", table_name="claim_evidence_links")
    op.drop_table("claim_evidence_links")
    op.drop_index("ix_claim_revision_claim_number", table_name="claim_revisions")
    op.drop_table("claim_revisions")
    op.drop_table("claims")
    op.drop_index("ix_evidence_case_information", table_name="evidence_items")
    op.drop_table("evidence_items")
    op.drop_index("ix_case_revision_case_number", table_name="research_case_revisions")
    op.drop_table("research_case_revisions")
    op.drop_table("research_cases")

"""Add V1 product research workspace metadata.

Revision ID: 20260821_0020
Revises: 20260803_0018
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260821_0020"
down_revision = "20260803_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "local_document_review_revisions",
        sa.Column("reviewer_identity", sa.String(length=128), nullable=True),
    )
    op.create_table(
        "product_research_case_profiles",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("case_type", sa.String(length=16), nullable=False),
        sa.Column("display_title", sa.String(length=300), nullable=False),
        sa.Column("industry_theme", sa.String(length=300), nullable=True),
        sa.Column("company_name", sa.String(length=300), nullable=True),
        sa.Column("stock_code", sa.String(length=32), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("case_type IN ('industry','company')", name="ck_product_case_type"),
        sa.CheckConstraint(
            "(case_type = 'industry' AND company_name IS NULL AND stock_code IS NULL) OR "
            "(case_type = 'company' AND industry_theme IS NULL)",
            name="ck_product_case_scope",
        ),
        sa.ForeignKeyConstraint(["case_id"], ["research_cases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("case_id"),
    )
    op.create_index(
        "ix_product_case_type_title",
        "product_research_case_profiles",
        ["case_type", "display_title"],
    )
    op.create_table(
        "product_research_revision_contents",
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("content_json", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("change_summary", sa.String(length=2000), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("length(content_sha256) = 64", name="ck_product_revision_content_sha"),
        sa.ForeignKeyConstraint(["revision_id"], ["research_case_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("revision_id"),
    )
    op.create_index(
        "ix_product_revision_recorded",
        "product_research_revision_contents",
        ["recorded_at_utc", "revision_id"],
    )
    op.create_table(
        "product_research_revision_evidence_references",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=False),
        sa.Column("citation_order", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=1000), nullable=True),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("citation_order > 0", name="ck_product_citation_order_positive"),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["revision_id"], ["research_case_revisions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("revision_id", "citation_order", name="uq_product_revision_citation_order"),
        sa.UniqueConstraint("revision_id", "evidence_id", name="uq_product_revision_evidence"),
    )
    op.create_index(
        "ix_product_evidence_reference",
        "product_research_revision_evidence_references",
        ["evidence_id", "revision_id"],
    )


def downgrade() -> None:
    connection = op.get_bind()
    populated = connection.execute(
        sa.text(
            "SELECT "
            "(SELECT count(*) FROM product_research_case_profiles) + "
            "(SELECT count(*) FROM product_research_revision_contents) + "
            "(SELECT count(*) FROM product_research_revision_evidence_references) + "
            "(SELECT count(*) FROM local_document_review_revisions "
            "WHERE reviewer_identity IS NOT NULL)"
        )
    ).scalar_one()
    if populated:
        raise RuntimeError(
            "Cannot downgrade V1 product workspace while append-only research data exists."
        )
    op.drop_index("ix_product_evidence_reference", table_name="product_research_revision_evidence_references")
    op.drop_table("product_research_revision_evidence_references")
    op.drop_index("ix_product_revision_recorded", table_name="product_research_revision_contents")
    op.drop_table("product_research_revision_contents")
    op.drop_index("ix_product_case_type_title", table_name="product_research_case_profiles")
    op.drop_table("product_research_case_profiles")
    op.drop_column("local_document_review_revisions", "reviewer_identity")

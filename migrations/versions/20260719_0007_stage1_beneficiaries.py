"""Add append-only Stage 1 beneficiary classifications and candidate pools.

Revision ID: 20260719_0007
Revises: 20260719_0006
Create Date: 2026-07-19
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260719_0007"
down_revision: str | None = "20260719_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = sa.Uuid()
    identity_type = sa.BigInteger().with_variant(sa.Integer(), "sqlite")
    op.create_table(
        "stage1_beneficiaries",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("case_id", uuid_type, nullable=False),
        sa.Column("map_id", uuid_type, nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"], ["research_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["map_id"], ["industry_maps.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "case_id",
            "map_id",
            "source",
            "stock_code",
            name="uq_stage1_beneficiary_identity",
        ),
    )
    op.create_index(
        "ix_stage1_beneficiary_map_stock",
        "stage1_beneficiaries",
        ["map_id", "source", "stock_code"],
    )

    op.create_table(
        "stage1_beneficiary_revisions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("beneficiary_id", uuid_type, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("selected_map_revision_id", uuid_type, nullable=False),
        sa.Column("stock_basic_record_id", identity_type, nullable=False),
        sa.Column("beneficiary_kind", sa.String(length=16), nullable=False),
        sa.Column("assessment_status", sa.String(length=16), nullable=False),
        sa.Column("rationale_summary", sa.String(length=4000), nullable=False),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid_type, nullable=True),
        sa.CheckConstraint(
            "revision_no > 0", name="ck_stage1_beneficiary_revision_positive"
        ),
        sa.CheckConstraint(
            "beneficiary_kind IN ('direct','secondary','potential')",
            name="ck_stage1_beneficiary_kind",
        ),
        sa.CheckConstraint(
            "assessment_status IN ('draft','supported','disputed','rejected')",
            name="ck_stage1_beneficiary_status",
        ),
        sa.ForeignKeyConstraint(
            ["beneficiary_id"],
            ["stage1_beneficiaries.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["selected_map_revision_id"],
            ["industry_map_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stock_basic_record_id"], ["stock_basic.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"],
            ["stage1_beneficiary_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "beneficiary_id",
            "revision_no",
            name="uq_stage1_beneficiary_revision_no",
        ),
        sa.UniqueConstraint(
            "id",
            "beneficiary_id",
            name="uq_stage1_beneficiary_revision_identity",
        ),
    )
    op.create_index(
        "ix_stage1_beneficiary_revision",
        "stage1_beneficiary_revisions",
        ["beneficiary_id", "revision_no"],
    )
    op.create_index(
        "ix_stage1_beneficiary_map_snapshot",
        "stage1_beneficiary_revisions",
        ["selected_map_revision_id", "stock_basic_record_id"],
    )

    op.create_table(
        "stage1_beneficiary_assertion_links",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("beneficiary_revision_id", uuid_type, nullable=False),
        sa.Column("node_revision_id", uuid_type, nullable=True),
        sa.Column("relationship_revision_id", uuid_type, nullable=True),
        sa.Column("observation_revision_id", uuid_type, nullable=True),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(CASE WHEN node_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN relationship_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN observation_revision_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_stage1_assertion_link_one_target",
        ),
        sa.ForeignKeyConstraint(
            ["beneficiary_revision_id"],
            ["stage1_beneficiary_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["node_revision_id"],
            ["industry_map_node_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["relationship_revision_id"],
            ["industry_map_relationship_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["observation_revision_id"],
            ["industry_map_observation_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_stage1_node_assertion_link",
        "stage1_beneficiary_assertion_links",
        ["beneficiary_revision_id", "node_revision_id"],
        unique=True,
        postgresql_where=sa.text("node_revision_id IS NOT NULL"),
        sqlite_where=sa.text("node_revision_id IS NOT NULL"),
    )
    op.create_index(
        "uq_stage1_relationship_assertion_link",
        "stage1_beneficiary_assertion_links",
        ["beneficiary_revision_id", "relationship_revision_id"],
        unique=True,
        postgresql_where=sa.text("relationship_revision_id IS NOT NULL"),
        sqlite_where=sa.text("relationship_revision_id IS NOT NULL"),
    )
    op.create_index(
        "uq_stage1_observation_assertion_link",
        "stage1_beneficiary_assertion_links",
        ["beneficiary_revision_id", "observation_revision_id"],
        unique=True,
        postgresql_where=sa.text("observation_revision_id IS NOT NULL"),
        sqlite_where=sa.text("observation_revision_id IS NOT NULL"),
    )

    op.create_table(
        "stage1_beneficiary_claim_links",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("beneficiary_revision_id", uuid_type, nullable=False),
        sa.Column("claim_revision_id", uuid_type, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["beneficiary_revision_id"],
            ["stage1_beneficiary_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "beneficiary_revision_id",
            "claim_revision_id",
            name="uq_stage1_beneficiary_claim_link",
        ),
    )
    op.create_index(
        "ix_stage1_beneficiary_claim_link",
        "stage1_beneficiary_claim_links",
        ["beneficiary_revision_id", "claim_revision_id"],
    )

    op.create_table(
        "stage1_candidate_pools",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("case_id", uuid_type, nullable=False),
        sa.Column("map_id", uuid_type, nullable=False),
        sa.Column("pool_key", sa.String(length=96), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"], ["research_cases.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["map_id"], ["industry_maps.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "case_id", "map_id", "pool_key", name="uq_stage1_candidate_pool_key"
        ),
    )
    op.create_index(
        "ix_stage1_candidate_pool_map",
        "stage1_candidate_pools",
        ["map_id", "pool_key"],
    )

    op.create_table(
        "stage1_candidate_pool_revisions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("candidate_pool_id", uuid_type, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("selected_map_revision_id", uuid_type, nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("scope", sa.String(length=4000), nullable=False),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid_type, nullable=True),
        sa.CheckConstraint(
            "revision_no > 0",
            name="ck_stage1_candidate_pool_revision_positive",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_pool_id"],
            ["stage1_candidate_pools.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["selected_map_revision_id"],
            ["industry_map_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"],
            ["stage1_candidate_pool_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_pool_id",
            "revision_no",
            name="uq_stage1_candidate_pool_revision_no",
        ),
    )
    op.create_index(
        "ix_stage1_candidate_pool_revision",
        "stage1_candidate_pool_revisions",
        ["candidate_pool_id", "revision_no"],
    )

    op.create_table(
        "stage1_candidate_pool_memberships",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("candidate_pool_revision_id", uuid_type, nullable=False),
        sa.Column("beneficiary_id", uuid_type, nullable=False),
        sa.Column("beneficiary_revision_id", uuid_type, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["candidate_pool_revision_id"],
            ["stage1_candidate_pool_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["beneficiary_revision_id", "beneficiary_id"],
            [
                "stage1_beneficiary_revisions.id",
                "stage1_beneficiary_revisions.beneficiary_id",
            ],
            name="fk_stage1_pool_membership_exact_revision",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "candidate_pool_revision_id",
            "beneficiary_id",
            name="uq_stage1_pool_beneficiary_identity",
        ),
        sa.UniqueConstraint(
            "candidate_pool_revision_id",
            "beneficiary_revision_id",
            name="uq_stage1_pool_beneficiary_revision",
        ),
    )
    op.create_index(
        "ix_stage1_candidate_pool_membership",
        "stage1_candidate_pool_memberships",
        ["candidate_pool_revision_id", "beneficiary_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_stage1_candidate_pool_membership",
        table_name="stage1_candidate_pool_memberships",
    )
    op.drop_table("stage1_candidate_pool_memberships")
    op.drop_index(
        "ix_stage1_candidate_pool_revision",
        table_name="stage1_candidate_pool_revisions",
    )
    op.drop_table("stage1_candidate_pool_revisions")
    op.drop_index(
        "ix_stage1_candidate_pool_map", table_name="stage1_candidate_pools"
    )
    op.drop_table("stage1_candidate_pools")
    op.drop_index(
        "ix_stage1_beneficiary_claim_link",
        table_name="stage1_beneficiary_claim_links",
    )
    op.drop_table("stage1_beneficiary_claim_links")
    op.drop_index(
        "uq_stage1_observation_assertion_link",
        table_name="stage1_beneficiary_assertion_links",
    )
    op.drop_index(
        "uq_stage1_relationship_assertion_link",
        table_name="stage1_beneficiary_assertion_links",
    )
    op.drop_index(
        "uq_stage1_node_assertion_link",
        table_name="stage1_beneficiary_assertion_links",
    )
    op.drop_table("stage1_beneficiary_assertion_links")
    op.drop_index(
        "ix_stage1_beneficiary_map_snapshot",
        table_name="stage1_beneficiary_revisions",
    )
    op.drop_index(
        "ix_stage1_beneficiary_revision",
        table_name="stage1_beneficiary_revisions",
    )
    op.drop_table("stage1_beneficiary_revisions")
    op.drop_index(
        "ix_stage1_beneficiary_map_stock", table_name="stage1_beneficiaries"
    )
    op.drop_table("stage1_beneficiaries")

"""Add append-only typed beneficiary evidence semantics.

Revision ID: 20260721_0012
Revises: 20260719_0011
Create Date: 2026-07-21
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260721_0012"
down_revision: str | None = "20260719_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = (
    "stage1_beneficiary_semantic_profiles",
    "stage1_beneficiary_semantic_profile_revisions",
    "stage1_beneficiary_semantic_assertions",
    "stage1_beneficiary_semantic_assertion_claim_links",
    "stage1_beneficiary_semantic_verification_items",
)


def upgrade() -> None:
    uuid = sa.Uuid()
    op.create_table(
        "stage1_beneficiary_semantic_profiles",
        sa.Column("id", uuid, nullable=False),
        sa.Column("beneficiary_id", uuid, nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["beneficiary_id"], ["stage1_beneficiaries.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "beneficiary_id", name="uq_stage1_beneficiary_semantic_profile"
        ),
    )
    op.create_index(
        "ix_stage1_beneficiary_semantic_profile",
        "stage1_beneficiary_semantic_profiles",
        ["beneficiary_id"],
    )

    op.create_table(
        "stage1_beneficiary_semantic_profile_revisions",
        sa.Column("id", uuid, nullable=False),
        sa.Column("profile_id", uuid, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("beneficiary_revision_id", uuid, nullable=False),
        sa.Column("selected_map_revision_id", uuid, nullable=False),
        sa.Column("taxonomy_version", sa.String(96), nullable=False),
        sa.Column("overall_status", sa.String(16), nullable=False),
        sa.Column("summary", sa.String(4000), nullable=False),
        sa.Column("recorded_by", sa.String(100), nullable=False),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid, nullable=True),
        sa.CheckConstraint(
            "revision_no > 0", name="ck_stage1_beneficiary_semantic_revision_positive"
        ),
        sa.CheckConstraint(
            "taxonomy_version = 'aquantai.typed-beneficiary-evidence-semantics.v1'",
            name="ck_stage1_beneficiary_semantic_taxonomy_version",
        ),
        sa.CheckConstraint(
            "overall_status IN ('draft','supported','disputed','rejected')",
            name="ck_stage1_beneficiary_semantic_overall_status",
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["stage1_beneficiary_semantic_profiles.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["beneficiary_revision_id"],
            ["stage1_beneficiary_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["selected_map_revision_id"],
            ["industry_map_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"],
            ["stage1_beneficiary_semantic_profile_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_id", "revision_no", name="uq_stage1_beneficiary_semantic_revision_no"
        ),
    )
    op.create_index(
        "ix_stage1_beneficiary_semantic_revision",
        "stage1_beneficiary_semantic_profile_revisions",
        ["profile_id", "revision_no"],
    )
    op.create_index(
        "ix_stage1_beneficiary_semantic_frozen",
        "stage1_beneficiary_semantic_profile_revisions",
        ["beneficiary_revision_id", "selected_map_revision_id"],
    )

    op.create_table(
        "stage1_beneficiary_semantic_assertions",
        sa.Column("id", uuid, nullable=False),
        sa.Column("profile_revision_id", uuid, nullable=False),
        sa.Column("assertion_key", sa.String(96), nullable=False),
        sa.Column("field_kind", sa.String(24), nullable=False),
        sa.Column("state_code", sa.String(96), nullable=False),
        sa.Column("evidence_state", sa.String(24), nullable=False),
        sa.Column("subject_text", sa.String(500), nullable=True),
        sa.Column("rationale", sa.String(4000), nullable=False),
        sa.Column("map_observation_revision_id", uuid, nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "field_kind IN ('exposure','driver','offering','customer','certification','capacity','production','order')",
            name="ck_stage1_beneficiary_semantic_field_kind",
        ),
        sa.CheckConstraint(
            "evidence_state IN ('supported','disputed','missing','not_applicable')",
            name="ck_stage1_beneficiary_semantic_evidence_state",
        ),
        sa.CheckConstraint(
            "position >= 0", name="ck_stage1_beneficiary_semantic_position"
        ),
        sa.CheckConstraint(
            "(field_kind = 'driver' AND map_observation_revision_id IS NOT NULL) OR "
            "(field_kind <> 'driver' AND map_observation_revision_id IS NULL)",
            name="ck_stage1_beneficiary_semantic_driver_observation",
        ),
        sa.ForeignKeyConstraint(
            ["profile_revision_id"],
            ["stage1_beneficiary_semantic_profile_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["map_observation_revision_id"],
            ["industry_map_observation_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "profile_revision_id",
            "assertion_key",
            name="uq_stage1_beneficiary_semantic_assertion_key",
        ),
    )
    op.create_index(
        "ix_stage1_beneficiary_semantic_assertion",
        "stage1_beneficiary_semantic_assertions",
        ["profile_revision_id", "field_kind", "position"],
    )

    op.create_table(
        "stage1_beneficiary_semantic_assertion_claim_links",
        sa.Column("id", uuid, nullable=False),
        sa.Column("assertion_id", uuid, nullable=False),
        sa.Column("claim_revision_id", uuid, nullable=False),
        sa.Column("relation", sa.String(16), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "relation IN ('support','contradict','context')",
            name="ck_stage1_beneficiary_semantic_claim_relation",
        ),
        sa.ForeignKeyConstraint(
            ["assertion_id"],
            ["stage1_beneficiary_semantic_assertions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "assertion_id",
            "claim_revision_id",
            "relation",
            name="uq_stage1_beneficiary_semantic_assertion_claim",
        ),
    )
    op.create_index(
        "ix_stage1_beneficiary_semantic_assertion_claim",
        "stage1_beneficiary_semantic_assertion_claim_links",
        ["assertion_id", "relation", "claim_revision_id"],
    )

    op.create_table(
        "stage1_beneficiary_semantic_verification_items",
        sa.Column("id", uuid, nullable=False),
        sa.Column("profile_revision_id", uuid, nullable=False),
        sa.Column("assertion_id", uuid, nullable=True),
        sa.Column("verification_question", sa.String(2000), nullable=False),
        sa.Column("expected_evidence_type", sa.String(500), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status = 'open'", name="ck_stage1_beneficiary_semantic_verification_open"
        ),
        sa.ForeignKeyConstraint(
            ["profile_revision_id"],
            ["stage1_beneficiary_semantic_profile_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assertion_id"],
            ["stage1_beneficiary_semantic_assertions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_stage1_beneficiary_semantic_verification",
        "stage1_beneficiary_semantic_verification_items",
        ["profile_revision_id", "assertion_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    populated = [
        table
        for table in _TABLES
        if bind.execute(sa.text(f"SELECT 1 FROM {table} LIMIT 1")).first() is not None
    ]
    if populated:
        raise RuntimeError(
            "Cannot downgrade typed beneficiary evidence semantics while semantic history exists. "
            "Preserve or explicitly migrate the append-only records first."
        )

    op.drop_index(
        "ix_stage1_beneficiary_semantic_verification",
        table_name="stage1_beneficiary_semantic_verification_items",
    )
    op.drop_table("stage1_beneficiary_semantic_verification_items")
    op.drop_index(
        "ix_stage1_beneficiary_semantic_assertion_claim",
        table_name="stage1_beneficiary_semantic_assertion_claim_links",
    )
    op.drop_table("stage1_beneficiary_semantic_assertion_claim_links")
    op.drop_index(
        "ix_stage1_beneficiary_semantic_assertion",
        table_name="stage1_beneficiary_semantic_assertions",
    )
    op.drop_table("stage1_beneficiary_semantic_assertions")
    op.drop_index(
        "ix_stage1_beneficiary_semantic_frozen",
        table_name="stage1_beneficiary_semantic_profile_revisions",
    )
    op.drop_index(
        "ix_stage1_beneficiary_semantic_revision",
        table_name="stage1_beneficiary_semantic_profile_revisions",
    )
    op.drop_table("stage1_beneficiary_semantic_profile_revisions")
    op.drop_index(
        "ix_stage1_beneficiary_semantic_profile",
        table_name="stage1_beneficiary_semantic_profiles",
    )
    op.drop_table("stage1_beneficiary_semantic_profiles")

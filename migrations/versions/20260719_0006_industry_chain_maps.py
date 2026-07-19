"""Add append-only evidence-backed industry chain maps.

Revision ID: 20260719_0006
Revises: 20260718_0005
Create Date: 2026-07-19
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260719_0006"
down_revision: str | None = "20260718_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    uuid_type = sa.Uuid()
    op.create_table(
        "industry_maps",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("case_id", uuid_type, nullable=False),
        sa.Column("map_key", sa.String(length=96), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["research_cases.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("case_id", "map_key", name="uq_industry_map_case_key"),
    )
    op.create_index("ix_industry_map_case_key", "industry_maps", ["case_id", "map_key"])

    op.create_table(
        "industry_map_revisions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("map_id", uuid_type, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("scope", sa.String(length=4000), nullable=False),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid_type, nullable=True),
        sa.CheckConstraint("revision_no > 0", name="ck_industry_map_revision_positive"),
        sa.ForeignKeyConstraint(["map_id"], ["industry_maps.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"],
            ["industry_map_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("map_id", "revision_no", name="uq_industry_map_revision_no"),
    )
    op.create_index(
        "ix_industry_map_revision", "industry_map_revisions", ["map_id", "revision_no"]
    )

    op.create_table(
        "industry_map_nodes",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("map_id", uuid_type, nullable=False),
        sa.Column("node_key", sa.String(length=96), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["map_id"], ["industry_maps.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("map_id", "node_key", name="uq_industry_map_node_key"),
    )
    op.create_index("ix_industry_map_node", "industry_map_nodes", ["map_id", "node_key"])

    op.create_table(
        "industry_map_node_revisions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("node_id", uuid_type, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=300), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=True),
        sa.Column("node_kind", sa.String(length=32), nullable=False),
        sa.Column("assertion_status", sa.String(length=16), nullable=False),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid_type, nullable=True),
        sa.CheckConstraint("revision_no > 0", name="ck_industry_node_revision_positive"),
        sa.CheckConstraint(
            "node_kind IN ('upstream_input','equipment','component','manufacturing',"
            "'distribution','service','customer_end_market',"
            "'regulation_infrastructure','other')",
            name="ck_industry_node_kind",
        ),
        sa.CheckConstraint(
            "assertion_status IN ('draft','supported','disputed','rejected')",
            name="ck_industry_node_status",
        ),
        sa.ForeignKeyConstraint(["node_id"], ["industry_map_nodes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"],
            ["industry_map_node_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("node_id", "revision_no", name="uq_industry_node_revision_no"),
    )
    op.create_index(
        "ix_industry_node_revision",
        "industry_map_node_revisions",
        ["node_id", "revision_no"],
    )

    op.create_table(
        "industry_map_relationships",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("map_id", uuid_type, nullable=False),
        sa.Column("relationship_key", sa.String(length=96), nullable=False),
        sa.Column("source_node_id", uuid_type, nullable=False),
        sa.Column("target_node_id", uuid_type, nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "source_node_id <> target_node_id",
            name="ck_industry_relationship_distinct_nodes",
        ),
        sa.ForeignKeyConstraint(["map_id"], ["industry_maps.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["source_node_id"], ["industry_map_nodes.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id"], ["industry_map_nodes.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "map_id", "relationship_key", name="uq_industry_map_relationship_key"
        ),
    )
    op.create_index(
        "ix_industry_map_relationship",
        "industry_map_relationships",
        ["map_id", "relationship_key"],
    )

    op.create_table(
        "industry_map_relationship_revisions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("relationship_id", uuid_type, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("relation_kind", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=True),
        sa.Column("assertion_status", sa.String(length=16), nullable=False),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid_type, nullable=True),
        sa.CheckConstraint(
            "revision_no > 0", name="ck_industry_relationship_revision_positive"
        ),
        sa.CheckConstraint(
            "relation_kind IN ('supplies','enables','depends_on','substitutes',"
            "'competes_with','distributes_to','regulates','other')",
            name="ck_industry_relationship_kind",
        ),
        sa.CheckConstraint(
            "assertion_status IN ('draft','supported','disputed','rejected')",
            name="ck_industry_relationship_status",
        ),
        sa.ForeignKeyConstraint(
            ["relationship_id"], ["industry_map_relationships.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"],
            ["industry_map_relationship_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "relationship_id", "revision_no", name="uq_industry_relationship_revision_no"
        ),
    )
    op.create_index(
        "ix_industry_relationship_revision",
        "industry_map_relationship_revisions",
        ["relationship_id", "revision_no"],
    )

    op.create_table(
        "industry_map_observations",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("map_id", uuid_type, nullable=False),
        sa.Column("observation_key", sa.String(length=96), nullable=False),
        sa.Column("observation_kind", sa.String(length=32), nullable=False),
        sa.Column("created_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "observation_kind IN ('driver','bottleneck','value_pool_shift')",
            name="ck_industry_observation_kind",
        ),
        sa.ForeignKeyConstraint(["map_id"], ["industry_maps.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "map_id", "observation_key", name="uq_industry_map_observation_key"
        ),
    )
    op.create_index(
        "ix_industry_map_observation",
        "industry_map_observations",
        ["map_id", "observation_key"],
    )

    op.create_table(
        "industry_map_observation_revisions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("observation_id", uuid_type, nullable=False),
        sa.Column("revision_no", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=True),
        sa.Column("assertion_status", sa.String(length=16), nullable=False),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_revision_id", uuid_type, nullable=True),
        sa.CheckConstraint(
            "revision_no > 0", name="ck_industry_observation_revision_positive"
        ),
        sa.CheckConstraint(
            "assertion_status IN ('draft','supported','disputed','rejected')",
            name="ck_industry_observation_status",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id"], ["industry_map_observations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["supersedes_revision_id"],
            ["industry_map_observation_revisions.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "observation_id", "revision_no", name="uq_industry_observation_revision_no"
        ),
    )
    op.create_index(
        "ix_industry_observation_revision",
        "industry_map_observation_revisions",
        ["observation_id", "revision_no"],
    )

    op.create_table(
        "industry_map_assertion_claim_links",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("node_revision_id", uuid_type, nullable=True),
        sa.Column("relationship_revision_id", uuid_type, nullable=True),
        sa.Column("observation_revision_id", uuid_type, nullable=True),
        sa.Column("claim_revision_id", uuid_type, nullable=False),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(CASE WHEN node_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN relationship_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN observation_revision_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_industry_assertion_link_one_target",
        ),
        sa.ForeignKeyConstraint(
            ["node_revision_id"], ["industry_map_node_revisions.id"], ondelete="RESTRICT"
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
        sa.ForeignKeyConstraint(
            ["claim_revision_id"], ["claim_revisions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_industry_node_claim_link",
        "industry_map_assertion_claim_links",
        ["node_revision_id", "claim_revision_id"],
        unique=True,
        postgresql_where=sa.text("node_revision_id IS NOT NULL"),
        sqlite_where=sa.text("node_revision_id IS NOT NULL"),
    )
    op.create_index(
        "uq_industry_relationship_claim_link",
        "industry_map_assertion_claim_links",
        ["relationship_revision_id", "claim_revision_id"],
        unique=True,
        postgresql_where=sa.text("relationship_revision_id IS NOT NULL"),
        sqlite_where=sa.text("relationship_revision_id IS NOT NULL"),
    )
    op.create_index(
        "uq_industry_observation_claim_link",
        "industry_map_assertion_claim_links",
        ["observation_revision_id", "claim_revision_id"],
        unique=True,
        postgresql_where=sa.text("observation_revision_id IS NOT NULL"),
        sqlite_where=sa.text("observation_revision_id IS NOT NULL"),
    )

    op.create_table(
        "industry_map_revision_memberships",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("map_revision_id", uuid_type, nullable=False),
        sa.Column("node_revision_id", uuid_type, nullable=True),
        sa.Column("relationship_revision_id", uuid_type, nullable=True),
        sa.Column("observation_revision_id", uuid_type, nullable=True),
        sa.Column("recorded_at_utc", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(CASE WHEN node_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN relationship_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
            "CASE WHEN observation_revision_id IS NOT NULL THEN 1 ELSE 0 END) = 1",
            name="ck_industry_membership_one_target",
        ),
        sa.ForeignKeyConstraint(
            ["map_revision_id"], ["industry_map_revisions.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["node_revision_id"], ["industry_map_node_revisions.id"], ondelete="RESTRICT"
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
        "uq_industry_map_node_membership",
        "industry_map_revision_memberships",
        ["map_revision_id", "node_revision_id"],
        unique=True,
        postgresql_where=sa.text("node_revision_id IS NOT NULL"),
        sqlite_where=sa.text("node_revision_id IS NOT NULL"),
    )
    op.create_index(
        "uq_industry_map_relationship_membership",
        "industry_map_revision_memberships",
        ["map_revision_id", "relationship_revision_id"],
        unique=True,
        postgresql_where=sa.text("relationship_revision_id IS NOT NULL"),
        sqlite_where=sa.text("relationship_revision_id IS NOT NULL"),
    )
    op.create_index(
        "uq_industry_map_observation_membership",
        "industry_map_revision_memberships",
        ["map_revision_id", "observation_revision_id"],
        unique=True,
        postgresql_where=sa.text("observation_revision_id IS NOT NULL"),
        sqlite_where=sa.text("observation_revision_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_industry_map_observation_membership",
        table_name="industry_map_revision_memberships",
    )
    op.drop_index(
        "uq_industry_map_relationship_membership",
        table_name="industry_map_revision_memberships",
    )
    op.drop_index(
        "uq_industry_map_node_membership",
        table_name="industry_map_revision_memberships",
    )
    op.drop_table("industry_map_revision_memberships")
    op.drop_index(
        "uq_industry_observation_claim_link",
        table_name="industry_map_assertion_claim_links",
    )
    op.drop_index(
        "uq_industry_relationship_claim_link",
        table_name="industry_map_assertion_claim_links",
    )
    op.drop_index(
        "uq_industry_node_claim_link",
        table_name="industry_map_assertion_claim_links",
    )
    op.drop_table("industry_map_assertion_claim_links")
    op.drop_index(
        "ix_industry_observation_revision",
        table_name="industry_map_observation_revisions",
    )
    op.drop_table("industry_map_observation_revisions")
    op.drop_index("ix_industry_map_observation", table_name="industry_map_observations")
    op.drop_table("industry_map_observations")
    op.drop_index(
        "ix_industry_relationship_revision",
        table_name="industry_map_relationship_revisions",
    )
    op.drop_table("industry_map_relationship_revisions")
    op.drop_index(
        "ix_industry_map_relationship", table_name="industry_map_relationships"
    )
    op.drop_table("industry_map_relationships")
    op.drop_index("ix_industry_node_revision", table_name="industry_map_node_revisions")
    op.drop_table("industry_map_node_revisions")
    op.drop_index("ix_industry_map_node", table_name="industry_map_nodes")
    op.drop_table("industry_map_nodes")
    op.drop_index("ix_industry_map_revision", table_name="industry_map_revisions")
    op.drop_table("industry_map_revisions")
    op.drop_index("ix_industry_map_case_key", table_name="industry_maps")
    op.drop_table("industry_maps")

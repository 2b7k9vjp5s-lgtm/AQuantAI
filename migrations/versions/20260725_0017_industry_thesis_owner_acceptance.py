"""Add Industry Thesis owner acceptance exact output links.

Revision ID: 20260725_0017
Revises: 20260722_0016
Create Date: 2026-07-25
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260725_0017"
down_revision: str | None = "20260722_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "industry_thesis_output_link_revisions"
_NEW_COLUMNS = {
    "accepted_session_revision_id",
    "reviewed_session_revision_id",
    "research_case_id",
    "output_contract_version",
    "reviewed_plan_fingerprint_sha256",
    "ordered_owner_output_bindings_json",
}


def _has_rows(bind: sa.Connection) -> bool:
    table = sa.table(_TABLE, sa.column("id"))
    return (
        bind.execute(sa.select(sa.literal(1)).select_from(table).limit(1)).first()
        is not None
    )


def _column_names(bind: sa.Connection) -> set[str]:
    return {item["name"] for item in sa.inspect(bind).get_columns(_TABLE)}


def _batch() -> object:
    bind = op.get_bind()
    recreate = "always" if bind.dialect.name == "sqlite" else "auto"
    return op.batch_alter_table(_TABLE, recreate=recreate)


def _legacy_output_table() -> sa.Table:
    """Return the exact empty 0016 output-revision table definition.

    Migration 0016 imports current ORM metadata, so a fresh installation can
    materialize the v1 shape before 0017 runs. Downgrade is allowed only while
    this table is empty; rebuilding that empty table from a frozen local schema
    avoids dialect-dependent batch reflection of constraints on removed columns.
    """

    metadata = sa.MetaData()
    for table_name in (
        "industry_thesis_output_link_identities",
        "industry_thesis_session_revisions",
        "industry_maps",
        "industry_map_revisions",
        "stage1_candidate_pool_revisions",
    ):
        sa.Table(
            table_name,
            metadata,
            sa.Column("id", sa.Uuid(), primary_key=True),
        )

    return sa.Table(
        _TABLE,
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "output_link_id",
            sa.Uuid(),
            sa.ForeignKey(
                "industry_thesis_output_link_identities.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column(
            "session_revision_id",
            sa.Uuid(),
            sa.ForeignKey(
                "industry_thesis_session_revisions.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "accepted_industry_map_identity_id",
            sa.Uuid(),
            sa.ForeignKey("industry_maps.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "accepted_industry_map_revision_id",
            sa.Uuid(),
            sa.ForeignKey("industry_map_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "accepted_candidate_pool_revision_id",
            sa.Uuid(),
            sa.ForeignKey(
                "stage1_candidate_pool_revisions.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "ordered_beneficiary_revision_ids_json",
            sa.Text(),
            nullable=False,
        ),
        sa.Column("coverage_state", sa.String(length=32), nullable=False),
        sa.Column(
            "acceptance_plan_fingerprint_sha256",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column("owner_transaction_id", sa.String(length=128), nullable=False),
        sa.Column("information_cutoff_date", sa.Date(), nullable=False),
        sa.Column(
            "recorded_at_utc",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "supersedes_output_link_revision_id",
            sa.Uuid(),
            sa.ForeignKey(
                f"{_TABLE}.id",
                ondelete="RESTRICT",
            ),
        ),
        sa.UniqueConstraint(
            "output_link_id",
            "revision_number",
            name="uq_industry_thesis_output_link_revision_number",
        ),
        sa.CheckConstraint(
            "revision_number > 0",
            name="ck_industry_thesis_output_revision_positive",
        ),
        sa.CheckConstraint(
            "coverage_state IN "
            "('reviewed_local_scope','partial_local_coverage','coverage_unknown')",
            name="ck_industry_thesis_output_coverage",
        ),
        sa.CheckConstraint(
            "length(acceptance_plan_fingerprint_sha256) = 64",
            name="ck_industry_thesis_output_plan_fingerprint",
        ),
        sa.Index(
            "ix_industry_thesis_output_revision",
            "output_link_id",
            "revision_number",
        ),
    )


def upgrade() -> None:
    """Upgrade only an empty deterministic schema; never guess history."""

    bind = op.get_bind()
    if _has_rows(bind):
        raise RuntimeError(
            "Cannot upgrade Industry Thesis output links while legacy rows exist: "
            "accepted/reviewed session, Research Case and per-candidate owner bindings "
            "cannot be derived without guessing. Preserve the database and perform a "
            "separately reviewed deterministic migration first."
        )

    present = _column_names(bind) & _NEW_COLUMNS
    if present:
        if present != _NEW_COLUMNS:
            missing = ", ".join(sorted(_NEW_COLUMNS - present))
            raise RuntimeError(
                "Cannot upgrade a partially materialized Industry Thesis owner-acceptance "
                f"schema. Missing exact columns: {missing}."
            )
        # Migration 0016 historically imports the current ORM table objects. On a fresh
        # install it can therefore materialize the complete 0017 table shape before this
        # revision runs. The table is empty and complete, so stamping 0017 is safe and
        # preserves the same final schema without rewriting the accepted 0016 migration.
        return

    with _batch() as batch:
        batch.alter_column(
            "accepted_candidate_pool_revision_id",
            existing_type=sa.Uuid(),
            nullable=True,
        )
        batch.add_column(
            sa.Column("accepted_session_revision_id", sa.Uuid(), nullable=False)
        )
        batch.add_column(
            sa.Column("reviewed_session_revision_id", sa.Uuid(), nullable=False)
        )
        batch.add_column(sa.Column("research_case_id", sa.Uuid(), nullable=False))
        batch.add_column(
            sa.Column("output_contract_version", sa.String(length=128), nullable=False)
        )
        batch.add_column(
            sa.Column(
                "reviewed_plan_fingerprint_sha256",
                sa.String(length=64),
                nullable=False,
            )
        )
        batch.add_column(
            sa.Column(
                "ordered_owner_output_bindings_json",
                sa.Text(),
                nullable=False,
            )
        )
        batch.create_foreign_key(
            "fk_industry_thesis_output_accepted_session",
            "industry_thesis_session_revisions",
            ["accepted_session_revision_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_industry_thesis_output_reviewed_session",
            "industry_thesis_session_revisions",
            ["reviewed_session_revision_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_industry_thesis_output_research_case",
            "research_cases",
            ["research_case_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_unique_constraint(
            "uq_industry_thesis_output_accepted_session",
            ["accepted_session_revision_id"],
        )
        batch.create_check_constraint(
            "ck_industry_thesis_output_reviewed_plan_fingerprint",
            "length(reviewed_plan_fingerprint_sha256) = 64",
        )
        batch.create_check_constraint(
            "ck_industry_thesis_output_contract_version",
            "length(trim(output_contract_version)) > 0",
        )
        batch.create_check_constraint(
            "ck_industry_thesis_output_owner_bindings",
            "length(ordered_owner_output_bindings_json) > 2",
        )
        batch.create_index(
            "ix_industry_thesis_output_reviewed_session",
            ["reviewed_session_revision_id"],
            unique=False,
        )


def downgrade() -> None:
    """Refuse populated history, otherwise rebuild the exact empty 0016 table."""

    bind = op.get_bind()
    if _has_rows(bind):
        raise RuntimeError(
            "Cannot downgrade Industry Thesis owner acceptance while v1 output-link "
            "history exists. The nullable handoff and exact owner bindings would be lost."
        )

    op.drop_table(_TABLE)
    _legacy_output_table().create(bind=bind, checkfirst=False)

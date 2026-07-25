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


def _has_rows(bind: sa.Connection) -> bool:
    table = sa.table(_TABLE, sa.column("id"))
    return (
        bind.execute(sa.select(sa.literal(1)).select_from(table).limit(1)).first()
        is not None
    )


def _batch() -> object:
    bind = op.get_bind()
    recreate = "always" if bind.dialect.name == "sqlite" else "auto"
    return op.batch_alter_table(_TABLE, recreate=recreate)


def upgrade() -> None:
    """Upgrade only an empty legacy output-link table; never guess history."""

    bind = op.get_bind()
    if _has_rows(bind):
        raise RuntimeError(
            "Cannot upgrade Industry Thesis output links while legacy rows exist: "
            "accepted/reviewed session, Research Case and per-candidate owner bindings "
            "cannot be derived without guessing. Preserve the database and perform a "
            "separately reviewed deterministic migration first."
        )

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
    """Refuse before any lossy operation when v1 output-link rows exist."""

    bind = op.get_bind()
    if _has_rows(bind):
        raise RuntimeError(
            "Cannot downgrade Industry Thesis owner acceptance while v1 output-link "
            "history exists. The nullable handoff and exact owner bindings would be lost."
        )

    with _batch() as batch:
        batch.drop_index("ix_industry_thesis_output_reviewed_session")
        batch.drop_constraint(
            "ck_industry_thesis_output_owner_bindings",
            type_="check",
        )
        batch.drop_constraint(
            "ck_industry_thesis_output_contract_version",
            type_="check",
        )
        batch.drop_constraint(
            "ck_industry_thesis_output_reviewed_plan_fingerprint",
            type_="check",
        )
        batch.drop_constraint(
            "uq_industry_thesis_output_accepted_session",
            type_="unique",
        )
        batch.drop_constraint(
            "fk_industry_thesis_output_research_case",
            type_="foreignkey",
        )
        batch.drop_constraint(
            "fk_industry_thesis_output_reviewed_session",
            type_="foreignkey",
        )
        batch.drop_constraint(
            "fk_industry_thesis_output_accepted_session",
            type_="foreignkey",
        )
        batch.drop_column("ordered_owner_output_bindings_json")
        batch.drop_column("reviewed_plan_fingerprint_sha256")
        batch.drop_column("output_contract_version")
        batch.drop_column("research_case_id")
        batch.drop_column("reviewed_session_revision_id")
        batch.drop_column("accepted_session_revision_id")
        batch.alter_column(
            "accepted_candidate_pool_revision_id",
            existing_type=sa.Uuid(),
            nullable=False,
        )

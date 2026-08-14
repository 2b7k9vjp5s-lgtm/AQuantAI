"""Add exact Research Case Revision bindings for accepted research owners.

Revision ID: 20260814_0019
Revises: 20260803_0018
Create Date: 2026-08-14
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260814_0019"
down_revision: str | None = "20260803_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDUSTRY_BINDING_TABLE = "industry_thesis_output_case_revision_bindings"
_STAGE2_BINDING_TABLE = "stage2_company_research_revision_case_bindings"
_INDUSTRY_BINDING_VERSION = "aquantai.industry-thesis-output-case-revision-binding.v1"
_STAGE2_BINDING_VERSION = "aquantai.stage2-company-research-case-revision-binding.v1"


def upgrade() -> None:
    op.create_table(
        _INDUSTRY_BINDING_TABLE,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "output_link_revision_id",
            sa.Uuid(),
            sa.ForeignKey(
                "industry_thesis_output_link_revisions.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "research_case_revision_id",
            sa.Uuid(),
            sa.ForeignKey("research_case_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("binding_contract_version", sa.String(128), nullable=False),
        sa.UniqueConstraint(
            "output_link_revision_id",
            name="uq_industry_thesis_output_case_revision_binding_owner",
        ),
        sa.CheckConstraint(
            f"binding_contract_version = '{_INDUSTRY_BINDING_VERSION}'",
            name="ck_industry_thesis_output_case_revision_binding_version",
        ),
    )
    op.create_index(
        "ix_industry_thesis_output_case_revision_binding_case_revision",
        _INDUSTRY_BINDING_TABLE,
        ["research_case_revision_id", "output_link_revision_id"],
    )

    op.create_table(
        _STAGE2_BINDING_TABLE,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "company_research_revision_id",
            sa.Uuid(),
            sa.ForeignKey(
                "stage2_company_research_revisions.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),
        sa.Column(
            "research_case_revision_id",
            sa.Uuid(),
            sa.ForeignKey("research_case_revisions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("binding_contract_version", sa.String(128), nullable=False),
        sa.UniqueConstraint(
            "company_research_revision_id",
            name="uq_stage2_company_research_revision_case_binding_owner",
        ),
        sa.CheckConstraint(
            f"binding_contract_version = '{_STAGE2_BINDING_VERSION}'",
            name="ck_stage2_company_research_revision_case_binding_version",
        ),
    )
    op.create_index(
        "ix_stage2_company_research_revision_case_binding_case_revision",
        _STAGE2_BINDING_TABLE,
        ["research_case_revision_id", "company_research_revision_id"],
    )


def downgrade() -> None:
    bind = op.get_bind()
    for table_name in (_INDUSTRY_BINDING_TABLE, _STAGE2_BINDING_TABLE):
        table = sa.table(table_name, sa.column("id"))
        if bind.execute(sa.select(sa.literal(1)).select_from(table).limit(1)).first():
            raise RuntimeError(
                "Cannot downgrade exact Research Case Revision bindings while immutable "
                "binding history exists. Preserve the database."
            )
    op.drop_table(_STAGE2_BINDING_TABLE)
    op.drop_table(_INDUSTRY_BINDING_TABLE)

"""Add offline industry-thesis orchestration append-only histories.

Revision ID: 20260722_0016
Revises: 20260722_0015
Create Date: 2026-07-22
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

from industry_alpha.industry_thesis_models import INDUSTRY_THESIS_MODELS

revision: str = "20260722_0016"
down_revision: str | None = "20260722_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = tuple(model.__table__ for model in INDUSTRY_THESIS_MODELS)


def upgrade() -> None:
    """Create exactly the six reviewed additive tables, without backfill."""
    bind = op.get_bind()
    for table in _TABLES:
        table.create(bind=bind, checkfirst=False)


def downgrade() -> None:
    """Refuse before any drop when industry-thesis history exists."""
    bind = op.get_bind()
    populated = [
        table.name
        for table in _TABLES
        if bind.execute(sa.select(sa.literal(1)).select_from(table).limit(1)).first()
        is not None
    ]
    if populated:
        raise RuntimeError(
            "Cannot downgrade Industry Thesis Orchestration while append-only history exists. "
            "Preserve or explicitly migrate the records first."
        )
    for table in reversed(_TABLES):
        table.drop(bind=bind, checkfirst=False)

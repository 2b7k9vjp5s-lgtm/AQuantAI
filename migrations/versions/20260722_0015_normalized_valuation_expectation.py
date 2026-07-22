"""Add normalized valuation and expectation append-only histories.

Revision ID: 20260722_0015
Revises: 20260722_0014
Create Date: 2026-07-22
"""

from __future__ import annotations

from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

import industry_alpha.normalized_valuation_context  # noqa: F401 - install typed context columns
from industry_alpha.normalized_valuation_models import NORMALIZED_VALUATION_MODELS

revision: str = "20260722_0015"
down_revision: str | None = "20260722_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = tuple(model.__table__ for model in NORMALIZED_VALUATION_MODELS)


def upgrade() -> None:
    """Create exactly the thirteen reviewed additive tables, without backfill."""
    bind = op.get_bind()
    for table in _TABLES:
        table.create(bind=bind, checkfirst=False)


def downgrade() -> None:
    """Refuse before any drop when normalized valuation history exists."""
    bind = op.get_bind()
    populated = [
        table.name
        for table in _TABLES
        if bind.execute(sa.select(sa.literal(1)).select_from(table).limit(1)).first()
        is not None
    ]
    if populated:
        raise RuntimeError(
            "Cannot downgrade Normalized Valuation and Expectation Metrics while "
            "append-only history exists. Preserve or explicitly migrate the records first."
        )
    for table in reversed(_TABLES):
        table.drop(bind=bind, checkfirst=False)

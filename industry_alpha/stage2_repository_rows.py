"""Neutral ordered row-loading mechanics shared by Stage 2 repositories."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

_RowT = TypeVar("_RowT")


def load_ordered_rows(
    session: Session,
    model: type[_RowT],
    field: Any,
    ids: Sequence[Any],
    *order_fields: Any,
) -> tuple[_RowT, ...]:
    """Load rows selected by explicit IDs and caller-owned ordering."""

    if not ids:
        return ()
    return tuple(
        session.scalars(
            select(model).where(field.in_(ids)).order_by(*order_fields)
        )
    )

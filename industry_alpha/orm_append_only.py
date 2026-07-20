"""Neutral SQLAlchemy append-only mutation scan."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from industry_alpha.errors import EvidenceLedgerImmutableError


def reject_append_only_mutation(
    session: Session,
    model_types: tuple[type[Any], ...],
) -> None:
    """Reject ORM updates and deletes for the supplied append-only model types."""

    for row in session.deleted:
        if isinstance(row, model_types):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be deleted."
            )
    for row in session.dirty:
        if isinstance(row, model_types) and session.is_modified(
            row, include_collections=False
        ):
            raise EvidenceLedgerImmutableError(
                f"{type(row).__name__} rows are append-only and cannot be updated."
            )

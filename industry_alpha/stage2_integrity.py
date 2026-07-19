"""Integrity-error translation shared by Stage 2 command services."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.exc import IntegrityError

from industry_alpha.errors import EvidenceLedgerConflictError


@contextmanager
def translate_integrity(message: str) -> Iterator[None]:
    """Translate only SQLAlchemy integrity failures to the domain conflict."""

    try:
        yield
    except IntegrityError as exc:
        raise EvidenceLedgerConflictError(message) from exc

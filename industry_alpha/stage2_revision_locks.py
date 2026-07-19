"""Process-local revision locks shared by Stage 2 command services."""

from __future__ import annotations

from threading import Lock, RLock
from uuid import UUID


_LOCKS_GUARD = Lock()
_LOCKS: dict[tuple[str, UUID], RLock] = {}


def revision_lock(kind: str, identity: UUID) -> RLock:
    """Return the process-local reentrant lock for an exact revision key."""

    key = (kind, identity)
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, RLock())

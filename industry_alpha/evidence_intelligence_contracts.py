"""JSON-ready contracts for the read-only Evidence Intelligence feed."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class EvidenceIntelligenceFeedContract:
    evaluated_at_utc: str
    as_of_cutoff: str | None
    recorded_from: str
    recorded_to: str
    event_type: str | None
    limit: int
    events: tuple[dict[str, Any], ...]
    next_cursor: str | None
    notices: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

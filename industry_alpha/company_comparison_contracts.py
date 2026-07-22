"""JSON-ready contract for the read-only Company Research Comparison Matrix."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class CompanyComparisonContract:
    selector: dict[str, Any]
    universe: dict[str, Any]
    rows: tuple[dict[str, Any], ...]
    notices: dict[str, Any]
    query_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

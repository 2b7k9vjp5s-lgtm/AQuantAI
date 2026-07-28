"""Pure deterministic contracts for the ordinary-user Industry Research flow.

This module owns no persistence, query, clock, network, AI, recommendation, or
candidate-state semantics. It only normalizes the complete commit-relevant
Owner Acceptance View body and calculates its canonical SHA-256 fingerprint.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping
from uuid import UUID

ACCEPTANCE_VIEW_SNAPSHOT_CONTRACT_VERSION = (
    "aquantai.industry-thesis-owner-acceptance-view-snapshot.v1"
)
SNAPSHOT_BODY_MISMATCH_CODE = "industry_research_e2e_snapshot_body_mismatch"

_REQUIRED_VIEW_KEYS = (
    "reviewed_session_revision_id",
    "expected_session_latest_revision_number",
    "reviewed_plan_fingerprint_sha256",
    "owner_context",
    "information_cutoff_date",
    "owner_acceptance_plan_version",
    "members",
    "candidate_pool_operation_contract",
    "output_metadata_defaults",
)


def _json_ready(value: Any) -> Any:
    """Normalize supported domain values without changing list order."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return _json_ready(value.value)
    if isinstance(value, Mapping):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    raise TypeError(f"unsupported acceptance snapshot value: {type(value).__name__}")


def canonical_acceptance_view_snapshot(view: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact commit-relevant, JSON-ready snapshot body."""

    missing = [key for key in _REQUIRED_VIEW_KEYS if key not in view]
    if missing:
        raise ValueError(
            "acceptance view is missing canonical snapshot fields: "
            + ", ".join(missing)
        )
    return {
        "snapshot_contract_version": ACCEPTANCE_VIEW_SNAPSHOT_CONTRACT_VERSION,
        **{key: _json_ready(view[key]) for key in _REQUIRED_VIEW_KEYS},
    }


def canonical_acceptance_view_snapshot_json(view: Mapping[str, Any]) -> str:
    """Serialize one snapshot using the frozen canonical JSON contract."""

    return json.dumps(
        canonical_acceptance_view_snapshot(view),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def acceptance_view_snapshot_content_sha256(view: Mapping[str, Any]) -> str:
    """Calculate the lowercase SHA-256 of the canonical UTF-8 snapshot body."""

    payload = canonical_acceptance_view_snapshot_json(view).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


__all__ = (
    "ACCEPTANCE_VIEW_SNAPSHOT_CONTRACT_VERSION",
    "SNAPSHOT_BODY_MISMATCH_CODE",
    "acceptance_view_snapshot_content_sha256",
    "canonical_acceptance_view_snapshot",
    "canonical_acceptance_view_snapshot_json",
)

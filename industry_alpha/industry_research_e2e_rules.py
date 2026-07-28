"""Pure deterministic contracts for the ordinary-user Industry Research flow.

This module owns no persistence, query, clock, network, AI, recommendation, or
candidate-state semantics.  It only normalizes the complete commit-relevant
Owner Acceptance View body and calculates its canonical SHA-256 fingerprint.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Mapping

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


def canonical_acceptance_view_snapshot(view: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact commit-relevant snapshot body.

    Object keys are later sorted by the JSON encoder.  List order is preserved
    exactly because ordered members and ordered operation options are part of the
    reviewed contract.  A deep copy prevents callers from mutating the
    authoritative view through the returned snapshot.
    """

    missing = [key for key in _REQUIRED_VIEW_KEYS if key not in view]
    if missing:
        raise ValueError(
            "acceptance view is missing canonical snapshot fields: "
            + ", ".join(missing)
        )
    return {
        "snapshot_contract_version": ACCEPTANCE_VIEW_SNAPSHOT_CONTRACT_VERSION,
        **{key: deepcopy(view[key]) for key in _REQUIRED_VIEW_KEYS},
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

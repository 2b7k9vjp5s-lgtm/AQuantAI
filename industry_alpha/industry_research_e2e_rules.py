"""Pure deterministic contracts for the ordinary-user Industry Research flow.

This module owns no persistence, query, clock, network, AI, recommendation, or
candidate-state semantics. It projects only the commit-relevant Owner Acceptance
View body and calculates its canonical SHA-256 fingerprint.
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
_OWNER_CONTEXT_KEYS = (
    "owner_context_contract_version",
    "research_case_id",
    "map_mode",
    "industry_map_id",
    "industry_map_revision_id",
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


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"acceptance snapshot {label} must be a mapping")
    return value


def _fields(value: Any, keys: tuple[str, ...], label: str) -> dict[str, Any]:
    source = _mapping(value, label)
    missing = [key for key in keys if key not in source]
    if missing:
        raise ValueError(
            f"acceptance snapshot {label} is missing fields: " + ", ".join(missing)
        )
    return {key: _json_ready(source[key]) for key in keys}


def _option_values(values: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"acceptance snapshot {label} must be a list")
    return [_fields(item, ("value",), label) for item in values]


def _authoring_contract(value: Any, label: str) -> dict[str, Any]:
    source = _mapping(value, label)
    required = (
        "legacy_beneficiary_kind_options",
        "assessment_status_options",
        "map_assertion_options",
        "claim_revision_options",
    )
    missing = [key for key in required if key not in source]
    if missing:
        raise ValueError(
            f"acceptance snapshot {label} is missing fields: " + ", ".join(missing)
        )
    return {
        "legacy_beneficiary_kind_options": _option_values(
            source["legacy_beneficiary_kind_options"],
            f"{label}.legacy_beneficiary_kind_options",
        ),
        "assessment_status_options": _option_values(
            source["assessment_status_options"],
            f"{label}.assessment_status_options",
        ),
        "map_assertion_options": [
            _fields(
                item,
                ("assertion_kind", "assertion_revision_id", "assertion_status"),
                f"{label}.map_assertion_options",
            )
            for item in source["map_assertion_options"]
        ],
        "claim_revision_options": [
            _fields(
                item,
                ("claim_revision_id", "claim_kind", "claim_status", "claim_key"),
                f"{label}.claim_revision_options",
            )
            for item in source["claim_revision_options"]
        ],
    }


def _semantic_options(values: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"acceptance snapshot {label} must be a list")
    return [
        _fields(
            item,
            ("profile_id", "profile_revision_id", "summary", "overall_status"),
            label,
        )
        for item in values
    ]


def _reuse_options(values: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"acceptance snapshot {label} must be a list")
    result = []
    for item in values:
        projected = _fields(
            item,
            (
                "beneficiary_id",
                "beneficiary_revision_id",
                "revision_number",
                "stock_basic_record_id",
                "legacy_beneficiary_kind",
                "assessment_status",
                "rationale_summary",
                "semantic_reuse_options",
            ),
            label,
        )
        projected["semantic_reuse_options"] = _semantic_options(
            _mapping(item, label)["semantic_reuse_options"],
            f"{label}.semantic_reuse_options",
        )
        result.append(projected)
    return result


def _append_options(values: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(values, (list, tuple)):
        raise ValueError(f"acceptance snapshot {label} must be a list")
    return [
        _fields(
            item,
            (
                "beneficiary_id",
                "expected_latest_revision_id",
                "revision_number",
                "stock_basic_record_id",
                "source",
                "stock_code",
                "current_legacy_beneficiary_kind",
                "current_assessment_status",
                "current_rationale_summary",
            ),
            label,
        )
        for item in values
    ]


def _create_contract(value: Any, label: str) -> dict[str, Any]:
    source = _mapping(value, label)
    result = _fields(
        source,
        ("available", "stock_basic_record_id", "source", "stock_code", "context_locked"),
        label,
    )
    result.update(_authoring_contract(source, label))
    return result


def _member(value: Any, label: str) -> dict[str, Any]:
    source = _mapping(value, label)
    required = (
        "sequence",
        "reviewed_candidate_revision_id",
        "stage1_reuse_options",
        "stage1_append_options",
        "stage1_create_contract",
        "stage1_authoring_contract",
    )
    missing = [key for key in required if key not in source]
    if missing:
        raise ValueError(
            f"acceptance snapshot {label} is missing fields: " + ", ".join(missing)
        )
    return {
        "sequence": _json_ready(source["sequence"]),
        "reviewed_candidate_revision_id": _json_ready(
            source["reviewed_candidate_revision_id"]
        ),
        "stage1_reuse_options": _reuse_options(
            source["stage1_reuse_options"], f"{label}.stage1_reuse_options"
        ),
        "stage1_append_options": _append_options(
            source["stage1_append_options"], f"{label}.stage1_append_options"
        ),
        "stage1_create_contract": _create_contract(
            source["stage1_create_contract"], f"{label}.stage1_create_contract"
        ),
        "stage1_authoring_contract": _authoring_contract(
            source["stage1_authoring_contract"], f"{label}.stage1_authoring_contract"
        ),
    }


def _pool_contract(value: Any) -> dict[str, Any]:
    source = _mapping(value, "candidate_pool_operation_contract")
    required = ("create_contract", "append_options", "reuse_options", "zero_supported_contract")
    missing = [key for key in required if key not in source]
    if missing:
        raise ValueError(
            "acceptance snapshot candidate_pool_operation_contract is missing fields: "
            + ", ".join(missing)
        )
    return {
        "create_contract": _fields(
            source["create_contract"],
            ("mode", "pool_key", "title_default", "scope_default"),
            "candidate_pool_operation_contract.create_contract",
        ),
        "append_options": [
            _fields(
                item,
                (
                    "candidate_pool_id",
                    "expected_latest_revision_id",
                    "revision_number",
                    "title",
                    "scope",
                ),
                "candidate_pool_operation_contract.append_options",
            )
            for item in source["append_options"]
        ],
        "reuse_options": [
            _fields(
                item,
                (
                    "candidate_pool_id",
                    "candidate_pool_revision_id",
                    "revision_number",
                    "title",
                    "scope",
                    "beneficiary_revision_ids",
                ),
                "candidate_pool_operation_contract.reuse_options",
            )
            for item in source["reuse_options"]
        ],
        "zero_supported_contract": _fields(
            source["zero_supported_contract"],
            ("mode",),
            "candidate_pool_operation_contract.zero_supported_contract",
        ),
    }


def canonical_acceptance_view_snapshot(view: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact commit-relevant, JSON-ready snapshot body.

    Presentation-only labels, localized copy, blocking messages, exchange/industry
    display metadata, and technical disclosures are intentionally excluded. The
    exact ordered authoring options and immutable identities remain protected.
    """

    missing = [key for key in _REQUIRED_VIEW_KEYS if key not in view]
    if missing:
        raise ValueError(
            "acceptance view is missing canonical snapshot fields: "
            + ", ".join(missing)
        )
    members = view["members"]
    if not isinstance(members, (list, tuple)):
        raise ValueError("acceptance snapshot members must be a list")
    return {
        "snapshot_contract_version": ACCEPTANCE_VIEW_SNAPSHOT_CONTRACT_VERSION,
        "reviewed_session_revision_id": _json_ready(view["reviewed_session_revision_id"]),
        "expected_session_latest_revision_number": _json_ready(
            view["expected_session_latest_revision_number"]
        ),
        "reviewed_plan_fingerprint_sha256": _json_ready(
            view["reviewed_plan_fingerprint_sha256"]
        ),
        "owner_context": _fields(view["owner_context"], _OWNER_CONTEXT_KEYS, "owner_context"),
        "information_cutoff_date": _json_ready(view["information_cutoff_date"]),
        "owner_acceptance_plan_version": _json_ready(view["owner_acceptance_plan_version"]),
        "members": [_member(item, f"members[{index}]") for index, item in enumerate(members)],
        "candidate_pool_operation_contract": _pool_contract(
            view["candidate_pool_operation_contract"]
        ),
        "output_metadata_defaults": _fields(
            view["output_metadata_defaults"],
            ("output_title", "output_scope"),
            "output_metadata_defaults",
        ),
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

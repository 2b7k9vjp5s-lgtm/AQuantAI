"""Deterministic, zero-I/O manifest projection for Guarded AI v1."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from industry_alpha.guarded_ai_contracts import (
    GuardedAIInputTooLargeError,
    GuardedAIManifest,
    MANIFEST_SCHEMA_VERSION,
    MAX_CANONICAL_INPUT_CHARS,
    PROJECTION_VERSION,
)

_SECTION_KEYS = (
    "identity",
    "frozen_stage1",
    "company_research",
    "hypotheses",
    "expectations",
    "valuation_observations",
    "catalysts",
    "risks",
    "industry_judgments",
    "company_judgments",
    "evidence_summary",
    "notices",
)
_EXCLUDED_KEYS = frozenset({"detail_routes", "detail_path"})


class GuardedAIManifestError(ValueError):
    """The accepted workspace cannot be projected safely."""


def build_guarded_ai_manifest(
    workspace: Mapping[str, Any],
    *,
    company_research_id: str,
    as_of_cutoff: str | None,
) -> GuardedAIManifest:
    """Build a stable manifest without database or network access."""

    identity = workspace.get("identity")
    if not isinstance(identity, Mapping):
        raise GuardedAIManifestError("workspace identity is missing")
    actual_id = identity.get("company_research_id")
    if actual_id != company_research_id:
        raise GuardedAIManifestError("workspace identity does not match the request")

    workspace_cutoff = workspace.get("as_of_cutoff")
    if workspace_cutoff != as_of_cutoff:
        raise GuardedAIManifestError("workspace cutoff does not match the request")

    item_ids: set[str] = set()
    sections: dict[str, Any] = {}
    included: list[str] = []
    unavailable: list[str] = []

    for section_name in _SECTION_KEYS:
        raw = workspace.get(section_name)
        if _is_unavailable(raw):
            unavailable.append(section_name)
        else:
            included.append(section_name)
        sections[section_name] = _project_value(
            raw,
            path=("sections", section_name),
            item_ids=item_ids,
        )

    content = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "projection_version": PROJECTION_VERSION,
        "company_research_id": company_research_id,
        "as_of_cutoff": as_of_cutoff,
        "sections": sections,
        "included_sections": included,
        "unavailable_sections": unavailable,
    }
    canonical_json = json.dumps(
        content,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    character_count = len(canonical_json)
    if character_count > MAX_CANONICAL_INPUT_CHARS:
        raise GuardedAIInputTooLargeError()
    fingerprint = "sha256:" + hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    return GuardedAIManifest(
        content=content,
        canonical_json=canonical_json,
        fingerprint=fingerprint,
        manifest_item_ids=frozenset(item_ids),
        input_character_count=character_count,
        included_sections=tuple(included),
        unavailable_sections=tuple(unavailable),
    )


def _project_value(value: Any, *, path: tuple[str, ...], item_ids: set[str]) -> Any:
    if isinstance(value, Mapping):
        projected: dict[str, Any] = {}
        for key in sorted(value):
            if not isinstance(key, str):
                raise GuardedAIManifestError("workspace object keys must be strings")
            if key in _EXCLUDED_KEYS:
                continue
            projected[key] = _project_value(
                value[key],
                path=(*path, key),
                item_ids=item_ids,
            )
        return projected
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [
            _project_value(item, path=(*path, str(index)), item_ids=item_ids)
            for index, item in enumerate(value)
        ]
    if isinstance(value, (bytes, bytearray)):
        raise GuardedAIManifestError("binary workspace content is not allowed")
    if value is not None and not isinstance(value, (str, int, float, bool)):
        raise GuardedAIManifestError("workspace contains a non-JSON scalar")
    item_id = _item_id(path)
    if item_id in item_ids:
        raise GuardedAIManifestError("manifest item ID collision")
    item_ids.add(item_id)
    return {"manifest_item_id": item_id, "value": value}


def _item_id(path: tuple[str, ...]) -> str:
    canonical_path = "/".join(_escape_path_part(part) for part in path)
    digest = hashlib.sha256(canonical_path.encode("utf-8")).hexdigest()[:20]
    return f"manifest:{digest}"


def _escape_path_part(part: str) -> str:
    return part.replace("~", "~0").replace("/", "~1")


def _is_unavailable(value: Any) -> bool:
    return value is None or value == {} or value == [] or value == ()

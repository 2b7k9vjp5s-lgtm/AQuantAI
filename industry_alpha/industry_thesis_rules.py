"""Deterministic validation and fingerprint rules for offline industry-thesis orchestration."""

from __future__ import annotations

from datetime import date, datetime, timezone
from hashlib import sha256
import json
from typing import Any
from uuid import UUID

from industry_alpha.industry_thesis_models import (
    ANALYSIS_HORIZONS,
    CANDIDATE_SOURCE_KINDS,
    COVERAGE_STATES,
    DRIVER_TYPES,
    IDENTITY_STATES,
    PROPOSAL_CONFIDENCE_STATES,
    PROPOSED_EXPOSURE_TYPES,
    REVIEW_STATES,
    WORKFLOW_STATES,
)

BUILDER_VERSION = "aquantai.industry-thesis-local-candidate-builder.v1"
ACTIVE_SOURCE_KINDS = (
    "accepted_local_mapping",
    "existing_industry_map_revision",
    "user_seed",
)
SOURCE_PRECEDENCE = {kind: index for index, kind in enumerate(CANDIDATE_SOURCE_KINDS)}
MAX_JSON_BYTES = 65_536
MAX_JSON_DEPTH = 8
MAX_JSON_ITEMS = 2_000


class IndustryThesisError(RuntimeError):
    """Stable, credential-safe public error."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class IndustryThesisNotFound(IndustryThesisError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def stored_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_uuid(value: Any, field: str, *, optional: bool = False) -> UUID | None:
    if value is None and optional:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            f"{field} must be an explicit UUID",
        ) from exc


def parse_integer(value: Any, field: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            f"{field} must be an integer greater than or equal to {minimum}",
        )
    return value


def parse_date(value: Any, field: str, *, optional: bool = False) -> date | None:
    if value is None and optional:
        return None
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            f"{field} must be YYYY-MM-DD",
        ) from exc


def bounded_text(
    value: Any,
    field: str,
    limit: int,
    *,
    optional: bool = False,
) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str):
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            f"{field} must be bounded text",
        )
    result = value.strip()
    if not result or len(result) > limit:
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            f"{field} must be non-empty text no longer than {limit} characters",
        )
    return result


def enum_text(value: Any, field: str, allowed: tuple[str, ...]) -> str:
    result = bounded_text(value, field, 96)
    if result not in allowed:
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            f"{field} has an unsupported value",
        )
    return result


def require_keys(raw: Any, allowed: set[str], required: set[str], *, field: str = "input") -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            f"{field} must be a JSON object",
        )
    unknown = sorted(set(raw) - allowed)
    missing = sorted(required - set(raw))
    if unknown:
        raise IndustryThesisError(
            "industry_thesis_unknown_field",
            f"{field} has unknown fields: {', '.join(unknown)}",
        )
    if missing:
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            f"{field} is missing fields: {', '.join(missing)}",
        )
    return raw


def _strict_json_value(value: Any, *, depth: int, counter: list[int]) -> Any:
    if depth > MAX_JSON_DEPTH:
        raise IndustryThesisError(
            "industry_thesis_json_invalid",
            "strict JSON exceeds the maximum nesting depth",
        )
    counter[0] += 1
    if counter[0] > MAX_JSON_ITEMS:
        raise IndustryThesisError(
            "industry_thesis_json_invalid",
            "strict JSON exceeds the maximum item count",
        )
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        raise IndustryThesisError(
            "industry_thesis_json_invalid",
            "strict JSON forbids binary floating-point values",
        )
    if isinstance(value, list):
        return [
            _strict_json_value(item, depth=depth + 1, counter=counter)
            for item in value
        ]
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise IndustryThesisError(
                "industry_thesis_json_invalid",
                "strict JSON object keys must be strings",
            )
        return {
            key: _strict_json_value(value[key], depth=depth + 1, counter=counter)
            for key in sorted(value)
        }
    raise IndustryThesisError(
        "industry_thesis_json_invalid",
        "strict JSON supports only null, strings, booleans, integers, arrays and objects",
    )


def canonical_json_text(value: Any, field: str) -> str:
    normalized = _strict_json_value(value, depth=0, counter=[0])
    try:
        text = json.dumps(
            normalized,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise IndustryThesisError(
            "industry_thesis_json_invalid",
            f"{field} is not strict JSON",
        ) from exc
    if len(text.encode("utf-8")) > MAX_JSON_BYTES:
        raise IndustryThesisError(
            "industry_thesis_json_invalid",
            f"{field} exceeds the 64 KiB limit",
        )
    return text


def json_value(text: str, field: str) -> Any:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise IndustryThesisError(
            "industry_thesis_graph_incomplete",
            f"stored {field} is not valid strict JSON",
        ) from exc
    if canonical_json_text(value, field) != text:
        raise IndustryThesisError(
            "industry_thesis_graph_incomplete",
            f"stored {field} is not canonical strict JSON",
        )
    return value


def fingerprint(value: Any) -> str:
    return sha256(canonical_json_text(value, "fingerprint payload").encode("utf-8")).hexdigest()


def parse_market_scope(value: Any) -> tuple[list[dict[str, Any]], str]:
    if not isinstance(value, list) or not value:
        raise IndustryThesisError(
            "industry_thesis_market_scope_required",
            "market_scope must be an explicit non-empty list",
        )
    scopes: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        require_keys(
            item,
            {
                "market_namespace",
                "exchange_namespace",
                "security_type",
                "include_status",
                "listed_instrument_ids",
            },
            {"market_namespace", "security_type", "include_status"},
            field=f"market_scope[{index}]",
        )
        listed_ids_raw = item.get("listed_instrument_ids", [])
        if not isinstance(listed_ids_raw, list):
            raise IndustryThesisError(
                "industry_thesis_input_invalid",
                f"market_scope[{index}].listed_instrument_ids must be a list",
            )
        listed_ids = sorted(
            {
                str(parse_uuid(raw_id, f"market_scope[{index}].listed_instrument_ids"))
                for raw_id in listed_ids_raw
            }
        )
        scope = {
            "market_namespace": bounded_text(
                item["market_namespace"], f"market_scope[{index}].market_namespace", 64
            ),
            "exchange_namespace": bounded_text(
                item.get("exchange_namespace"),
                f"market_scope[{index}].exchange_namespace",
                64,
                optional=True,
            ),
            "security_type": bounded_text(
                item["security_type"], f"market_scope[{index}].security_type", 64
            ),
            "include_status": bounded_text(
                item["include_status"], f"market_scope[{index}].include_status", 64
            ),
            "listed_instrument_ids": listed_ids,
        }
        scopes.append(scope)
    scopes.sort(
        key=lambda item: (
            item["market_namespace"],
            item["exchange_namespace"] or "",
            item["security_type"],
            item["include_status"],
            tuple(item["listed_instrument_ids"]),
        )
    )
    text = canonical_json_text(scopes, "market_scope")
    return scopes, text


_SESSION_FIELDS = {
    "thesis_text_original",
    "thesis_title_reviewed",
    "driver_type",
    "analysis_horizon_kind",
    "analysis_start_date",
    "analysis_end_date",
    "market_scope",
    "chain_boundary",
    "exclusions",
    "seed_companies",
    "seed_products",
    "seed_technologies",
    "seed_bottlenecks",
    "draft_graph",
    "coverage_state",
    "workflow_state",
    "information_cutoff_date",
    "revision_note",
}
_SESSION_REQUIRED = _SESSION_FIELDS - {
    "thesis_title_reviewed",
    "analysis_start_date",
    "analysis_end_date",
}


def normalize_session_payload(raw: dict[str, Any]) -> dict[str, Any]:
    require_keys(raw, _SESSION_FIELDS, _SESSION_REQUIRED)
    horizon = enum_text(raw["analysis_horizon_kind"], "analysis_horizon_kind", ANALYSIS_HORIZONS)
    start = parse_date(raw.get("analysis_start_date"), "analysis_start_date", optional=True)
    end = parse_date(raw.get("analysis_end_date"), "analysis_end_date", optional=True)
    if horizon == "custom" and (start is None or end is None):
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "custom analysis horizon requires start and end dates",
        )
    if (start is None) != (end is None) or (start is not None and end is not None and end < start):
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "analysis dates must be supplied as an ordered pair",
        )
    _, market_scope_json = parse_market_scope(raw["market_scope"])
    data = {
        "thesis_text_original": bounded_text(raw["thesis_text_original"], "thesis_text_original", 4000),
        "thesis_title_reviewed": bounded_text(
            raw.get("thesis_title_reviewed"), "thesis_title_reviewed", 300, optional=True
        ),
        "driver_type": enum_text(raw["driver_type"], "driver_type", DRIVER_TYPES),
        "analysis_horizon_kind": horizon,
        "analysis_start_date": start,
        "analysis_end_date": end,
        "market_scope_json": market_scope_json,
        "chain_boundary_json": canonical_json_text(raw["chain_boundary"], "chain_boundary"),
        "exclusions_json": canonical_json_text(raw["exclusions"], "exclusions"),
        "seed_companies_json": canonical_json_text(raw["seed_companies"], "seed_companies"),
        "seed_products_json": canonical_json_text(raw["seed_products"], "seed_products"),
        "seed_technologies_json": canonical_json_text(raw["seed_technologies"], "seed_technologies"),
        "seed_bottlenecks_json": canonical_json_text(raw["seed_bottlenecks"], "seed_bottlenecks"),
        "draft_graph_json": canonical_json_text(raw["draft_graph"], "draft_graph"),
        "coverage_state": enum_text(raw["coverage_state"], "coverage_state", COVERAGE_STATES),
        "workflow_state": enum_text(raw["workflow_state"], "workflow_state", WORKFLOW_STATES),
        "information_cutoff_date": parse_date(
            raw["information_cutoff_date"], "information_cutoff_date"
        ),
        "revision_note": bounded_text(raw["revision_note"], "revision_note", 1000),
    }
    fingerprint_payload = {
        "thesis_text_original": data["thesis_text_original"],
        "thesis_title_reviewed": data["thesis_title_reviewed"],
        "driver_type": data["driver_type"],
        "analysis_horizon_kind": data["analysis_horizon_kind"],
        "analysis_start_date": None if start is None else start.isoformat(),
        "analysis_end_date": None if end is None else end.isoformat(),
        "market_scope": json_value(data["market_scope_json"], "market_scope"),
        "chain_boundary": json_value(data["chain_boundary_json"], "chain_boundary"),
        "exclusions": json_value(data["exclusions_json"], "exclusions"),
        "seed_companies": json_value(data["seed_companies_json"], "seed_companies"),
        "seed_products": json_value(data["seed_products_json"], "seed_products"),
        "seed_technologies": json_value(data["seed_technologies_json"], "seed_technologies"),
        "seed_bottlenecks": json_value(data["seed_bottlenecks_json"], "seed_bottlenecks"),
        "draft_graph": json_value(data["draft_graph_json"], "draft_graph"),
        "coverage_state": data["coverage_state"],
        "workflow_state": data["workflow_state"],
        "information_cutoff_date": data["information_cutoff_date"].isoformat(),
    }
    data["input_fingerprint_sha256"] = fingerprint(fingerprint_payload)
    return data


def session_revision_to_input(revision: Any) -> dict[str, Any]:
    return {
        "thesis_text_original": revision.thesis_text_original,
        "thesis_title_reviewed": revision.thesis_title_reviewed,
        "driver_type": revision.driver_type,
        "analysis_horizon_kind": revision.analysis_horizon_kind,
        "analysis_start_date": None if revision.analysis_start_date is None else revision.analysis_start_date.isoformat(),
        "analysis_end_date": None if revision.analysis_end_date is None else revision.analysis_end_date.isoformat(),
        "market_scope": json_value(revision.market_scope_json, "market_scope"),
        "chain_boundary": json_value(revision.chain_boundary_json, "chain_boundary"),
        "exclusions": json_value(revision.exclusions_json, "exclusions"),
        "seed_companies": json_value(revision.seed_companies_json, "seed_companies"),
        "seed_products": json_value(revision.seed_products_json, "seed_products"),
        "seed_technologies": json_value(revision.seed_technologies_json, "seed_technologies"),
        "seed_bottlenecks": json_value(revision.seed_bottlenecks_json, "seed_bottlenecks"),
        "draft_graph": json_value(revision.draft_graph_json, "draft_graph"),
        "coverage_state": revision.coverage_state,
        "workflow_state": revision.workflow_state,
        "information_cutoff_date": revision.information_cutoff_date.isoformat(),
        "revision_note": revision.revision_note,
    }


def apply_session_patch(revision: Any, changes: Any, revision_note: Any) -> dict[str, Any]:
    if not isinstance(changes, dict) or not changes:
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "changes must be a non-empty JSON object",
        )
    mutable = _SESSION_FIELDS - {"revision_note"}
    unknown = sorted(set(changes) - mutable)
    if unknown:
        raise IndustryThesisError(
            "industry_thesis_unknown_field",
            f"changes has unknown fields: {', '.join(unknown)}",
        )
    payload = session_revision_to_input(revision)
    payload.update(changes)
    payload["revision_note"] = revision_note
    return normalize_session_payload(payload)


def normalize_candidate_build(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "session_revision_id",
        "expected_session_latest_revision_number",
        "builder_version",
        "allowed_source_kinds",
        "proposals",
    }
    require_keys(raw, allowed, allowed)
    builder_version = bounded_text(raw["builder_version"], "builder_version", 128)
    if builder_version != BUILDER_VERSION:
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "unsupported deterministic candidate builder version",
        )
    source_kinds = raw["allowed_source_kinds"]
    if not isinstance(source_kinds, list) or not source_kinds:
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "allowed_source_kinds must be a non-empty list",
        )
    normalized_source_kinds = tuple(
        sorted(
            {
                enum_text(value, "allowed_source_kinds", ACTIVE_SOURCE_KINDS)
                for value in source_kinds
            },
            key=lambda value: SOURCE_PRECEDENCE[value],
        )
    )
    proposals = raw["proposals"]
    if not isinstance(proposals, list):
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "proposals must be an explicit list",
        )
    normalized = [normalize_candidate_proposal(item, index=index) for index, item in enumerate(proposals)]
    for item in normalized:
        if item["source_kind"] not in normalized_source_kinds:
            raise IndustryThesisError(
                "industry_thesis_input_invalid",
                "proposal source kind was not explicitly allowed",
            )
    keys = [item["candidate_key"] for item in normalized]
    if len(keys) != len(set(keys)):
        raise IndustryThesisError(
            "industry_thesis_duplicate_source",
            "one build request cannot contain the same exact candidate source twice",
        )
    normalized.sort(
        key=lambda item: (
            SOURCE_PRECEDENCE[item["source_kind"]],
            item["candidate_key"],
            item["company_label_original"],
        )
    )
    return {
        "session_revision_id": parse_uuid(raw["session_revision_id"], "session_revision_id"),
        "expected_session_latest_revision_number": parse_integer(
            raw["expected_session_latest_revision_number"],
            "expected_session_latest_revision_number",
            minimum=1,
        ),
        "builder_version": builder_version,
        "allowed_source_kinds": normalized_source_kinds,
        "proposals": normalized,
    }


def normalize_candidate_proposal(raw: Any, *, index: int) -> dict[str, Any]:
    allowed = {
        "source_kind",
        "source_reference",
        "proposed_stock_basic_record_id",
        "proposed_listed_instrument_id",
        "company_label_original",
        "product_or_service_fit",
        "industry_position",
        "benefit_path_text",
        "proposed_exposure_type",
        "proposal_confidence",
        "identity_state",
        "review_state",
        "rationale",
        "uncertainty",
        "manifest_fingerprint_sha256",
        "expected_latest_revision_number",
    }
    required = allowed - {
        "proposed_stock_basic_record_id",
        "proposed_listed_instrument_id",
        "product_or_service_fit",
        "industry_position",
        "manifest_fingerprint_sha256",
        "expected_latest_revision_number",
    }
    require_keys(raw, allowed, required, field=f"proposals[{index}]")
    source_kind = enum_text(raw["source_kind"], "source_kind", ACTIVE_SOURCE_KINDS)
    source_reference_json = canonical_json_text(raw["source_reference"], "source_reference")
    stock_id = None
    if raw.get("proposed_stock_basic_record_id") is not None:
        stock_id = parse_integer(
            raw["proposed_stock_basic_record_id"],
            "proposed_stock_basic_record_id",
            minimum=1,
        )
    instrument_id = parse_uuid(
        raw.get("proposed_listed_instrument_id"),
        "proposed_listed_instrument_id",
        optional=True,
    )
    identity_state = enum_text(raw["identity_state"], "identity_state", IDENTITY_STATES)
    if identity_state == "exact_accepted_identity" and stock_id is None and instrument_id is None:
        raise IndustryThesisError(
            "industry_thesis_identity_invalid",
            "exact accepted identity requires an explicit persisted identity ID",
        )
    if identity_state != "exact_accepted_identity" and (stock_id is not None or instrument_id is not None):
        raise IndustryThesisError(
            "industry_thesis_identity_invalid",
            "non-exact identity state cannot carry an accepted identity ID",
        )
    manifest = bounded_text(
        raw.get("manifest_fingerprint_sha256"),
        "manifest_fingerprint_sha256",
        64,
        optional=True,
    )
    if manifest is not None and (len(manifest) != 64 or any(char not in "0123456789abcdef" for char in manifest)):
        raise IndustryThesisError(
            "industry_thesis_input_invalid",
            "manifest_fingerprint_sha256 must be lowercase SHA-256 text",
        )
    source_reference = json_value(source_reference_json, "source_reference")
    candidate_key = fingerprint(
        {
            "source_kind": source_kind,
            "source_reference": source_reference,
        }
    )
    return {
        "candidate_key": candidate_key,
        "source_kind": source_kind,
        "source_reference_json": source_reference_json,
        "proposed_stock_basic_record_id": stock_id,
        "proposed_listed_instrument_id": instrument_id,
        "company_label_original": bounded_text(
            raw["company_label_original"], "company_label_original", 300
        ),
        "product_or_service_fit": bounded_text(
            raw.get("product_or_service_fit"),
            "product_or_service_fit",
            2000,
            optional=True,
        ),
        "industry_position": bounded_text(
            raw.get("industry_position"), "industry_position", 1000, optional=True
        ),
        "benefit_path_text": bounded_text(raw["benefit_path_text"], "benefit_path_text", 4000),
        "proposed_exposure_type": enum_text(
            raw["proposed_exposure_type"],
            "proposed_exposure_type",
            PROPOSED_EXPOSURE_TYPES,
        ),
        "proposal_confidence": enum_text(
            raw["proposal_confidence"],
            "proposal_confidence",
            PROPOSAL_CONFIDENCE_STATES,
        ),
        "identity_state": identity_state,
        "review_state": enum_text(raw["review_state"], "review_state", REVIEW_STATES),
        "rationale_json": canonical_json_text(raw["rationale"], "rationale"),
        "uncertainty_json": canonical_json_text(raw["uncertainty"], "uncertainty"),
        "manifest_fingerprint_sha256": manifest,
        "expected_latest_revision_number": (
            None
            if raw.get("expected_latest_revision_number") is None
            else parse_integer(
                raw["expected_latest_revision_number"],
                "expected_latest_revision_number",
                minimum=0,
            )
        ),
    }

"""Deterministic validation and fingerprint rules for local documents."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from industry_alpha.document_import_contracts import DocumentImportError


MAX_INPUT_BYTES = 52_428_800
MAX_PAGES = 300
MAX_PAGE_CHARACTERS = 100_000
MAX_DOCUMENT_CHARACTERS = 5_000_000
MAX_DECODED_PAGE_BYTES = 52_428_800
MAX_DECODED_DOCUMENT_BYTES = 209_715_200
MAX_WORKER_MEMORY_BYTES = 536_870_912
MAX_CANDIDATES = 500
MAX_ACCEPTED_CANDIDATES = 200
MAX_QUEUE_PAGE_SIZE = 50

CANDIDATE_KINDS = frozenset({"document_identity", "company_identity", "fact", "event"})
REVIEW_STATES = frozenset({"draft", "deferred", "rejected"})
DECISIONS = frozenset({"selected", "rejected", "deferred"})
DOCUMENT_KINDS = frozenset(
    {
        "filing",
        "announcement",
        "regulatory",
        "statistics",
        "company_report",
        "industry_report",
        "other_official",
    }
)


def sha256_hex(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise DocumentImportError("naive_timestamp", "timestamps must be timezone-aware")
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float):
        raise DocumentImportError("float_not_allowed", "canonical contracts prohibit floats")
    if isinstance(value, dict):
        return {str(key): canonical_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [canonical_value(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def fingerprint(value: Any) -> str:
    return sha256_hex(canonical_json(value).encode("utf-8"))


def utc_timestamp(value: datetime | None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None or result.utcoffset() is None:
        raise DocumentImportError("naive_timestamp", "recorded_at_utc must include UTC offset")
    return result.astimezone(timezone.utc)


def bounded_text(value: str, field: str, maximum: int, *, optional: bool = False) -> str | None:
    if not isinstance(value, str):
        raise DocumentImportError("invalid_text", f"{field} must be text")
    result = value.strip()
    if not result:
        if optional:
            return None
        raise DocumentImportError("missing_text", f"{field} is required")
    if len(result) > maximum:
        raise DocumentImportError("text_too_large", f"{field} exceeds {maximum} characters")
    return result


def validated_basename(value: str) -> str:
    if not isinstance(value, str):
        raise DocumentImportError("invalid_filename", "filename must be text")
    if not value or not value.strip():
        raise DocumentImportError("invalid_filename", "filename is required")
    if len(value) > 255:
        raise DocumentImportError("invalid_filename", "filename exceeds 255 characters")
    if any(char in value for char in ("/", "\\", "\x00")) or any(
        ord(char) < 32 or ord(char) == 127 for char in value
    ):
        raise DocumentImportError("invalid_filename", "filename must be a safe basename")
    return value


def validate_sha256(value: str, field: str) -> str:
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise DocumentImportError("invalid_fingerprint", f"{field} must be lowercase SHA-256")
    return value


def validate_document_identity_payload(payload: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "identity_namespace",
        "identity_key",
        "document_title",
        "publisher_or_author",
        "document_date",
        "document_kind",
        "revision_label",
        "supersedes_document_content_id",
    }
    if set(payload) - expected:
        raise DocumentImportError("candidate_payload_unknown_field")
    if payload.get("identity_namespace") != "user_defined_document":
        raise DocumentImportError("invalid_document_identity_namespace")
    try:
        document_date = date.fromisoformat(str(payload.get("document_date", "")))
    except ValueError as exc:
        raise DocumentImportError("invalid_document_date") from exc
    result = {
        "identity_namespace": "user_defined_document",
        "identity_key": bounded_text(str(payload.get("identity_key", "")), "identity_key", 200),
        "document_title": bounded_text(str(payload.get("document_title", "")), "document_title", 500),
        "publisher_or_author": bounded_text(
            str(payload.get("publisher_or_author", "")), "publisher_or_author", 300
        ),
        "document_date": document_date.isoformat(),
        "document_kind": str(payload.get("document_kind", "")),
        "revision_label": None,
        "supersedes_document_content_id": None,
    }
    if result["document_kind"] not in DOCUMENT_KINDS:
        raise DocumentImportError("invalid_document_kind")
    if payload.get("revision_label") is not None:
        result["revision_label"] = bounded_text(
            str(payload["revision_label"]), "revision_label", 200, optional=True
        )
    if payload.get("supersedes_document_content_id") is not None:
        try:
            result["supersedes_document_content_id"] = str(
                UUID(str(payload["supersedes_document_content_id"]))
            )
        except ValueError as exc:
            raise DocumentImportError("invalid_superseded_content_id") from exc
    return result


def validate_company_identity_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if set(payload) - {"subject_kind", "listed_instrument_id", "display_label"}:
        raise DocumentImportError("candidate_payload_unknown_field")
    kind = str(payload.get("subject_kind", ""))
    if kind not in {"listed_instrument", "not_company_specific"}:
        raise DocumentImportError("invalid_subject_kind")
    instrument = payload.get("listed_instrument_id")
    if kind == "listed_instrument" and instrument is None:
        raise DocumentImportError("listed_instrument_required")
    if kind == "not_company_specific" and instrument is not None:
        raise DocumentImportError("listed_instrument_forbidden")
    try:
        instrument_id = str(UUID(str(instrument))) if instrument else None
    except ValueError as exc:
        raise DocumentImportError("invalid_listed_instrument_id") from exc
    return {
        "subject_kind": kind,
        "listed_instrument_id": instrument_id,
        "display_label": bounded_text(
            str(payload.get("display_label", kind)), "display_label", 300
        ),
    }

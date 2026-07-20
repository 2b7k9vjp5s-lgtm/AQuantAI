"""Deterministic request, cursor, and projection logic for Evidence Intelligence."""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable
from uuid import UUID

from industry_alpha.evidence_intelligence_contracts import (
    EvidenceIntelligenceFeedContract,
)
from industry_alpha.evidence_intelligence_repository import (
    EVENT_TYPES,
    EVENT_TYPE_ORDER,
    EvidenceIntelligenceDataError,
    EvidenceIntelligenceRepository,
    EvidenceIntelligenceRow,
    FeedCursorPosition,
)
from industry_alpha.stage2_query_values import date_text, stored_utc, timestamp_text, uuid_text

DEFAULT_WINDOW = timedelta(days=7)
MAX_WINDOW = timedelta(days=30)
DEFAULT_LIMIT = 50
MAX_LIMIT = 100
MAX_CURSOR_LENGTH = 1024
CURSOR_VERSION = 1

FEED_NOTICES: dict[str, Any] = {
    "read_only": True,
    "research_only": True,
    "not_investment_advice": True,
    "no_scores_rankings_or_recommendations": True,
    "no_hidden_network_requests": True,
    "description": (
        "This feed reports accepted evidence and research revision chronology only. "
        "Recency and activity do not indicate investment attractiveness."
    ),
}


class EvidenceIntelligenceValidationError(ValueError):
    """A feed request or cursor violates the approved deterministic contract."""


@dataclass(frozen=True)
class EvidenceIntelligenceRequest:
    evaluated_at_utc: datetime
    as_of_cutoff: date | None
    recorded_from: datetime
    recorded_to: datetime
    event_type: str | None
    limit: int
    cursor: FeedCursorPosition | None


class EvidenceIntelligenceQueryService:
    def __init__(self, repository: EvidenceIntelligenceRepository) -> None:
        self._repository = repository

    def build_feed(
        self, request: EvidenceIntelligenceRequest
    ) -> EvidenceIntelligenceFeedContract:
        rows = list(
            self._repository.list_events(
                recorded_from=request.recorded_from,
                recorded_to=request.recorded_to,
                as_of_cutoff=request.as_of_cutoff,
                event_type=request.event_type,
                cursor=request.cursor,
                per_source_limit=request.limit + 1,
            )
        )
        _sort_rows(rows)
        has_more = len(rows) > request.limit
        visible_rows = rows[: request.limit]
        next_cursor = (
            encode_cursor(_cursor_from_row(visible_rows[-1]))
            if has_more and visible_rows
            else None
        )
        return EvidenceIntelligenceFeedContract(
            evaluated_at_utc=timestamp_text(request.evaluated_at_utc),
            as_of_cutoff=date_text(request.as_of_cutoff),
            recorded_from=timestamp_text(request.recorded_from),
            recorded_to=timestamp_text(request.recorded_to),
            event_type=request.event_type,
            limit=request.limit,
            events=tuple(_event_payload(row) for row in visible_rows),
            next_cursor=next_cursor,
            notices=dict(FEED_NOTICES),
        )


def resolve_feed_request(
    *,
    as_of_cutoff: date | None = None,
    recorded_from: datetime | None = None,
    recorded_to: datetime | None = None,
    event_type: str | None = None,
    limit: int = DEFAULT_LIMIT,
    cursor: str | None = None,
    evaluated_at_utc: datetime | None = None,
    now_provider: Callable[[], datetime] | None = None,
) -> EvidenceIntelligenceRequest:
    if evaluated_at_utc is not None and now_provider is not None:
        raise EvidenceIntelligenceValidationError(
            "evaluated_at_utc and now_provider cannot both be supplied."
        )
    raw_evaluated_at = (
        evaluated_at_utc
        if evaluated_at_utc is not None
        else (now_provider or _utc_now)()
    )
    evaluated = _aware_utc(raw_evaluated_at, "evaluated_at_utc")
    resolved_to = (
        _aware_utc(recorded_to, "recorded_to")
        if recorded_to is not None
        else evaluated
    )
    resolved_from = (
        _aware_utc(recorded_from, "recorded_from")
        if recorded_from is not None
        else resolved_to - DEFAULT_WINDOW
    )
    if resolved_from >= resolved_to:
        raise EvidenceIntelligenceValidationError(
            "recorded_from must be earlier than recorded_to."
        )
    if resolved_to - resolved_from > MAX_WINDOW:
        raise EvidenceIntelligenceValidationError(
            "recorded window cannot exceed 30 calendar days."
        )
    normalized_event_type = None
    if event_type is not None:
        normalized_event_type = str(event_type).strip()
        if normalized_event_type not in EVENT_TYPES:
            raise EvidenceIntelligenceValidationError(
                "event_type must be one of: " + ", ".join(EVENT_TYPES) + "."
            )
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise EvidenceIntelligenceValidationError("limit must be an integer.")
    if not 1 <= limit <= MAX_LIMIT:
        raise EvidenceIntelligenceValidationError(
            f"limit must be between 1 and {MAX_LIMIT}."
        )
    return EvidenceIntelligenceRequest(
        evaluated_at_utc=evaluated,
        as_of_cutoff=as_of_cutoff,
        recorded_from=resolved_from,
        recorded_to=resolved_to,
        event_type=normalized_event_type,
        limit=limit,
        cursor=decode_cursor(cursor) if cursor is not None else None,
    )


def encode_cursor(position: FeedCursorPosition) -> str:
    payload = {
        "event_id": str(position.event_id),
        "event_type": position.event_type,
        "recorded_at_utc": timestamp_text(position.recorded_at_utc),
        "v": CURSOR_VERSION,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    ).decode("ascii")
    return encoded.rstrip("=")


def decode_cursor(value: str) -> FeedCursorPosition:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceIntelligenceValidationError("cursor must be a non-empty string.")
    normalized = value.strip()
    if len(normalized) > MAX_CURSOR_LENGTH:
        raise EvidenceIntelligenceValidationError("cursor is too large.")
    try:
        padding = "=" * (-len(normalized) % 4)
        decoded = base64.b64decode(
            normalized + padding,
            altchars=b"-_",
            validate=True,
        )
        payload = json.loads(decoded.decode("utf-8"))
    except (
        binascii.Error,
        UnicodeDecodeError,
        json.JSONDecodeError,
        ValueError,
    ) as exc:
        raise EvidenceIntelligenceValidationError("cursor is malformed.") from exc
    expected_keys = {"v", "recorded_at_utc", "event_type", "event_id"}
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise EvidenceIntelligenceValidationError("cursor shape is invalid.")
    if payload["v"] != CURSOR_VERSION:
        raise EvidenceIntelligenceValidationError("cursor version is unsupported.")
    event_type = payload["event_type"]
    if event_type not in EVENT_TYPES:
        raise EvidenceIntelligenceValidationError("cursor event_type is invalid.")
    try:
        event_id = UUID(str(payload["event_id"]))
    except (ValueError, TypeError, AttributeError) as exc:
        raise EvidenceIntelligenceValidationError("cursor event_id is invalid.") from exc
    recorded_at = _parse_cursor_timestamp(payload["recorded_at_utc"])
    return FeedCursorPosition(
        recorded_at_utc=recorded_at,
        event_type=event_type,
        event_id=event_id,
    )


def _parse_cursor_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceIntelligenceValidationError(
            "cursor recorded_at_utc is invalid."
        )
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise EvidenceIntelligenceValidationError(
            "cursor recorded_at_utc is invalid."
        ) from exc
    return _aware_utc(parsed, "cursor recorded_at_utc")


def _aware_utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise EvidenceIntelligenceValidationError(f"{field_name} must be a timestamp.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise EvidenceIntelligenceValidationError(
            f"{field_name} must include a UTC offset."
        )
    return stored_utc(value)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _sort_rows(rows: list[EvidenceIntelligenceRow]) -> None:
    for row in rows:
        if row.event_type not in EVENT_TYPE_ORDER:
            raise EvidenceIntelligenceDataError(
                f"unsupported accepted feed event type: {row.event_type}"
            )
    rows.sort(key=lambda row: row.event_id.int, reverse=True)
    rows.sort(key=lambda row: EVENT_TYPE_ORDER[row.event_type])
    rows.sort(key=lambda row: stored_utc(row.recorded_at_utc), reverse=True)


def _cursor_from_row(row: EvidenceIntelligenceRow) -> FeedCursorPosition:
    return FeedCursorPosition(
        recorded_at_utc=stored_utc(row.recorded_at_utc),
        event_type=row.event_type,
        event_id=row.event_id,
    )


def _event_payload(row: EvidenceIntelligenceRow) -> dict[str, Any]:
    return {
        "event_type": row.event_type,
        "event_id": str(row.event_id),
        "object_id": str(row.object_id),
        "revision_no": row.revision_no,
        "primary_text": row.primary_text,
        "primary_text_source_field": row.primary_text_source_field,
        "summary": row.summary,
        "information_date": date_text(row.information_date),
        "information_cutoff_date": date_text(row.information_cutoff_date),
        "recorded_at_utc": timestamp_text(row.recorded_at_utc),
        "source_kind": row.source_kind,
        "evidence_grade": row.evidence_grade,
        "source_locator": row.source_locator,
        "supersedes_id": uuid_text(row.supersedes_id),
        "detail_path": row.detail_path,
    }

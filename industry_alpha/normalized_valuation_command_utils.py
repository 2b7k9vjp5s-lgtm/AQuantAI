"""Shared strict local-command mechanics for normalized valuation Slice 5."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from threading import Lock, RLock
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.normalized_financial_rules import NormalizedMetricError

_LOCK_GUARD = Lock()
_LOCKS: dict[tuple[str, str], RLock] = {}


def identity_lock(kind: str, key: str) -> RLock:
    with _LOCK_GUARD:
        return _LOCKS.setdefault((kind, key), RLock())


def stored_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def parse_utc(value: Any, field: str) -> datetime:
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise NormalizedMetricError(
            "normalized_metric_input_invalid", f"{field} must be ISO UTC"
        ) from exc
    if result.tzinfo is None or result.utcoffset() != timezone.utc.utcoffset(result):
        raise NormalizedMetricError(
            "normalized_metric_input_invalid", f"{field} must be explicit UTC"
        )
    return result.astimezone(timezone.utc)


def parse_date(value: Any, field: str, *, optional: bool = False) -> date | None:
    if value is None and optional:
        return None
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise NormalizedMetricError(
            "normalized_metric_input_invalid", f"{field} must be YYYY-MM-DD"
        ) from exc


def parse_uuid(value: Any, field: str, *, optional: bool = False) -> UUID | None:
    if value is None and optional:
        return None
    try:
        return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise NormalizedMetricError(
            "normalized_metric_input_invalid", f"{field} must be an explicit UUID"
        ) from exc


def bounded_text(
    value: Any, field: str, limit: int, *, optional: bool = False
) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise NormalizedMetricError(
            "normalized_metric_input_invalid", f"{field} must be bounded text"
        )
    return value.strip()


def integer_value(value: Any, field: str, *, optional: bool = False) -> int | None:
    if value is None and optional:
        return None
    if isinstance(value, bool):
        raise NormalizedMetricError(
            "normalized_metric_input_invalid", f"{field} must be an integer"
        )
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise NormalizedMetricError(
            "normalized_metric_input_invalid", f"{field} must be an integer"
        ) from exc
    if str(result) != str(value).strip():
        raise NormalizedMetricError(
            "normalized_metric_input_invalid", f"{field} must be an exact integer"
        )
    return result


def require_keys(raw: Any, allowed: set[str], required: set[str]) -> None:
    if not isinstance(raw, dict):
        raise NormalizedMetricError(
            "normalized_metric_input_invalid", "input must be a JSON object"
        )
    unknown = sorted(set(raw) - allowed)
    missing = sorted(required - set(raw))
    if unknown:
        raise NormalizedMetricError(
            "normalized_metric_unknown_field", f"unknown fields: {', '.join(unknown)}"
        )
    if missing:
        raise NormalizedMetricError(
            "normalized_metric_input_invalid", f"missing fields: {', '.join(missing)}"
        )


def require_visible(row: Any, cutoff: date, recorded_at: datetime) -> None:
    information = getattr(row, "information_cutoff_date", None)
    if information is None:
        information = getattr(row, "information_date", None)
    recorded = getattr(row, "recorded_at_utc", None)
    if information is not None and information > cutoff:
        raise NormalizedMetricError(
            "normalized_metric_later_information", "upstream information exceeds cutoff"
        )
    if recorded is not None and stored_utc(recorded) > recorded_at:
        raise NormalizedMetricError(
            "normalized_metric_later_information", "upstream record exceeds recorded boundary"
        )


def latest_revision(
    session: Session, model: type[Any], foreign_key: Any, identity_id: UUID | None
) -> Any | None:
    if identity_id is None:
        return None
    return session.scalar(
        select(model)
        .where(foreign_key == identity_id)
        .order_by(model.revision_no.desc())
        .limit(1)
        .with_for_update()
    )


def require_expected_latest(expected: UUID | None, latest: Any | None) -> None:
    actual = None if latest is None else latest.id
    if expected != actual:
        raise NormalizedMetricError(
            "normalized_metric_revision_conflict", "expected-latest revision does not match"
        )


def require_append_chronology(
    cutoff: date, recorded_at: datetime, latest: Any | None
) -> None:
    if cutoff > recorded_at.date():
        raise NormalizedMetricError(
            "normalized_metric_chronology_invalid", "cutoff cannot exceed recorded UTC date"
        )
    if latest is not None and (
        cutoff < latest.information_cutoff_date
        or recorded_at <= stored_utc(latest.recorded_at_utc)
    ):
        raise NormalizedMetricError(
            "normalized_metric_chronology_invalid", "append-only chronology must advance"
        )


def execute_command(
    *,
    session_factory: sessionmaker[Session],
    kind: str,
    key: str,
    dry_run: bool,
    action: Callable[[Session], dict[str, Any]],
) -> dict[str, Any]:
    try:
        with identity_lock(kind, key):
            if dry_run:
                with session_factory() as session:
                    return action(session)
            with session_factory.begin() as session:
                return action(session)
    except IntegrityError as exc:
        raise NormalizedMetricError(
            "normalized_metric_revision_conflict",
            "normalized metric history conflicts with accepted history",
        ) from exc


def decimal_text(value: Decimal | None, scale: int) -> str | None:
    if value is None:
        return None
    return format(value, f".{scale}f")

"""Neutral pure value helpers shared by Stage 2 query services."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from industry_alpha.errors import EvidenceLedgerNotVisible


def stored_utc(value: datetime | None) -> datetime:
    """Return a required timestamp normalized to UTC."""

    if value is None:
        raise EvidenceLedgerNotVisible("required UTC timestamp is unavailable.")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def timestamp_text(value: datetime | None) -> str:
    """Serialize a required timestamp with the existing trailing-Z convention."""

    return stored_utc(value).isoformat().replace("+00:00", "Z")


def date_text(value: date | None) -> str | None:
    """Serialize an optional calendar date."""

    return None if value is None else value.isoformat()


def uuid_text(value: UUID | None) -> str | None:
    """Serialize an optional UUID."""

    return None if value is None else str(value)


def recorded_visible(recorded_at: datetime, cutoff: date | None) -> bool:
    """Return whether a recorded timestamp is visible at a calendar-date cutoff."""

    return cutoff is None or stored_utc(recorded_at).date() <= cutoff


def dated_visible(
    information_date: date,
    recorded_at: datetime,
    cutoff: date | None,
) -> bool:
    """Return whether both information and recorded dates are cutoff-visible."""

    return cutoff is None or (
        information_date <= cutoff and stored_utc(recorded_at).date() <= cutoff
    )

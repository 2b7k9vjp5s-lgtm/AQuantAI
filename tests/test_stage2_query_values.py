from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest

from industry_alpha.errors import EvidenceLedgerNotVisible
from industry_alpha.stage2_query_values import (
    date_text,
    dated_visible,
    recorded_visible,
    stored_utc,
    timestamp_text,
    uuid_text,
)


def test_missing_required_timestamp_preserves_exact_error() -> None:
    with pytest.raises(
        EvidenceLedgerNotVisible,
        match=r"^required UTC timestamp is unavailable\.$",
    ):
        stored_utc(None)

    with pytest.raises(
        EvidenceLedgerNotVisible,
        match=r"^required UTC timestamp is unavailable\.$",
    ):
        timestamp_text(None)


def test_naive_datetime_is_assigned_utc_without_wall_clock_change() -> None:
    value = datetime(2026, 7, 19, 10, 30, 15)

    normalized = stored_utc(value)

    assert normalized == datetime(2026, 7, 19, 10, 30, 15, tzinfo=timezone.utc)
    assert normalized.tzinfo is timezone.utc


def test_aware_datetime_is_converted_to_utc_and_timestamp_uses_z() -> None:
    value = datetime(
        2026,
        7,
        19,
        18,
        30,
        15,
        tzinfo=timezone(timedelta(hours=8)),
    )

    assert stored_utc(value) == datetime(
        2026, 7, 19, 10, 30, 15, tzinfo=timezone.utc
    )
    assert timestamp_text(value) == "2026-07-19T10:30:15Z"


def test_optional_date_and_uuid_text_preserve_none() -> None:
    value = UUID("12345678-1234-5678-1234-567812345678")

    assert date_text(None) is None
    assert date_text(date(2026, 7, 19)) == "2026-07-19"
    assert uuid_text(None) is None
    assert uuid_text(value) == "12345678-1234-5678-1234-567812345678"


def test_recorded_visibility_is_date_granular_and_inclusive() -> None:
    recorded = datetime(2026, 7, 19, 23, 59, tzinfo=timezone.utc)

    assert recorded_visible(recorded, None)
    assert not recorded_visible(recorded, date(2026, 7, 18))
    assert recorded_visible(recorded, date(2026, 7, 19))
    assert recorded_visible(recorded, date(2026, 7, 20))


def test_dated_visibility_requires_both_dates_to_be_visible() -> None:
    recorded = datetime(2026, 7, 19, 10, tzinfo=timezone.utc)
    cutoff = date(2026, 7, 19)

    assert dated_visible(date(2026, 7, 19), recorded, None)
    assert dated_visible(date(2026, 7, 19), recorded, cutoff)
    assert not dated_visible(
        date(2026, 7, 20),
        recorded,
        cutoff,
    )
    assert not dated_visible(
        date(2026, 7, 18),
        datetime(2026, 7, 20, 10, tzinfo=timezone.utc),
        cutoff,
    )

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest

from industry_alpha.evidence_intelligence_query import (
    EvidenceIntelligenceQueryService,
    EvidenceIntelligenceValidationError,
    decode_cursor,
    encode_cursor,
    resolve_feed_request,
)
from industry_alpha.evidence_intelligence_repository import (
    EVENT_TYPE_CASE_REVISION,
    EVENT_TYPE_COMPANY_RESEARCH_REVISION,
    EVENT_TYPE_EVIDENCE,
    EVENT_TYPE_INDUSTRY_MAP_REVISION,
    EvidenceIntelligenceRow,
    FeedCursorPosition,
)

UTC = timezone.utc
NOW = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)


class FakeRepository:
    def __init__(self, rows: list[EvidenceIntelligenceRow]) -> None:
        self.rows = rows
        self.calls: list[dict] = []

    def list_events(self, **kwargs):
        self.calls.append(kwargs)
        return tuple(self.rows)


def _row(event_type: str, identifier: int, *, recorded_at: datetime = NOW):
    event_id = UUID(int=identifier)
    object_id = UUID(int=identifier + 1000)
    return EvidenceIntelligenceRow(
        event_type=event_type,
        event_id=event_id,
        object_id=object_id,
        revision_no=None if event_type == EVENT_TYPE_EVIDENCE else 1,
        primary_text=f"event-{identifier}",
        primary_text_source_field=(
            "source_title"
            if event_type == EVENT_TYPE_EVIDENCE
            else "research_question"
            if event_type == EVENT_TYPE_COMPANY_RESEARCH_REVISION
            else "title"
        ),
        summary=None,
        information_date=date(2026, 7, 19)
        if event_type == EVENT_TYPE_EVIDENCE
        else None,
        information_cutoff_date=None
        if event_type == EVENT_TYPE_EVIDENCE
        else date(2026, 7, 19),
        recorded_at_utc=recorded_at,
        source_kind="official" if event_type == EVENT_TYPE_EVIDENCE else None,
        evidence_grade="A" if event_type == EVENT_TYPE_EVIDENCE else None,
        source_locator=None,
        supersedes_id=None,
        detail_path=f"/industry-alpha/cases/{object_id}",
    )


def test_query_orders_equal_timestamps_and_emits_cursor() -> None:
    repository = FakeRepository(
        [
            _row(EVENT_TYPE_COMPANY_RESEARCH_REVISION, 4),
            _row(EVENT_TYPE_INDUSTRY_MAP_REVISION, 3),
            _row(EVENT_TYPE_CASE_REVISION, 2),
            _row(EVENT_TYPE_EVIDENCE, 1),
        ]
    )
    request = resolve_feed_request(
        limit=2,
        evaluated_at_utc=NOW + timedelta(hours=1),
    )

    result = EvidenceIntelligenceQueryService(repository).build_feed(request)

    assert [event["event_type"] for event in result.events] == [
        EVENT_TYPE_EVIDENCE,
        EVENT_TYPE_CASE_REVISION,
    ]
    assert result.next_cursor is not None
    position = decode_cursor(result.next_cursor)
    assert position.event_type == EVENT_TYPE_CASE_REVISION
    assert position.event_id == UUID(int=2)
    assert repository.calls[0]["per_source_limit"] == 3


def test_cursor_round_trip_is_versioned_and_utc_normalized() -> None:
    position = FeedCursorPosition(
        recorded_at_utc=datetime(2026, 7, 20, 20, 0, tzinfo=timezone(timedelta(hours=8))),
        event_type=EVENT_TYPE_EVIDENCE,
        event_id=UUID(int=99),
    )

    decoded = decode_cursor(encode_cursor(position))

    assert decoded.event_type == position.event_type
    assert decoded.event_id == position.event_id
    assert decoded.recorded_at_utc == NOW


def test_resolve_request_defaults_to_seven_day_window() -> None:
    request = resolve_feed_request(evaluated_at_utc=NOW)

    assert request.recorded_to == NOW
    assert request.recorded_from == NOW - timedelta(days=7)
    assert request.limit == 50


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {
                "recorded_from": NOW - timedelta(days=31),
                "recorded_to": NOW,
                "evaluated_at_utc": NOW,
            },
            "30 calendar days",
        ),
        (
            {
                "recorded_from": datetime(2026, 7, 19, 12, 0),
                "evaluated_at_utc": NOW,
            },
            "UTC offset",
        ),
        (
            {"event_type": "opportunity", "evaluated_at_utc": NOW},
            "event_type",
        ),
        (
            {"limit": 101, "evaluated_at_utc": NOW},
            "limit",
        ),
        (
            {"cursor": "not-a-cursor", "evaluated_at_utc": NOW},
            "cursor",
        ),
    ],
)
def test_resolve_request_fails_closed(kwargs, message) -> None:
    with pytest.raises(EvidenceIntelligenceValidationError, match=message):
        resolve_feed_request(**kwargs)

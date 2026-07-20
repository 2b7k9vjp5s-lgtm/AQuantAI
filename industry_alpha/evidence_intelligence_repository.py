"""Bounded scalar reads for the global Evidence Intelligence feed."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from industry_alpha.chain_map_models import IndustryMapRevision
from industry_alpha.models import EvidenceItem, ResearchCaseRevision
from industry_alpha.stage2_models import Stage2CompanyResearchRevision
from industry_alpha.stage2_query_values import stored_utc

EVENT_TYPE_EVIDENCE = "evidence"
EVENT_TYPE_CASE_REVISION = "case_revision"
EVENT_TYPE_INDUSTRY_MAP_REVISION = "industry_map_revision"
EVENT_TYPE_COMPANY_RESEARCH_REVISION = "company_research_revision"

EVENT_TYPES = (
    EVENT_TYPE_EVIDENCE,
    EVENT_TYPE_CASE_REVISION,
    EVENT_TYPE_INDUSTRY_MAP_REVISION,
    EVENT_TYPE_COMPANY_RESEARCH_REVISION,
)
EVENT_TYPE_ORDER = {event_type: index for index, event_type in enumerate(EVENT_TYPES)}


class EvidenceIntelligenceDataError(RuntimeError):
    """A required accepted feed value could not be projected safely."""


@dataclass(frozen=True)
class FeedCursorPosition:
    recorded_at_utc: datetime
    event_type: str
    event_id: UUID


@dataclass(frozen=True)
class EvidenceIntelligenceRow:
    event_type: str
    event_id: UUID
    object_id: UUID
    revision_no: int | None
    primary_text: str
    primary_text_source_field: str
    summary: str | None
    information_date: date | None
    information_cutoff_date: date | None
    recorded_at_utc: datetime
    source_kind: str | None
    evidence_grade: str | None
    source_locator: str | None
    supersedes_id: UUID | None
    detail_path: str | None


class EvidenceIntelligenceRepository:
    """Read exactly the approved feed columns without loading domain graphs."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_events(
        self,
        *,
        recorded_from: datetime,
        recorded_to: datetime,
        as_of_cutoff: date | None,
        event_type: str | None,
        cursor: FeedCursorPosition | None,
        per_source_limit: int,
    ) -> tuple[EvidenceIntelligenceRow, ...]:
        selected_types = (event_type,) if event_type is not None else EVENT_TYPES
        rows: list[EvidenceIntelligenceRow] = []
        for selected_type in selected_types:
            if selected_type == EVENT_TYPE_EVIDENCE:
                rows.extend(
                    self._list_evidence(
                        recorded_from,
                        recorded_to,
                        as_of_cutoff,
                        cursor,
                        per_source_limit,
                    )
                )
            elif selected_type == EVENT_TYPE_CASE_REVISION:
                rows.extend(
                    self._list_case_revisions(
                        recorded_from,
                        recorded_to,
                        as_of_cutoff,
                        cursor,
                        per_source_limit,
                    )
                )
            elif selected_type == EVENT_TYPE_INDUSTRY_MAP_REVISION:
                rows.extend(
                    self._list_map_revisions(
                        recorded_from,
                        recorded_to,
                        as_of_cutoff,
                        cursor,
                        per_source_limit,
                    )
                )
            elif selected_type == EVENT_TYPE_COMPANY_RESEARCH_REVISION:
                rows.extend(
                    self._list_company_revisions(
                        recorded_from,
                        recorded_to,
                        as_of_cutoff,
                        cursor,
                        per_source_limit,
                    )
                )
            else:
                raise EvidenceIntelligenceDataError(
                    f"unsupported accepted feed event type: {selected_type}"
                )
        return tuple(rows)

    def _list_evidence(
        self,
        recorded_from: datetime,
        recorded_to: datetime,
        cutoff: date | None,
        cursor: FeedCursorPosition | None,
        limit: int,
    ) -> tuple[EvidenceIntelligenceRow, ...]:
        statement = select(
            EvidenceItem.id.label("event_id"),
            EvidenceItem.case_id.label("object_id"),
            EvidenceItem.source_title.label("primary_text"),
            EvidenceItem.summary.label("summary"),
            EvidenceItem.information_date.label("information_date"),
            EvidenceItem.recorded_at_utc.label("recorded_at_utc"),
            EvidenceItem.source_kind.label("source_kind"),
            EvidenceItem.evidence_grade.label("evidence_grade"),
            EvidenceItem.source_locator.label("source_locator"),
            EvidenceItem.supersedes_evidence_id.label("supersedes_id"),
        ).where(
            *self._visibility_conditions(
                EvidenceItem.recorded_at_utc,
                EvidenceItem.information_date,
                recorded_from,
                recorded_to,
                cutoff,
            )
        )
        cursor_condition = self._cursor_condition(
            EVENT_TYPE_EVIDENCE,
            EvidenceItem.recorded_at_utc,
            EvidenceItem.id,
            cursor,
        )
        if cursor_condition is not None:
            statement = statement.where(cursor_condition)
        statement = statement.order_by(
            EvidenceItem.recorded_at_utc.desc(), EvidenceItem.id.desc()
        ).limit(limit)
        return tuple(
            self._evidence_row(mapping)
            for mapping in self._session.execute(statement).mappings()
        )

    def _list_case_revisions(
        self,
        recorded_from: datetime,
        recorded_to: datetime,
        cutoff: date | None,
        cursor: FeedCursorPosition | None,
        limit: int,
    ) -> tuple[EvidenceIntelligenceRow, ...]:
        statement = select(
            ResearchCaseRevision.id.label("event_id"),
            ResearchCaseRevision.case_id.label("object_id"),
            ResearchCaseRevision.revision_no.label("revision_no"),
            ResearchCaseRevision.title.label("primary_text"),
            ResearchCaseRevision.summary.label("summary"),
            ResearchCaseRevision.information_cutoff_date.label(
                "information_cutoff_date"
            ),
            ResearchCaseRevision.recorded_at_utc.label("recorded_at_utc"),
            ResearchCaseRevision.supersedes_revision_id.label("supersedes_id"),
        ).where(
            *self._visibility_conditions(
                ResearchCaseRevision.recorded_at_utc,
                ResearchCaseRevision.information_cutoff_date,
                recorded_from,
                recorded_to,
                cutoff,
            )
        )
        cursor_condition = self._cursor_condition(
            EVENT_TYPE_CASE_REVISION,
            ResearchCaseRevision.recorded_at_utc,
            ResearchCaseRevision.id,
            cursor,
        )
        if cursor_condition is not None:
            statement = statement.where(cursor_condition)
        statement = statement.order_by(
            ResearchCaseRevision.recorded_at_utc.desc(),
            ResearchCaseRevision.id.desc(),
        ).limit(limit)
        return tuple(
            self._revision_row(
                mapping,
                EVENT_TYPE_CASE_REVISION,
                "title",
                "/industry-alpha/cases/{object_id}",
            )
            for mapping in self._session.execute(statement).mappings()
        )

    def _list_map_revisions(
        self,
        recorded_from: datetime,
        recorded_to: datetime,
        cutoff: date | None,
        cursor: FeedCursorPosition | None,
        limit: int,
    ) -> tuple[EvidenceIntelligenceRow, ...]:
        statement = select(
            IndustryMapRevision.id.label("event_id"),
            IndustryMapRevision.map_id.label("object_id"),
            IndustryMapRevision.revision_no.label("revision_no"),
            IndustryMapRevision.title.label("primary_text"),
            IndustryMapRevision.scope.label("summary"),
            IndustryMapRevision.information_cutoff_date.label(
                "information_cutoff_date"
            ),
            IndustryMapRevision.recorded_at_utc.label("recorded_at_utc"),
            IndustryMapRevision.supersedes_revision_id.label("supersedes_id"),
        ).where(
            *self._visibility_conditions(
                IndustryMapRevision.recorded_at_utc,
                IndustryMapRevision.information_cutoff_date,
                recorded_from,
                recorded_to,
                cutoff,
            )
        )
        cursor_condition = self._cursor_condition(
            EVENT_TYPE_INDUSTRY_MAP_REVISION,
            IndustryMapRevision.recorded_at_utc,
            IndustryMapRevision.id,
            cursor,
        )
        if cursor_condition is not None:
            statement = statement.where(cursor_condition)
        statement = statement.order_by(
            IndustryMapRevision.recorded_at_utc.desc(),
            IndustryMapRevision.id.desc(),
        ).limit(limit)
        return tuple(
            self._revision_row(
                mapping,
                EVENT_TYPE_INDUSTRY_MAP_REVISION,
                "title",
                "/industry-alpha/maps/{object_id}",
            )
            for mapping in self._session.execute(statement).mappings()
        )

    def _list_company_revisions(
        self,
        recorded_from: datetime,
        recorded_to: datetime,
        cutoff: date | None,
        cursor: FeedCursorPosition | None,
        limit: int,
    ) -> tuple[EvidenceIntelligenceRow, ...]:
        statement = select(
            Stage2CompanyResearchRevision.id.label("event_id"),
            Stage2CompanyResearchRevision.company_research_id.label("object_id"),
            Stage2CompanyResearchRevision.revision_no.label("revision_no"),
            Stage2CompanyResearchRevision.research_question.label("primary_text"),
            Stage2CompanyResearchRevision.summary.label("summary"),
            Stage2CompanyResearchRevision.information_cutoff_date.label(
                "information_cutoff_date"
            ),
            Stage2CompanyResearchRevision.recorded_at_utc.label("recorded_at_utc"),
            Stage2CompanyResearchRevision.supersedes_revision_id.label(
                "supersedes_id"
            ),
        ).where(
            *self._visibility_conditions(
                Stage2CompanyResearchRevision.recorded_at_utc,
                Stage2CompanyResearchRevision.information_cutoff_date,
                recorded_from,
                recorded_to,
                cutoff,
            )
        )
        cursor_condition = self._cursor_condition(
            EVENT_TYPE_COMPANY_RESEARCH_REVISION,
            Stage2CompanyResearchRevision.recorded_at_utc,
            Stage2CompanyResearchRevision.id,
            cursor,
        )
        if cursor_condition is not None:
            statement = statement.where(cursor_condition)
        statement = statement.order_by(
            Stage2CompanyResearchRevision.recorded_at_utc.desc(),
            Stage2CompanyResearchRevision.id.desc(),
        ).limit(limit)
        return tuple(
            self._revision_row(
                mapping,
                EVENT_TYPE_COMPANY_RESEARCH_REVISION,
                "research_question",
                "/industry-alpha/company-research/{object_id}",
            )
            for mapping in self._session.execute(statement).mappings()
        )

    @staticmethod
    def _visibility_conditions(
        recorded_column: Any,
        information_column: Any,
        recorded_from: datetime,
        recorded_to: datetime,
        cutoff: date | None,
    ) -> tuple[Any, ...]:
        conditions: list[Any] = [
            recorded_column >= recorded_from,
            recorded_column < recorded_to,
        ]
        if cutoff is not None:
            conditions.extend(
                [
                    information_column <= cutoff,
                    recorded_column < _cutoff_exclusive_utc(cutoff),
                ]
            )
        return tuple(conditions)

    @staticmethod
    def _cursor_condition(
        source_event_type: str,
        recorded_column: Any,
        id_column: Any,
        cursor: FeedCursorPosition | None,
    ) -> Any | None:
        if cursor is None:
            return None
        source_order = EVENT_TYPE_ORDER[source_event_type]
        cursor_order = EVENT_TYPE_ORDER[cursor.event_type]
        cursor_time = stored_utc(cursor.recorded_at_utc)
        if source_order < cursor_order:
            return recorded_column < cursor_time
        if source_order > cursor_order:
            return recorded_column <= cursor_time
        return or_(
            recorded_column < cursor_time,
            and_(recorded_column == cursor_time, id_column < cursor.event_id),
        )

    @staticmethod
    def _evidence_row(mapping: Any) -> EvidenceIntelligenceRow:
        event_id = _required_uuid(mapping["event_id"], "evidence event_id")
        object_id = _required_uuid(mapping["object_id"], "evidence object_id")
        primary_text = _required_text(mapping["primary_text"], "evidence source_title")
        information_date = _required_date(
            mapping["information_date"], "evidence information_date"
        )
        source_kind = _required_text(mapping["source_kind"], "evidence source_kind")
        evidence_grade = _required_text(
            mapping["evidence_grade"], "evidence evidence_grade"
        )
        return EvidenceIntelligenceRow(
            event_type=EVENT_TYPE_EVIDENCE,
            event_id=event_id,
            object_id=object_id,
            revision_no=None,
            primary_text=primary_text,
            primary_text_source_field="source_title",
            summary=mapping["summary"],
            information_date=information_date,
            information_cutoff_date=None,
            recorded_at_utc=_required_utc(
                mapping["recorded_at_utc"], "evidence recorded_at_utc"
            ),
            source_kind=source_kind,
            evidence_grade=evidence_grade,
            source_locator=mapping["source_locator"],
            supersedes_id=_optional_uuid(mapping["supersedes_id"]),
            detail_path=f"/industry-alpha/cases/{object_id}",
        )

    @staticmethod
    def _revision_row(
        mapping: Any,
        event_type: str,
        primary_text_source_field: str,
        detail_path_template: str,
    ) -> EvidenceIntelligenceRow:
        event_id = _required_uuid(mapping["event_id"], f"{event_type} event_id")
        object_id = _required_uuid(mapping["object_id"], f"{event_type} object_id")
        revision_no = mapping["revision_no"]
        if not isinstance(revision_no, int) or revision_no <= 0:
            raise EvidenceIntelligenceDataError(
                f"{event_type} revision_no is unavailable or invalid."
            )
        return EvidenceIntelligenceRow(
            event_type=event_type,
            event_id=event_id,
            object_id=object_id,
            revision_no=revision_no,
            primary_text=_required_text(
                mapping["primary_text"], f"{event_type} primary_text"
            ),
            primary_text_source_field=primary_text_source_field,
            summary=mapping["summary"],
            information_date=None,
            information_cutoff_date=_required_date(
                mapping["information_cutoff_date"],
                f"{event_type} information_cutoff_date",
            ),
            recorded_at_utc=_required_utc(
                mapping["recorded_at_utc"], f"{event_type} recorded_at_utc"
            ),
            source_kind=None,
            evidence_grade=None,
            source_locator=None,
            supersedes_id=_optional_uuid(mapping["supersedes_id"]),
            detail_path=detail_path_template.format(object_id=object_id),
        )


def _cutoff_exclusive_utc(value: date) -> datetime:
    if value == date.max:
        return datetime.max.replace(tzinfo=timezone.utc)
    return datetime.combine(value + timedelta(days=1), time.min, tzinfo=timezone.utc)


def _required_uuid(value: Any, field_name: str) -> UUID:
    if value is None:
        raise EvidenceIntelligenceDataError(f"{field_name} is unavailable.")
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise EvidenceIntelligenceDataError(f"{field_name} is invalid.") from exc


def _optional_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    try:
        return value if isinstance(value, UUID) else UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise EvidenceIntelligenceDataError("supersedes_id is invalid.") from exc


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceIntelligenceDataError(f"{field_name} is unavailable.")
    return value


def _required_date(value: Any, field_name: str) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise EvidenceIntelligenceDataError(f"{field_name} is unavailable or invalid.")
    return value


def _required_utc(value: Any, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise EvidenceIntelligenceDataError(f"{field_name} is unavailable or invalid.")
    try:
        return stored_utc(value)
    except ValueError as exc:
        raise EvidenceIntelligenceDataError(f"{field_name} is invalid.") from exc

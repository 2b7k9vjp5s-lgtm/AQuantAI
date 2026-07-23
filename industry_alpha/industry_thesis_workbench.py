"""Bounded projections and exact local options for the personal research workbench."""

from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from backend.database.canonical_price_models import (
    ListedInstrument,
    ListedInstrumentRevision,
)
from backend.database.models import IngestionRun, StockBasicRecord
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.industry_thesis_models import (
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_rules import stored_utc


class IndustryThesisWorkbenchError(ValueError):
    """Stable workbench validation failure."""


_EXACT_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{3,31}$")


def validate_workbench_boundary(
    as_of_cutoff: date,
    as_of_recorded_at_utc: datetime,
) -> datetime:
    """Require an explicit UTC recorded boundary compatible with the cutoff."""

    if (
        as_of_recorded_at_utc.tzinfo is None
        or as_of_recorded_at_utc.utcoffset()
        != timezone.utc.utcoffset(as_of_recorded_at_utc)
    ):
        raise IndustryThesisWorkbenchError(
            "as_of_recorded_at_utc must be an explicit UTC timestamp"
        )
    boundary = as_of_recorded_at_utc.astimezone(timezone.utc)
    if as_of_cutoff > boundary.date():
        raise IndustryThesisWorkbenchError(
            "as_of_cutoff cannot be later than as_of_recorded_at_utc"
        )
    return boundary


def _validated_limit(limit: int, maximum: int) -> int:
    if limit < 1 or limit > maximum:
        raise IndustryThesisWorkbenchError(
            f"limit must be between 1 and {maximum}"
        )
    return limit


def _display_title(revision: IndustryThesisSessionRevision) -> str:
    reviewed = (revision.thesis_title_reviewed or "").strip()
    if reviewed:
        return reviewed
    first_line = next(
        (
            line.strip()
            for line in revision.thesis_text_original.splitlines()
            if line.strip()
        ),
        "未命名研究",
    )
    return first_line if len(first_line) <= 80 else f"{first_line[:77]}…"


def _text_preview(value: str) -> str:
    normalized = " ".join(value.split())
    return normalized if len(normalized) <= 180 else f"{normalized[:177]}…"


def _next_surface(workflow_state: str) -> str:
    if workflow_state == "reviewed_plan_ready":
        return "result"
    if workflow_state in {"candidate_build_ready", "awaiting_review"}:
        return "review"
    return "scope"


def _normalized_option_query(query: str | None) -> str:
    value = "" if query is None else query.strip()
    if len(value) > 120:
        raise IndustryThesisWorkbenchError(
            "query must be no longer than 120 characters"
        )
    return value


class IndustryThesisWorkbenchQueryService:
    """Compose bounded views without creating a second state owner."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_sessions(
        self,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
        limit: int = 50,
    ) -> dict[str, Any]:
        boundary = validate_workbench_boundary(
            as_of_cutoff,
            as_of_recorded_at_utc,
        )
        _validated_limit(limit, 100)

        visible = (
            select(
                IndustryThesisSessionRevision.session_id.label("session_id"),
                func.max(
                    IndustryThesisSessionRevision.revision_number
                ).label("latest_revision_number"),
                func.count(
                    IndustryThesisSessionRevision.id
                ).label("visible_revision_count"),
            )
            .where(
                IndustryThesisSessionRevision.information_cutoff_date
                <= as_of_cutoff,
                IndustryThesisSessionRevision.recorded_at_utc <= boundary,
            )
            .group_by(IndustryThesisSessionRevision.session_id)
            .subquery()
        )

        statement = (
            select(
                IndustryThesisSessionIdentity,
                IndustryThesisSessionRevision,
                visible.c.visible_revision_count,
            )
            .join(
                visible,
                visible.c.session_id == IndustryThesisSessionIdentity.id,
            )
            .join(
                IndustryThesisSessionRevision,
                and_(
                    IndustryThesisSessionRevision.session_id
                    == IndustryThesisSessionIdentity.id,
                    IndustryThesisSessionRevision.revision_number
                    == visible.c.latest_revision_number,
                ),
            )
            .where(
                IndustryThesisSessionIdentity.created_recorded_utc <= boundary
            )
            .order_by(
                IndustryThesisSessionRevision.recorded_at_utc.desc(),
                IndustryThesisSessionIdentity.id.asc(),
            )
            .limit(limit + 1)
        )
        rows = list(self._session.execute(statement).all())
        has_more = len(rows) > limit
        rows = rows[:limit]

        sessions: list[dict[str, Any]] = []
        for identity, revision, visible_revision_count in rows:
            recorded_at = stored_utc(revision.recorded_at_utc)
            sessions.append(
                {
                    "session_id": str(identity.id),
                    "session_state": identity.state,
                    "visible_revision_count": int(visible_revision_count),
                    "visible_latest_revision_id": str(revision.id),
                    "visible_latest_revision_number": (
                        revision.revision_number
                    ),
                    "thesis_title": _display_title(revision),
                    "thesis_text_preview": _text_preview(
                        revision.thesis_text_original
                    ),
                    "driver_type": revision.driver_type,
                    "analysis_horizon_kind": (
                        revision.analysis_horizon_kind
                    ),
                    "coverage_state": revision.coverage_state,
                    "workflow_state": revision.workflow_state,
                    "next_surface": _next_surface(
                        revision.workflow_state
                    ),
                    "information_cutoff_date": (
                        revision.information_cutoff_date.isoformat()
                    ),
                    "recorded_at_utc": recorded_at.isoformat(),
                    "advanced_details": {
                        "input_fingerprint_sha256": (
                            revision.input_fingerprint_sha256
                        ),
                        "supersedes_revision_id": (
                            None
                            if revision.supersedes_revision_id is None
                            else str(revision.supersedes_revision_id)
                        ),
                    },
                }
            )

        return {
            "as_of_cutoff": as_of_cutoff.isoformat(),
            "as_of_recorded_at_utc": boundary.isoformat(),
            "limit": limit,
            "has_more": has_more,
            "session_count": len(sessions),
            "sessions": sessions,
            "notices": {
                "review_history_only": True,
                "accepted_outputs_not_inferred": True,
                "not_investment_advice": True,
            },
        }

    def list_map_options(
        self,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
        query: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Return exact latest-visible Industry Map revisions."""

        boundary = validate_workbench_boundary(
            as_of_cutoff,
            as_of_recorded_at_utc,
        )
        _validated_limit(limit, 20)
        normalized_query = _normalized_option_query(query)

        visible = (
            select(
                IndustryMapRevision.map_id.label("map_id"),
                func.max(
                    IndustryMapRevision.revision_no
                ).label("revision_no"),
            )
            .where(
                IndustryMapRevision.information_cutoff_date
                <= as_of_cutoff,
                IndustryMapRevision.recorded_at_utc <= boundary,
            )
            .group_by(IndustryMapRevision.map_id)
            .subquery()
        )
        statement = (
            select(IndustryMap, IndustryMapRevision)
            .join(visible, visible.c.map_id == IndustryMap.id)
            .join(
                IndustryMapRevision,
                and_(
                    IndustryMapRevision.map_id == IndustryMap.id,
                    IndustryMapRevision.revision_no
                    == visible.c.revision_no,
                ),
            )
        )
        if normalized_query:
            pattern = f"%{normalized_query}%"
            statement = statement.where(
                or_(
                    IndustryMapRevision.title.ilike(pattern),
                    IndustryMapRevision.scope.ilike(pattern),
                    IndustryMap.map_key.ilike(pattern),
                )
            )
        statement = statement.order_by(
            func.lower(IndustryMapRevision.title),
            IndustryMap.map_key,
            IndustryMapRevision.id,
        ).limit(limit)

        options = [
            {
                "source_kind": "industry_map_revision",
                "map_id": str(industry_map.id),
                "map_revision_id": str(revision.id),
                "revision_number": revision.revision_no,
                "title": revision.title,
                "scope": revision.scope,
                "map_key": industry_map.map_key,
                "information_cutoff_date": (
                    revision.information_cutoff_date.isoformat()
                ),
                "recorded_at_utc": stored_utc(
                    revision.recorded_at_utc
                ).isoformat(),
            }
            for industry_map, revision in self._session.execute(
                statement
            ).all()
        ]
        return {
            "as_of_cutoff": as_of_cutoff.isoformat(),
            "as_of_recorded_at_utc": boundary.isoformat(),
            "query": normalized_query,
            "option_count": len(options),
            "options": options,
            "notices": {
                "explicit_selection_required": True,
                "accepted_membership_not_inferred": True,
            },
        }

    def list_company_options(
        self,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
        query: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search exact persisted stock or listed-instrument identities."""

        boundary = validate_workbench_boundary(
            as_of_cutoff,
            as_of_recorded_at_utc,
        )
        _validated_limit(limit, 20)
        normalized_query = _normalized_option_query(query)
        if len(normalized_query) < 2 and not _EXACT_CODE.fullmatch(
            normalized_query
        ):
            raise IndustryThesisWorkbenchError(
                "company query requires at least two characters or an exact code"
            )

        pattern = f"%{normalized_query}%"
        stock_rows = list(
            self._session.execute(
                select(StockBasicRecord, IngestionRun)
                .join(
                    IngestionRun,
                    IngestionRun.id
                    == StockBasicRecord.ingestion_run_id,
                )
                .where(
                    IngestionRun.status == "succeeded",
                    IngestionRun.information_cutoff_date
                    <= as_of_cutoff,
                    IngestionRun.completed_at.is_not(None),
                    IngestionRun.completed_at <= boundary,
                    or_(
                        StockBasicRecord.stock_name.ilike(pattern),
                        StockBasicRecord.stock_code.ilike(pattern),
                    ),
                )
                .order_by(
                    IngestionRun.completed_at.desc(),
                    IngestionRun.id.desc(),
                    StockBasicRecord.id.desc(),
                )
                .limit(200)
            ).all()
        )
        stock_latest: dict[tuple[str, str], tuple[Any, Any]] = {}
        for stock, run in stock_rows:
            stock_latest.setdefault(
                (stock.source, stock.stock_code),
                (stock, run),
            )

        listed_visible = (
            select(
                ListedInstrumentRevision.instrument_id.label(
                    "instrument_id"
                ),
                func.max(
                    ListedInstrumentRevision.revision_no
                ).label("revision_no"),
            )
            .where(
                ListedInstrumentRevision.information_cutoff_date
                <= as_of_cutoff,
                ListedInstrumentRevision.recorded_at_utc <= boundary,
            )
            .group_by(ListedInstrumentRevision.instrument_id)
            .subquery()
        )
        listed_rows = list(
            self._session.execute(
                select(ListedInstrument, ListedInstrumentRevision)
                .join(
                    listed_visible,
                    listed_visible.c.instrument_id
                    == ListedInstrument.id,
                )
                .join(
                    ListedInstrumentRevision,
                    and_(
                        ListedInstrumentRevision.instrument_id
                        == ListedInstrument.id,
                        ListedInstrumentRevision.revision_no
                        == listed_visible.c.revision_no,
                    ),
                )
                .where(
                    ListedInstrumentRevision.canonical_symbol.ilike(
                        pattern
                    )
                )
                .order_by(
                    func.lower(
                        ListedInstrumentRevision.canonical_symbol
                    ),
                    ListedInstrument.id,
                )
                .limit(limit * 3)
            ).all()
        )

        options: list[dict[str, Any]] = []
        for stock, run in stock_latest.values():
            options.append(
                {
                    "source_kind": "stock_basic_record",
                    "exact_id": str(stock.id),
                    "stock_basic_record_id": stock.id,
                    "listed_instrument_id": None,
                    "label": stock.stock_name,
                    "code": stock.stock_code,
                    "market": stock.exchange,
                    "industry": stock.industry,
                    "source": stock.source,
                    "information_cutoff_date": (
                        run.information_cutoff_date.isoformat()
                    ),
                    "recorded_at_utc": stored_utc(
                        run.completed_at
                    ).isoformat(),
                }
            )
        for instrument, revision in listed_rows:
            options.append(
                {
                    "source_kind": "listed_instrument",
                    "exact_id": str(instrument.id),
                    "stock_basic_record_id": None,
                    "listed_instrument_id": str(instrument.id),
                    "label": revision.canonical_symbol,
                    "code": revision.canonical_symbol,
                    "market": revision.market_code,
                    "industry": "",
                    "source": revision.recorded_by,
                    "information_cutoff_date": (
                        revision.information_cutoff_date.isoformat()
                    ),
                    "recorded_at_utc": stored_utc(
                        revision.recorded_at_utc
                    ).isoformat(),
                }
            )

        options.sort(
            key=lambda item: (
                item["label"].casefold(),
                item["code"].casefold(),
                item["source_kind"],
                item["exact_id"],
            )
        )
        options = options[:limit]
        return {
            "as_of_cutoff": as_of_cutoff.isoformat(),
            "as_of_recorded_at_utc": boundary.isoformat(),
            "query": normalized_query,
            "option_count": len(options),
            "options": options,
            "notices": {
                "explicit_selection_required": True,
                "first_result_not_selected": True,
                "text_match_is_not_identity": True,
            },
        }

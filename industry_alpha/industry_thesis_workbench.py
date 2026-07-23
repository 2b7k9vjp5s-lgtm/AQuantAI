"""Bounded read-only projections for the personal Industry Thesis workbench."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from industry_alpha.industry_thesis_models import (
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_rules import stored_utc


class IndustryThesisWorkbenchError(ValueError):
    """Stable read-model validation failure."""


def validate_workbench_boundary(
    as_of_cutoff: date,
    as_of_recorded_at_utc: datetime,
) -> datetime:
    """Require an explicit UTC recorded boundary compatible with the cutoff."""

    if (
        as_of_recorded_at_utc.tzinfo is None
        or as_of_recorded_at_utc.utcoffset() != timezone.utc.utcoffset(as_of_recorded_at_utc)
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


def _display_title(revision: IndustryThesisSessionRevision) -> str:
    reviewed = (revision.thesis_title_reviewed or "").strip()
    if reviewed:
        return reviewed
    first_line = next(
        (line.strip() for line in revision.thesis_text_original.splitlines() if line.strip()),
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


class IndustryThesisWorkbenchQueryService:
    """Compose a bounded history list without creating a second state owner."""

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
        if limit < 1 or limit > 100:
            raise IndustryThesisWorkbenchError("limit must be between 1 and 100")

        visible = (
            select(
                IndustryThesisSessionRevision.session_id.label("session_id"),
                func.max(IndustryThesisSessionRevision.revision_number).label(
                    "latest_revision_number"
                ),
                func.count(IndustryThesisSessionRevision.id).label(
                    "visible_revision_count"
                ),
            )
            .where(
                IndustryThesisSessionRevision.information_cutoff_date <= as_of_cutoff,
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
            .join(visible, visible.c.session_id == IndustryThesisSessionIdentity.id)
            .join(
                IndustryThesisSessionRevision,
                and_(
                    IndustryThesisSessionRevision.session_id
                    == IndustryThesisSessionIdentity.id,
                    IndustryThesisSessionRevision.revision_number
                    == visible.c.latest_revision_number,
                ),
            )
            .where(IndustryThesisSessionIdentity.created_recorded_utc <= boundary)
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
                    "visible_latest_revision_number": revision.revision_number,
                    "thesis_title": _display_title(revision),
                    "thesis_text_preview": _text_preview(
                        revision.thesis_text_original
                    ),
                    "driver_type": revision.driver_type,
                    "analysis_horizon_kind": revision.analysis_horizon_kind,
                    "coverage_state": revision.coverage_state,
                    "workflow_state": revision.workflow_state,
                    "next_surface": _next_surface(revision.workflow_state),
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

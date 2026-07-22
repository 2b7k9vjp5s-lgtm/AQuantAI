"""Context-aware wrappers for the approved observation and expectation commands."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.normalized_expectation_commands import (
    NormalizedExpectationGapCommandService,
    parse_expectation_gap_command,
)
from industry_alpha.normalized_financial_commands import (
    StructuredFinancialObservationCommandService,
    parse_observation_command,
)
from industry_alpha.normalized_financial_rules import NormalizedMetricError
from industry_alpha.normalized_valuation_command_utils import (
    execute_command,
    parse_uuid,
    require_visible,
)
from industry_alpha.normalized_valuation_context import (
    expectation_context,
    observation_context,
)
from industry_alpha.stage2_expectations_models import (
    Stage2MarketExpectationRevision,
    Stage2ValuationSnapshotRevision,
)

OBSERVATION_CONTEXT_FIELDS = {
    "market_expectation_revision_id",
    "valuation_snapshot_revision_id",
}
EXPECTATION_CONTEXT_FIELD = "market_expectation_revision_id"


class ContextAwareStructuredFinancialObservationCommandService:
    """Append an observation with zero or one exact optional v0.6B context."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._delegate = StructuredFinancialObservationCommandService(session_factory)

    def record_observation(
        self, raw: dict[str, Any], *, dry_run: bool = False
    ) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise NormalizedMetricError(
                "normalized_metric_input_invalid", "input must be a JSON object"
            )
        market_id = parse_uuid(
            raw.get("market_expectation_revision_id"),
            "market_expectation_revision_id",
            optional=True,
        )
        valuation_id = parse_uuid(
            raw.get("valuation_snapshot_revision_id"),
            "valuation_snapshot_revision_id",
            optional=True,
        )
        if market_id is not None and valuation_id is not None:
            raise NormalizedMetricError(
                "normalized_financial_context_invalid",
                "an observation may freeze at most one optional v0.6B context revision",
            )
        base_raw = {
            key: value for key, value in raw.items() if key not in OBSERVATION_CONTEXT_FIELDS
        }
        data = parse_observation_command(base_raw)
        return execute_command(
            session_factory=self._session_factory,
            kind="structured_financial_observation",
            key=data["observation_key"],
            dry_run=dry_run,
            action=lambda session: self._record(
                session, data, market_id, valuation_id, dry_run
            ),
        )

    def _record(
        self,
        session: Session,
        data: dict[str, Any],
        market_id: UUID | None,
        valuation_id: UUID | None,
        dry_run: bool,
    ) -> dict[str, Any]:
        self._validate_context(session, data, market_id, valuation_id)
        with observation_context(market_id, valuation_id):
            result = self._delegate._record(session, data, dry_run)
        return {
            **result,
            "market_expectation_revision_id": None
            if market_id is None
            else str(market_id),
            "valuation_snapshot_revision_id": None
            if valuation_id is None
            else str(valuation_id),
        }

    @staticmethod
    def _validate_context(
        session: Session,
        data: dict[str, Any],
        market_id: UUID | None,
        valuation_id: UUID | None,
    ) -> None:
        if market_id is not None:
            revision = session.get(Stage2MarketExpectationRevision, market_id)
            if revision is None:
                raise NormalizedMetricError(
                    "normalized_financial_context_missing",
                    "exact Market Expectation revision is missing",
                )
            if revision.company_research_revision_id != data["company_research_revision_id"]:
                raise NormalizedMetricError(
                    "normalized_financial_context_mismatch",
                    "Market Expectation context does not match the Company Research revision",
                )
            require_visible(
                revision, data["information_cutoff_date"], data["recorded_at_utc"]
            )
        if valuation_id is not None:
            revision = session.get(Stage2ValuationSnapshotRevision, valuation_id)
            if revision is None:
                raise NormalizedMetricError(
                    "normalized_financial_context_missing",
                    "exact Valuation Snapshot revision is missing",
                )
            if revision.company_research_revision_id != data["company_research_revision_id"]:
                raise NormalizedMetricError(
                    "normalized_financial_context_mismatch",
                    "Valuation Snapshot context does not match the Company Research revision",
                )
            require_visible(
                revision, data["information_cutoff_date"], data["recorded_at_utc"]
            )


class ContextAwareNormalizedExpectationGapCommandService:
    """Append an expectation gap with an optional exact Market Expectation context."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._delegate = NormalizedExpectationGapCommandService(session_factory)

    def record_expectation_gap(
        self, raw: dict[str, Any], *, dry_run: bool = False
    ) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise NormalizedMetricError(
                "normalized_metric_input_invalid", "input must be a JSON object"
            )
        market_id = parse_uuid(
            raw.get(EXPECTATION_CONTEXT_FIELD),
            EXPECTATION_CONTEXT_FIELD,
            optional=True,
        )
        base_raw = {
            key: value for key, value in raw.items() if key != EXPECTATION_CONTEXT_FIELD
        }
        data = parse_expectation_gap_command(base_raw)
        return execute_command(
            session_factory=self._session_factory,
            kind="normalized_expectation_gap",
            key=data["gap_key"],
            dry_run=dry_run,
            action=lambda session: self._record(session, data, market_id, dry_run),
        )

    def _record(
        self,
        session: Session,
        data: dict[str, Any],
        market_id: UUID | None,
        dry_run: bool,
    ) -> dict[str, Any]:
        if market_id is not None:
            revision = session.get(Stage2MarketExpectationRevision, market_id)
            if revision is None:
                raise NormalizedMetricError(
                    "normalized_expectation_context_missing",
                    "exact Market Expectation revision is missing",
                )
            if revision.company_research_revision_id != data["company_research_revision_id"]:
                raise NormalizedMetricError(
                    "normalized_expectation_context_mismatch",
                    "Market Expectation context does not match the Company Research revision",
                )
            require_visible(
                revision, data["information_cutoff_date"], data["recorded_at_utc"]
            )
        with expectation_context(market_id):
            result = self._delegate._record(session, data, dry_run)
        return {
            **result,
            "market_expectation_revision_id": None
            if market_id is None
            else str(market_id),
        }


__all__ = (
    "ContextAwareStructuredFinancialObservationCommandService",
    "ContextAwareNormalizedExpectationGapCommandService",
)

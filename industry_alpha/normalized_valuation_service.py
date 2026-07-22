"""Public normalized valuation and expectation service surface."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from industry_alpha.normalized_comparison_commands import ValuationComparisonCommandService
from industry_alpha.normalized_expectation_commands import NormalizedExpectationGapCommandService
from industry_alpha.normalized_financial_commands import StructuredFinancialObservationCommandService
from industry_alpha.normalized_financial_rules import NormalizedMetricError
from industry_alpha.normalized_valuation_commands import NormalizedValuationMetricCommandService
from industry_alpha.normalized_valuation_query import (
    NormalizedMetricNotFound,
    NormalizedValuationQueryService,
)


class NormalizedValuationCommandService:
    """One bounded façade for the four approved local write commands."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._observation = StructuredFinancialObservationCommandService(session_factory)
        self._metric = NormalizedValuationMetricCommandService(session_factory)
        self._comparison = ValuationComparisonCommandService(session_factory)
        self._expectation = NormalizedExpectationGapCommandService(session_factory)

    def record_observation(
        self, raw: dict[str, Any], *, dry_run: bool = False
    ) -> dict[str, Any]:
        return self._observation.record_observation(raw, dry_run=dry_run)

    def record_metric(
        self, raw: dict[str, Any], *, dry_run: bool = False
    ) -> dict[str, Any]:
        return self._metric.record_metric(raw, dry_run=dry_run)

    def record_comparison_set(
        self, raw: dict[str, Any], *, dry_run: bool = False
    ) -> dict[str, Any]:
        return self._comparison.record_comparison_set(raw, dry_run=dry_run)

    def record_expectation_gap(
        self, raw: dict[str, Any], *, dry_run: bool = False
    ) -> dict[str, Any]:
        return self._expectation.record_expectation_gap(raw, dry_run=dry_run)


__all__ = (
    "NormalizedValuationCommandService",
    "NormalizedValuationQueryService",
    "NormalizedMetricError",
    "NormalizedMetricNotFound",
)

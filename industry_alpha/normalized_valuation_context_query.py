"""Exact-ID reads including optional typed v0.6B context revisions."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from industry_alpha.normalized_valuation_models import (
    NormalizedExpectationGapRevision,
    StructuredFinancialObservationRevision,
)
from industry_alpha.normalized_valuation_query import (
    NormalizedValuationQueryService as BaseNormalizedValuationQueryService,
)


class NormalizedValuationQueryService(BaseNormalizedValuationQueryService):
    """Extend the accepted exact-ID payload with optional context revision IDs."""

    def get_financial_observation_revision(
        self,
        revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        payload = super().get_financial_observation_revision(
            revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=as_of_recorded_at_utc,
        )
        revision = self._session.get(StructuredFinancialObservationRevision, revision_id)
        payload["market_expectation_revision_id"] = (
            None
            if revision.market_expectation_revision_id is None
            else str(revision.market_expectation_revision_id)
        )
        payload["valuation_snapshot_revision_id"] = (
            None
            if revision.valuation_snapshot_revision_id is None
            else str(revision.valuation_snapshot_revision_id)
        )
        return payload

    def get_expectation_gap_revision(
        self,
        revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> dict[str, Any]:
        payload = super().get_expectation_gap_revision(
            revision_id,
            as_of_cutoff=as_of_cutoff,
            as_of_recorded_at_utc=as_of_recorded_at_utc,
        )
        revision = self._session.get(NormalizedExpectationGapRevision, revision_id)
        payload["market_expectation_revision_id"] = (
            None
            if revision.market_expectation_revision_id is None
            else str(revision.market_expectation_revision_id)
        )
        return payload


__all__ = ("NormalizedValuationQueryService",)

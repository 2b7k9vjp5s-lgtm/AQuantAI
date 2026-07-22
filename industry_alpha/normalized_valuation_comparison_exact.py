"""Exact-revision gate for the atomic Slice 5 comparison command."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from industry_alpha.normalized_financial_rules import NormalizedMetricError
from industry_alpha.normalized_valuation_comparison_service import (
    StrictValuationComparisonCommandService,
)


class ExactValuationComparisonCommandService(
    StrictValuationComparisonCommandService
):
    """Require every metric revision to bind the member's exact instrument revision."""

    def _record(
        self, session: Session, data: dict[str, Any], dry_run: bool
    ) -> dict[str, Any]:
        subject_member = next(member for member in data["members"] if member["is_subject"])
        subject_revision, subject_identity = self._metric_graph(
            session, data["subject_metric_revision_id"], data
        )
        expected_definition = (
            subject_identity.metric_code == data["metric_code"]
            and subject_identity.target_period_key == data["target_period_key"]
            and subject_identity.period_basis == data["period_basis"]
            and subject_identity.accounting_scope == data["accounting_scope"]
            and subject_identity.formula_version == data["formula_version"]
        )
        if not expected_definition:
            raise NormalizedMetricError(
                "normalized_comparison_universe_mismatch",
                "subject metric revision does not match the comparison definition",
            )
        if subject_revision.instrument_revision_id != subject_member["instrument_revision_id"]:
            raise NormalizedMetricError(
                "normalized_comparison_universe_mismatch",
                "subject metric revision does not bind the subject member instrument revision",
            )

        for member in data["members"]:
            metric_revision_id = member["metric_revision_id"]
            if metric_revision_id is None:
                continue
            metric_revision, _metric_identity = self._metric_graph(
                session, metric_revision_id, data
            )
            if metric_revision.instrument_revision_id != member["instrument_revision_id"]:
                raise NormalizedMetricError(
                    "normalized_comparison_universe_mismatch",
                    "metric revision does not bind the member's exact instrument revision",
                )

        return super()._record(session, data, dry_run)


__all__ = ("ExactValuationComparisonCommandService",)

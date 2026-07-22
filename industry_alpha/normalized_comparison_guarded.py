"""Identity guard around the normalized valuation comparison command."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price_models import ListedInstrumentRevision
from industry_alpha.normalized_comparison_commands import (
    ValuationComparisonCommandService,
    parse_comparison_command,
)
from industry_alpha.normalized_financial_rules import NormalizedMetricError
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
)


def validate_comparison_manifest_shape(data: dict[str, Any]) -> None:
    """Reject duplicate explicit peer identities before any database write."""

    if data["comparison_kind"] != "peer":
        return
    research_revisions = [
        member["company_research_revision_id"] for member in data["members"]
    ]
    instrument_revisions = [
        member["instrument_revision_id"] for member in data["members"]
    ]
    if len(set(research_revisions)) != len(research_revisions):
        raise NormalizedMetricError(
            "normalized_comparison_universe_mismatch",
            "peer members must use distinct Company Research revisions",
        )
    if len(set(instrument_revisions)) != len(instrument_revisions):
        raise NormalizedMetricError(
            "normalized_comparison_universe_mismatch",
            "peer members must use distinct listed-instrument revisions",
        )


class GuardedValuationComparisonCommandService:
    """Preflight stable peer identities, then delegate the atomic append."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._delegate = ValuationComparisonCommandService(session_factory)

    def record_comparison_set(
        self, raw: dict[str, Any], *, dry_run: bool = False
    ) -> dict[str, Any]:
        data = parse_comparison_command(raw)
        validate_comparison_manifest_shape(data)
        self._validate_stable_identities(data)
        return self._delegate.record_comparison_set(raw, dry_run=dry_run)

    def _validate_stable_identities(self, data: dict[str, Any]) -> None:
        if data["comparison_kind"] != "peer":
            return
        research_identity_ids = []
        instrument_identity_ids = []
        subject_research_id = None
        subject_instrument_id = None
        with self._session_factory() as session:
            for member in data["members"]:
                research_revision = session.get(
                    Stage2CompanyResearchRevision,
                    member["company_research_revision_id"],
                )
                instrument_revision = session.get(
                    ListedInstrumentRevision, member["instrument_revision_id"]
                )
                if research_revision is None or instrument_revision is None:
                    raise NormalizedMetricError(
                        "normalized_comparison_universe_mismatch",
                        "peer identity revision is missing",
                    )
                research = session.get(
                    Stage2CompanyResearch, research_revision.company_research_id
                )
                if research is None:
                    raise NormalizedMetricError(
                        "normalized_comparison_universe_mismatch",
                        "peer Company Research identity is missing",
                    )
                if research.stock_code != instrument_revision.canonical_symbol:
                    raise NormalizedMetricError(
                        "normalized_comparison_universe_mismatch",
                        "peer Company Research stock code does not match the listed instrument",
                    )
                research_identity_ids.append(research.id)
                instrument_identity_ids.append(instrument_revision.instrument_id)
                if member["is_subject"]:
                    subject_research_id = research.id
                    subject_instrument_id = instrument_revision.instrument_id
        if len(set(research_identity_ids)) != len(research_identity_ids):
            raise NormalizedMetricError(
                "normalized_comparison_universe_mismatch",
                "peer members must represent distinct Company Research identities",
            )
        if len(set(instrument_identity_ids)) != len(instrument_identity_ids):
            raise NormalizedMetricError(
                "normalized_comparison_universe_mismatch",
                "peer members must represent distinct listed instruments",
            )
        if subject_research_id != data["subject_company_research_id"]:
            raise NormalizedMetricError(
                "normalized_comparison_universe_mismatch",
                "subject member does not match subject_company_research_id",
            )
        if subject_instrument_id != data["subject_instrument_id"]:
            raise NormalizedMetricError(
                "normalized_comparison_universe_mismatch",
                "subject member does not match subject_instrument_id",
            )

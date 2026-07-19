"""Neutral frozen-boundary mechanics shared by Stage 2 command slices."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerValidationError
from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem
from industry_alpha.stage2_expectations_models import (
    Stage2ExpectationClaimLink,
    Stage2ExpectationEvidenceLink,
    Stage2ExpectationHypothesisLink,
    Stage2MarketExpectation,
    Stage2MarketExpectationRevision,
    Stage2ValuationClaimLink,
    Stage2ValuationEvidenceLink,
    Stage2ValuationHypothesisLink,
    Stage2ValuationSnapshot,
    Stage2ValuationSnapshotRevision,
)
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
    Stage2FinancialHypothesis,
    Stage2FinancialHypothesisRevision,
    Stage2ResearchHypothesisLink,
)
from industry_alpha.validation import (
    utc_timestamp,
    validate_recorded_cutoff,
    validate_utc_chronology,
)


@dataclass(frozen=True)
class Stage2BaseBoundary:
    """Exact accepted v0.6A/v0.6B boundary consumed by later Stage 2 slices."""

    research_revision: Stage2CompanyResearchRevision
    hypotheses: tuple[Stage2FinancialHypothesisRevision, ...]
    expectations: tuple[Stage2MarketExpectationRevision, ...]
    valuations: tuple[Stage2ValuationSnapshotRevision, ...]
    claims: tuple[ClaimRevision, ...]
    evidence: tuple[tuple[ClaimRevision, ClaimEvidenceLink, EvidenceItem], ...]


def build_stage2_base_boundary(
    session: Session,
    research: Stage2CompanyResearch,
    *,
    company_research_revision_id: UUID,
    hypothesis_revision_ids: tuple[UUID, ...],
    expectation_revision_ids: tuple[UUID, ...] = (),
    valuation_revision_ids: tuple[UUID, ...] = (),
    claim_revision_ids: tuple[UUID, ...],
    cutoff: date,
    recorded: datetime,
    **_data: Any,
) -> Stage2BaseBoundary:
    """Load and validate the exact frozen v0.6A/v0.6B boundary."""

    research_revision = session.get(
        Stage2CompanyResearchRevision, company_research_revision_id
    )
    if (
        research_revision is None
        or research_revision.company_research_id != research.id
    ):
        raise EvidenceLedgerValidationError(
            "company_research_revision_id must belong to this company research file."
        )
    visible_upstream(
        research_revision, cutoff, recorded, "company-research revision"
    )

    hypotheses = load_unique(
        session,
        Stage2FinancialHypothesisRevision,
        hypothesis_revision_ids,
        "hypothesis_revision_ids",
        required=True,
    )
    frozen_hypotheses = set(
        session.scalars(
            select(Stage2ResearchHypothesisLink.hypothesis_revision_id).where(
                Stage2ResearchHypothesisLink.company_research_revision_id
                == research_revision.id
            )
        )
    )
    for item in hypotheses:
        identity = session.get(Stage2FinancialHypothesis, item.hypothesis_id)
        if (
            identity is None
            or identity.company_research_id != research.id
            or item.id not in frozen_hypotheses
        ):
            raise EvidenceLedgerValidationError(
                "hypothesis revisions must be frozen by the exact company-research revision."
            )
        if item.hypothesis_status not in {"supported", "disputed"}:
            raise EvidenceLedgerValidationError(
                "assessment hypotheses must be accepted supported or disputed revisions."
            )
        visible_upstream(item, cutoff, recorded, "hypothesis revision")

    expectations = load_unique(
        session,
        Stage2MarketExpectationRevision,
        expectation_revision_ids,
        "expectation_revision_ids",
    )
    valuations = load_unique(
        session,
        Stage2ValuationSnapshotRevision,
        valuation_revision_ids,
        "valuation_revision_ids",
    )
    if not expectations and not valuations:
        raise EvidenceLedgerValidationError(
            "at least one exact v0.6B expectation or valuation revision is required."
        )
    for item in expectations:
        identity = session.get(Stage2MarketExpectation, item.expectation_id)
        if identity is None or identity.company_research_id != research.id:
            raise EvidenceLedgerValidationError(
                "expectation revisions must belong to the same company research file."
            )
        if (
            item.company_research_revision_id != research_revision.id
            or item.status not in {"supported", "disputed"}
        ):
            raise EvidenceLedgerValidationError(
                "expectation revisions must be accepted by the exact company-research boundary."
            )
        visible_upstream(item, cutoff, recorded, "expectation revision")
    for item in valuations:
        identity = session.get(Stage2ValuationSnapshot, item.valuation_id)
        if identity is None or identity.company_research_id != research.id:
            raise EvidenceLedgerValidationError(
                "valuation revisions must belong to the same company research file."
            )
        if (
            item.company_research_revision_id != research_revision.id
            or item.status not in {"supported", "disputed"}
        ):
            raise EvidenceLedgerValidationError(
                "valuation revisions must be accepted by the exact company-research boundary."
            )
        visible_upstream(item, cutoff, recorded, "valuation revision")

    claims = load_unique(
        session,
        ClaimRevision,
        claim_revision_ids,
        "claim_revision_ids",
        required=True,
    )
    upstream_claim_links = (
        list(
            session.scalars(
                select(Stage2ExpectationClaimLink).where(
                    Stage2ExpectationClaimLink.expectation_revision_id.in_(
                        [item.id for item in expectations]
                    )
                )
            )
        )
        if expectations
        else []
    )
    if valuations:
        upstream_claim_links.extend(
            session.scalars(
                select(Stage2ValuationClaimLink).where(
                    Stage2ValuationClaimLink.valuation_revision_id.in_(
                        [item.id for item in valuations]
                    )
                )
            )
        )
    for link in upstream_claim_links:
        validate_utc_chronology(
            recorded,
            ("v0.6B claim boundary timestamp", stored_utc(link.recorded_at_utc)),
        )
    upstream_claim_ids = {link.claim_revision_id for link in upstream_claim_links}

    evidence_boundaries: list[Any] = []
    if expectations:
        evidence_boundaries.extend(
            session.scalars(
                select(Stage2ExpectationEvidenceLink).where(
                    Stage2ExpectationEvidenceLink.expectation_revision_id.in_(
                        [item.id for item in expectations]
                    )
                )
            )
        )
    if valuations:
        evidence_boundaries.extend(
            session.scalars(
                select(Stage2ValuationEvidenceLink).where(
                    Stage2ValuationEvidenceLink.valuation_revision_id.in_(
                        [item.id for item in valuations]
                    )
                )
            )
        )
    for boundary in evidence_boundaries:
        validate_utc_chronology(
            recorded,
            (
                "v0.6B evidence boundary timestamp",
                stored_utc(boundary.recorded_at_utc),
            ),
        )

    evidence: list[tuple[ClaimRevision, ClaimEvidenceLink, EvidenceItem]] = []
    for claim in claims:
        identity = session.get(Claim, claim.claim_id)
        if (
            identity is None
            or identity.case_id != research.case_id
            or claim.id not in upstream_claim_ids
        ):
            raise EvidenceLedgerValidationError(
                "claim revisions must belong to the research case and exact frozen v0.6B boundary."
            )
        visible_upstream(claim, cutoff, recorded, "claim revision")
        for boundary in evidence_boundaries:
            if boundary.claim_revision_id != claim.id:
                continue
            link = session.get(ClaimEvidenceLink, boundary.claim_evidence_link_id)
            item = session.get(EvidenceItem, boundary.evidence_id)
            if (
                link is None
                or item is None
                or link.claim_revision_id != claim.id
                or link.evidence_id != item.id
            ):
                raise EvidenceLedgerValidationError(
                    "frozen evidence link is inconsistent."
                )
            if (
                item.information_date <= cutoff
                and stored_utc(link.recorded_at_utc) <= recorded
                and stored_utc(item.recorded_at_utc) <= recorded
            ):
                evidence.append((claim, link, item))

    hypothesis_ids = {item.id for item in hypotheses}
    upstream_hypothesis_links: list[Any] = []
    if expectations:
        upstream_hypothesis_links.extend(
            session.scalars(
                select(Stage2ExpectationHypothesisLink).where(
                    Stage2ExpectationHypothesisLink.expectation_revision_id.in_(
                        [item.id for item in expectations]
                    )
                )
            )
        )
    if valuations:
        upstream_hypothesis_links.extend(
            session.scalars(
                select(Stage2ValuationHypothesisLink).where(
                    Stage2ValuationHypothesisLink.valuation_revision_id.in_(
                        [item.id for item in valuations]
                    )
                )
            )
        )
    for link in upstream_hypothesis_links:
        validate_utc_chronology(
            recorded,
            (
                "v0.6B hypothesis boundary timestamp",
                stored_utc(link.recorded_at_utc),
            ),
        )
    upstream_hypothesis_ids = {
        link.hypothesis_revision_id for link in upstream_hypothesis_links
    }
    if hypothesis_ids != upstream_hypothesis_ids:
        raise EvidenceLedgerValidationError(
            "assessment hypotheses must exactly match the selected v0.6B frozen boundary."
        )

    unique_evidence = {row[1].id: row for row in evidence}
    return Stage2BaseBoundary(
        research_revision,
        tuple(hypotheses),
        tuple(expectations),
        tuple(valuations),
        tuple(claims),
        tuple(unique_evidence[key] for key in sorted(unique_evidence, key=str)),
    )


def load_unique(
    session: Session,
    model: type[Any],
    ids: tuple[UUID, ...],
    field: str,
    *,
    required: bool = False,
) -> list[Any]:
    """Load an exact tuple of unique rows under the current transaction lock."""

    if not isinstance(ids, tuple) or len(ids) != len(set(ids)) or (required and not ids):
        suffix = "non-empty and unique" if required else "unique"
        raise EvidenceLedgerValidationError(
            f"{field} must be a tuple of {suffix} identifiers."
        )
    if not ids:
        return []
    rows = list(
        session.scalars(
            select(model).where(model.id.in_(ids)).order_by(model.id).with_for_update()
        )
    )
    if len(rows) != len(ids):
        raise EvidenceLedgerNotFound(f"one or more {field} were not found.")
    return rows


def visible_upstream(
    row: Any, cutoff: date, recorded: datetime, label: str
) -> None:
    """Enforce the existing cutoff and recorded-time visibility boundary."""

    if row.information_cutoff_date > cutoff:
        raise EvidenceLedgerValidationError(
            f"{label} cutoff exceeds assessment cutoff."
        )
    validate_utc_chronology(
        recorded, (f"{label} timestamp", stored_utc(row.recorded_at_utc))
    )


def time_boundary(data: dict[str, Any]) -> tuple[datetime, date]:
    """Normalize and validate the command cutoff/recorded pair."""

    cutoff = data.get("information_cutoff_date")
    if not isinstance(cutoff, date) or isinstance(cutoff, datetime):
        raise EvidenceLedgerValidationError(
            "information_cutoff_date must be a date."
        )
    recorded = utc_timestamp(data.get("recorded_at_utc"))
    validate_recorded_cutoff(cutoff, recorded)
    return recorded, cutoff


def lock_company_research(
    session: Session, identity: UUID
) -> Stage2CompanyResearch:
    """Lock and return one Stage 2 company-research identity."""

    row = session.scalar(
        select(Stage2CompanyResearch)
        .where(Stage2CompanyResearch.id == identity)
        .with_for_update()
    )
    if row is None:
        raise EvidenceLedgerNotFound(
            f"Stage 2 company research {identity} was not found."
        )
    return row


def required_text(value: str, field: str, maximum: int) -> str:
    """Preserve the current shared non-empty bounded text validation."""

    if not isinstance(value, str):
        raise EvidenceLedgerValidationError(f"{field} must be a string.")
    normalized = value.strip()
    if not normalized:
        raise EvidenceLedgerValidationError(f"{field} must not be blank.")
    if len(normalized) > maximum:
        raise EvidenceLedgerValidationError(
            f"{field} must not exceed {maximum} characters."
        )
    return normalized


def stored_utc(value: datetime | None) -> datetime:
    """Normalize a stored timestamp to aware UTC without changing semantics."""

    if value is None:
        raise EvidenceLedgerValidationError("required UTC timestamp is missing.")
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

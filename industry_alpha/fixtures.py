"""Deterministic, offline evidence-ledger fixture."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from industry_alpha.commands import (
    CaseClaimInput,
    EvidenceLedgerCommandService,
    EvidenceLinkInput,
    VerificationInput,
)
from industry_alpha.models import ClaimRevision
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker


def _recorded(day: int) -> datetime:
    return datetime(2026, 6, day, 9, 0, tzinfo=timezone.utc)


def build_evidence_ledger_fixture(session_factory: sessionmaker[Session]) -> UUID:
    """Create one bounded case with support, a lead, conflict, and checklist."""
    commands = EvidenceLedgerCommandService(session_factory)
    case = commands.create_case(
        case_key="fixture-industry-evidence-ledger",
        title="Fixture industry evidence review",
        research_question="What can the attributable fixture evidence establish?",
        summary="Initial evidence collection without an investment conclusion.",
        workflow_state="open",
        conclusion_status="unassessed",
        information_cutoff_date=date(2026, 6, 5),
        origin="fixture",
        recorded_at_utc=_recorded(5),
    )
    primary = commands.add_evidence(
        case.id,
        evidence_grade="A",
        source_kind="official",
        source_title="Fixture regulatory publication",
        publisher_or_author="Fixture authority",
        source_locator="fixture://official/publication",
        information_date=date(2026, 6, 4),
        summary="The publication states one bounded factual observation.",
        content_fingerprint="fixture-primary-v1",
        recorded_at_utc=_recorded(5),
    )
    secondary = commands.add_evidence(
        case.id,
        evidence_grade="B",
        source_kind="research",
        source_title="Fixture attributable industry study",
        publisher_or_author="Fixture research publisher",
        information_date=date(2026, 6, 6),
        summary="The study provides a discernible method for a bounded inference.",
        content_fingerprint="fixture-secondary-v1",
        recorded_at_utc=_recorded(6),
    )
    lead = commands.add_evidence(
        case.id,
        evidence_grade="D",
        source_kind="community",
        source_title="Fixture unverified community lead",
        information_date=date(2026, 6, 6),
        summary="An unverified lead retained for visibility, not factual support.",
        content_fingerprint="fixture-lead-v1",
        recorded_at_utc=_recorded(6),
    )
    contradiction = commands.add_evidence(
        case.id,
        evidence_grade="C",
        source_kind="media",
        source_title="Fixture attributable contradictory context",
        publisher_or_author="Fixture publisher",
        information_date=date(2026, 6, 9),
        summary="Attributable context contradicts the current inference.",
        content_fingerprint="fixture-contradiction-v1",
        recorded_at_utc=_recorded(10),
    )
    commands.create_claim(
        case.id,
        claim_key="fixture-fact",
        statement="The fixture publication contains the bounded observation.",
        claim_kind="fact",
        claim_status="supported",
        information_cutoff_date=date(2026, 6, 5),
        evidence_links=(EvidenceLinkInput(primary.id, "supports"),),
        recorded_at_utc=_recorded(5),
    )
    inference = commands.create_claim(
        case.id,
        claim_key="fixture-inference",
        statement="The evidence may imply a change requiring further verification.",
        claim_kind="inference",
        claim_status="draft",
        inference_confidence="low",
        inference_basis="One attributable study plus an unverified lead.",
        information_cutoff_date=date(2026, 6, 6),
        evidence_links=(
            EvidenceLinkInput(secondary.id, "supports"),
            EvidenceLinkInput(lead.id, "context", "D-grade lead retained as context only."),
        ),
        recorded_at_utc=_recorded(6),
    )
    disputed = commands.append_claim_revision(
        inference.id,
        statement="The bounded inference remains disputed pending primary verification.",
        claim_kind="inference",
        claim_status="disputed",
        inference_confidence="low",
        inference_basis="Attributable supporting and contradictory material coexist.",
        information_cutoff_date=date(2026, 6, 10),
        evidence_links=(
            EvidenceLinkInput(secondary.id, "supports"),
            EvidenceLinkInput(contradiction.id, "contradicts"),
            EvidenceLinkInput(lead.id, "context"),
        ),
        recorded_at_utc=_recorded(10),
    )
    commands.append_case_revision(
        case.id,
        title="Completed fixture evidence review",
        research_question="What can the attributable fixture evidence establish?",
        summary="Conflicting evidence remains explicit; no recommendation is produced.",
        workflow_state="completed",
        conclusion_status="disputed",
        information_cutoff_date=date(2026, 6, 10),
        claim_links=(CaseClaimInput(disputed.id, "conclusion"),),
        verification_items=(
            VerificationInput(
                "Obtain primary evidence that resolves the contradictory context.",
                status="open",
                due_date=date(2026, 7, 10),
            ),
        ),
        recorded_at_utc=_recorded(10),
    )
    with session_factory() as session:
        assert session.scalar(
            select(ClaimRevision).where(ClaimRevision.id == disputed.id)
        ) is not None
    return case.id

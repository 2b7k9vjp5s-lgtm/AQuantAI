from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.api.industry_alpha import get_industry_alpha_session_factory
from backend.database.engine import build_session_factory
from backend.database.models import Base
from backend.main import app
from industry_alpha.commands import (
    CaseClaimInput,
    EvidenceLedgerCommandService,
    EvidenceLinkInput,
    VerificationInput,
)
from industry_alpha.errors import (
    EvidenceLedgerConflictError,
    EvidenceLedgerImmutableError,
    EvidenceLedgerValidationError,
)
from industry_alpha.models import (
    CaseRevisionClaimLink,
    Claim,
    ClaimEvidenceLink,
    ClaimRevision,
    EvidenceItem,
    ResearchCase,
    ResearchCaseRevision,
    VerificationItem,
)
from industry_alpha.query import EvidenceLedgerQueryService
from industry_alpha.repository import EvidenceLedgerRepository


def utc(day: int) -> datetime:
    return datetime(2026, 1, day, 12, tzinfo=timezone.utc)


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    yield factory
    engine.dispose()


def create_case(service: EvidenceLedgerCommandService, key: str = "case-one"):
    return service.create_case(
        case_key=key,
        title="Reviewed industry research case",
        research_question="What evidence is available?",
        information_cutoff_date=date(2026, 1, 2),
        recorded_at_utc=utc(2),
    )


def add_evidence(
    service: EvidenceLedgerCommandService,
    case_id,
    grade: str,
    day: int,
    *,
    fingerprint: str | None = None,
):
    return service.add_evidence(
        case_id,
        evidence_grade=grade,
        source_kind="official" if grade == "A" else "research",
        source_title=f"Evidence {grade}-{day}",
        information_date=date(2026, 1, day),
        summary="Attributable fixture evidence.",
        content_fingerprint=fingerprint,
        recorded_at_utc=utc(day),
    )


def test_case_creation_separates_workflow_and_conclusion(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)
    with session_factory() as session:
        revision = session.scalar(select(ResearchCaseRevision))
        assert case.case_key == "case-one"
        assert revision.revision_no == 1
        assert revision.workflow_state == "open"
        assert revision.conclusion_status == "unassessed"


def test_case_revision_number_and_supersedes_are_deterministic(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)
    second = service.append_case_revision(
        case.id,
        title="Second",
        research_question="Still reviewing?",
        information_cutoff_date=date(2026, 1, 3),
        workflow_state="paused",
        conclusion_status="insufficient_evidence",
        recorded_at_utc=utc(3),
    )
    with session_factory() as session:
        first = session.scalar(
            select(ResearchCaseRevision).where(ResearchCaseRevision.revision_no == 1)
        )
        assert second.revision_no == 2
        assert second.supersedes_revision_id == first.id


def test_accepted_rows_reject_update_and_delete_and_rollback(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)
    with session_factory() as session:
        row = session.get(ResearchCase, case.id)
        row.case_key = "changed"
        with pytest.raises(EvidenceLedgerImmutableError):
            session.commit()
        session.rollback()
        row = session.get(ResearchCase, case.id)
        session.delete(row)
        with pytest.raises(EvidenceLedgerImmutableError):
            session.commit()
        session.rollback()
    with session_factory() as session:
        assert session.get(ResearchCase, case.id).case_key == "case-one"


@pytest.mark.parametrize("grade", ["A", "B", "C", "D"])
def test_reviewed_evidence_grades_are_accepted(session_factory, grade):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)
    assert add_evidence(service, case.id, grade, 3).evidence_grade == grade


def test_invalid_grade_and_duplicate_fingerprint_roll_back(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)
    with pytest.raises(EvidenceLedgerValidationError):
        add_evidence(service, case.id, "E", 3)
    add_evidence(service, case.id, "A", 3, fingerprint="same-content")
    with pytest.raises(EvidenceLedgerConflictError):
        add_evidence(service, case.id, "B", 4, fingerprint="same-content")
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(EvidenceItem)) == 1


def test_fact_and_inference_fields_are_strict(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)
    with pytest.raises(EvidenceLedgerValidationError, match="fact claims"):
        service.create_claim(
            case.id,
            claim_key="fact",
            statement="A fact.",
            claim_kind="fact",
            claim_status="draft",
            inference_confidence="high",
            information_cutoff_date=date(2026, 1, 3),
            recorded_at_utc=utc(3),
        )
    with pytest.raises(EvidenceLedgerValidationError, match="require inference_confidence"):
        service.create_claim(
            case.id,
            claim_key="inference",
            statement="An inference.",
            claim_kind="inference",
            claim_status="draft",
            information_cutoff_date=date(2026, 1, 3),
            recorded_at_utc=utc(3),
        )
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Claim)) == 0


def test_supported_claim_requires_abc_and_rejects_d_only(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)
    d = add_evidence(service, case.id, "D", 3)
    with pytest.raises(EvidenceLedgerValidationError, match="D-only"):
        service.create_claim(
            case.id,
            claim_key="lead",
            statement="Unverified lead.",
            claim_kind="fact",
            claim_status="supported",
            information_cutoff_date=date(2026, 1, 3),
            evidence_links=(EvidenceLinkInput(d.id, "supports"),),
            recorded_at_utc=utc(3),
        )
    a = add_evidence(service, case.id, "A", 3)
    claim = service.create_claim(
        case.id,
        claim_key="supported-fact",
        statement="The filing states the reviewed fact.",
        claim_kind="fact",
        claim_status="supported",
        information_cutoff_date=date(2026, 1, 3),
        evidence_links=(EvidenceLinkInput(a.id, "supports"),),
        recorded_at_utc=utc(3),
    )
    with session_factory() as session:
        revision = session.scalar(select(ClaimRevision).where(ClaimRevision.claim_id == claim.id))
        assert revision.claim_status == "supported"


def test_conflict_blocks_supported_and_disputed_requires_conflict(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)
    a = add_evidence(service, case.id, "A", 3)
    c = add_evidence(service, case.id, "C", 4)
    with pytest.raises(EvidenceLedgerValidationError, match="contradictory"):
        service.create_claim(
            case.id,
            claim_key="conflicted",
            statement="Conflicted fact.",
            claim_kind="fact",
            claim_status="supported",
            information_cutoff_date=date(2026, 1, 4),
            evidence_links=(
                EvidenceLinkInput(a.id, "supports"),
                EvidenceLinkInput(c.id, "contradicts"),
            ),
            recorded_at_utc=utc(4),
        )
    with pytest.raises(EvidenceLedgerValidationError, match="require contradictory"):
        service.create_claim(
            case.id,
            claim_key="not-disputed",
            statement="No conflict attached.",
            claim_kind="fact",
            claim_status="disputed",
            information_cutoff_date=date(2026, 1, 4),
            evidence_links=(EvidenceLinkInput(a.id, "supports"),),
            recorded_at_utc=utc(4),
        )


def test_cross_case_links_rejected_without_partial_claim(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    first = create_case(service, "first")
    second = create_case(service, "second")
    evidence = add_evidence(service, second.id, "A", 3)
    with pytest.raises(EvidenceLedgerValidationError, match="same case"):
        service.create_claim(
            first.id,
            claim_key="cross-case",
            statement="Invalid relation.",
            claim_kind="fact",
            claim_status="supported",
            information_cutoff_date=date(2026, 1, 3),
            evidence_links=(EvidenceLinkInput(evidence.id, "supports"),),
            recorded_at_utc=utc(3),
        )
    with session_factory() as session:
        assert session.scalar(select(func.count()).select_from(Claim)) == 0


def test_links_and_frozen_membership_respect_information_cutoffs(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)
    later_evidence = add_evidence(service, case.id, "A", 5)
    claim = service.create_claim(
        case.id,
        claim_key="cutoff-boundary",
        statement="Draft before later evidence.",
        claim_kind="fact",
        claim_status="draft",
        information_cutoff_date=date(2026, 1, 4),
        recorded_at_utc=utc(4),
    )
    with session_factory() as session:
        claim_revision = session.scalar(
            select(ClaimRevision).where(ClaimRevision.claim_id == claim.id)
        )
    with pytest.raises(EvidenceLedgerValidationError, match="exceeds the claim"):
        service.link_evidence(
            claim_revision.id,
            later_evidence.id,
            relation="context",
            recorded_at_utc=utc(5),
        )
    with pytest.raises(EvidenceLedgerValidationError, match="exceeds the case"):
        service.append_case_revision(
            case.id,
            title="Invalid frozen membership",
            research_question="Can later claims leak?",
            information_cutoff_date=date(2026, 1, 3),
            claim_links=(CaseClaimInput(claim_revision.id, "context"),),
            recorded_at_utc=utc(5),
        )


def test_supported_case_freezes_exact_supported_claim_revision(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)
    evidence = add_evidence(service, case.id, "B", 3)
    claim = service.create_claim(
        case.id,
        claim_key="conclusion",
        statement="Supported inference.",
        claim_kind="inference",
        claim_status="supported",
        inference_confidence="medium",
        inference_basis="Bounded fixture basis.",
        information_cutoff_date=date(2026, 1, 3),
        evidence_links=(EvidenceLinkInput(evidence.id, "supports"),),
        recorded_at_utc=utc(3),
    )
    with session_factory() as session:
        claim_revision = session.scalar(select(ClaimRevision).where(ClaimRevision.claim_id == claim.id))
    case_revision = service.append_case_revision(
        case.id,
        title="Supported record",
        research_question="What does reviewed evidence support?",
        information_cutoff_date=date(2026, 1, 4),
        conclusion_status="supported",
        claim_links=(CaseClaimInput(claim_revision.id, "conclusion"),),
        recorded_at_utc=utc(4),
    )
    with session_factory() as session:
        frozen = session.scalar(
            select(CaseRevisionClaimLink).where(
                CaseRevisionClaimLink.case_revision_id == case_revision.id
            )
        )
        assert frozen.claim_revision_id == claim_revision.id


def test_disputed_case_and_completed_checklist_rules(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)
    contradiction = add_evidence(service, case.id, "C", 3)
    claim = service.create_claim(
        case.id,
        claim_key="disputed",
        statement="Disputed inference.",
        claim_kind="inference",
        claim_status="disputed",
        inference_confidence="low",
        inference_basis="Conflicting attributable evidence.",
        information_cutoff_date=date(2026, 1, 3),
        evidence_links=(EvidenceLinkInput(contradiction.id, "contradicts"),),
        recorded_at_utc=utc(3),
    )
    with session_factory() as session:
        claim_revision = session.scalar(select(ClaimRevision).where(ClaimRevision.claim_id == claim.id))
    with pytest.raises(EvidenceLedgerValidationError, match="后续验证清单"):
        service.append_case_revision(
            case.id,
            title="Incomplete completion",
            research_question="What remains?",
            information_cutoff_date=date(2026, 1, 4),
            workflow_state="completed",
            conclusion_status="disputed",
            claim_links=(CaseClaimInput(claim_revision.id, "conclusion"),),
            recorded_at_utc=utc(4),
        )
    revision = service.append_case_revision(
        case.id,
        title="Completed ledger review",
        research_question="What remains?",
        information_cutoff_date=date(2026, 1, 4),
        workflow_state="completed",
        conclusion_status="disputed",
        claim_links=(CaseClaimInput(claim_revision.id, "conclusion"),),
        verification_items=(
            VerificationInput("Verify the conflict with a later filing."),
            VerificationInput("Revisit the inference.", status="deferred"),
        ),
        recorded_at_utc=utc(4),
    )
    with session_factory() as session:
        items = list(
            session.scalars(
                select(VerificationItem)
                .where(VerificationItem.case_revision_id == revision.id)
                .order_by(VerificationItem.item_no)
            )
        )
        assert [item.item_no for item in items] == [1, 2]


def test_verification_items_append_with_deterministic_numbers(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)
    with session_factory() as session:
        revision = session.scalar(
            select(ResearchCaseRevision).where(ResearchCaseRevision.case_id == case.id)
        )
    first = service.add_verification_item(
        revision.id,
        description="Verify the first bounded question.",
        recorded_at_utc=utc(3),
    )
    second = service.add_verification_item(
        revision.id,
        description="Verify the second bounded question.",
        status="deferred",
        recorded_at_utc=utc(4),
    )
    assert (first.item_no, second.item_no) == (1, 2)


def test_cutoff_excludes_later_backfilled_evidence_links_conflicts_and_checklist(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)
    early = add_evidence(service, case.id, "A", 3)
    claim = service.create_claim(
        case.id,
        claim_key="fact",
        statement="Early supported fact.",
        claim_kind="fact",
        claim_status="supported",
        information_cutoff_date=date(2026, 1, 3),
        evidence_links=(EvidenceLinkInput(early.id, "supports"),),
        recorded_at_utc=utc(3),
    )
    late_backfill = service.add_evidence(
        case.id,
        evidence_grade="C",
        source_kind="research",
        source_title="Old information recorded later",
        information_date=date(2026, 1, 2),
        summary="Backfilled contradictory evidence.",
        recorded_at_utc=utc(8),
    )
    disputed = service.append_claim_revision(
        claim.id,
        statement="Fact is now disputed.",
        claim_kind="fact",
        claim_status="disputed",
        information_cutoff_date=date(2026, 1, 8),
        evidence_links=(EvidenceLinkInput(late_backfill.id, "contradicts"),),
        recorded_at_utc=utc(8),
    )
    service.append_case_revision(
        case.id,
        title="Completed disputed review",
        research_question="What changed?",
        information_cutoff_date=date(2026, 1, 8),
        workflow_state="completed",
        conclusion_status="disputed",
        claim_links=(CaseClaimInput(disputed.id, "conclusion"),),
        verification_items=(VerificationInput("Obtain a primary-source clarification."),),
        recorded_at_utc=utc(8),
    )
    with session_factory() as session:
        query = EvidenceLedgerQueryService(EvidenceLedgerRepository(session))
        historical = query.get_case(
            case.id, as_of_cutoff=date(2026, 1, 5)
        ).to_dict()
        current = query.get_case(case.id).to_dict()
    assert historical["latest_revision"]["revision_no"] == 1
    assert len(historical["evidence_items"]) == 1
    assert historical["conflicts"] == []
    assert historical["verification_items"] == []
    assert historical["claims"][0]["current_revision"]["claim_status"] == "supported"
    assert current["latest_revision"]["revision_no"] == 2
    assert len(current["evidence_items"]) == 2
    assert len(current["conflicts"]) == 1
    assert current["label_metadata"]["verification_items"] == "后续验证清单"
    json.dumps(current, allow_nan=False)


def test_query_order_is_deterministic(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    b = create_case(service, "b-case")
    a = create_case(service, "a-case")
    add_evidence(service, a.id, "B", 4)
    add_evidence(service, a.id, "A", 3)
    with session_factory() as session:
        query = EvidenceLedgerQueryService(EvidenceLedgerRepository(session))
        first = query.list_cases().to_dict()
        second = query.list_cases().to_dict()
        detail = query.get_case(a.id).to_dict()
    assert [item["case_key"] for item in first["cases"]] == ["a-case", "b-case"]
    assert first == second
    assert [item["evidence_grade"] for item in detail["evidence_items"]] == ["A", "B"]
    assert b.id != a.id


def test_read_only_api_success_errors_and_no_mutation_routes(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)
    app.dependency_overrides[get_industry_alpha_session_factory] = lambda: session_factory
    try:
        client = TestClient(app)
        listed = client.get("/industry-alpha/cases")
        detail = client.get(f"/industry-alpha/cases/{case.id}")
        assert listed.status_code == 200
        assert listed.json()["case_count"] == 1
        assert detail.status_code == 200
        assert detail.json()["notices"]["read_only"] is True
        assert client.get("/industry-alpha/cases?as_of_cutoff=bad").status_code == 422
        assert client.get(f"/industry-alpha/cases/{uuid4()}").status_code == 404
        assert client.get(
            f"/industry-alpha/cases/{case.id}?as_of_cutoff=2026-01-01"
        ).status_code == 404
        assert client.post("/industry-alpha/cases", json={}).status_code == 405
        for method in (client.put, client.patch, client.delete):
            assert method(f"/industry-alpha/cases/{case.id}").status_code == 405
    finally:
        app.dependency_overrides.clear()


def test_same_case_concurrent_revision_numbers_are_unique(session_factory):
    service = EvidenceLedgerCommandService(session_factory)
    case = create_case(service)

    def append(number: int) -> int:
        return service.append_case_revision(
            case.id,
            title=f"Concurrent {number}",
            research_question="Concurrency test",
            information_cutoff_date=date(2026, 1, 3),
            recorded_at_utc=utc(3),
        ).revision_no

    with ThreadPoolExecutor(max_workers=2) as pool:
        numbers = sorted(pool.map(append, [1, 2]))
    assert numbers == [2, 3]

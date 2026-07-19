"""Deterministic offline fixture for Stage 1 beneficiary classifications."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.database.models import IngestionRun, StockBasicRecord
from industry_alpha.chain_map_fixtures import build_industry_chain_map_fixture
from industry_alpha.chain_map_models import (
    IndustryMap,
    IndustryMapNode,
    IndustryMapNodeRevision,
    IndustryMapObservation,
    IndustryMapObservationRevision,
    IndustryMapRelationship,
    IndustryMapRelationshipRevision,
    IndustryMapRevision,
)
from industry_alpha.commands import EvidenceLedgerCommandService, EvidenceLinkInput
from industry_alpha.models import Claim, ClaimRevision
from industry_alpha.stage1_commands import (
    MapAssertionRevisionInput,
    Stage1BeneficiaryCommandService,
)
from industry_alpha.stage1_models import Stage1BeneficiaryRevision


@dataclass(frozen=True)
class Stage1FixtureIds:
    map_id: UUID
    direct_beneficiary_id: UUID
    secondary_beneficiary_id: UUID
    draft_beneficiary_id: UUID
    disputed_beneficiary_id: UUID
    candidate_pool_id: UUID


def _recorded(day: int, hour: int = 10) -> datetime:
    return datetime(2026, 7, day, hour, tzinfo=timezone.utc)


def build_stage1_beneficiary_fixture(
    session_factory: sessionmaker[Session],
) -> Stage1FixtureIds:
    map_id = build_industry_chain_map_fixture(session_factory)
    with session_factory() as session:
        industry_map_revision = session.scalar(
            select(IndustryMapRevision)
            .where(IndustryMapRevision.map_id == map_id)
            .order_by(IndustryMapRevision.revision_no.desc())
        )
        industry_map = session.get(IndustryMap, map_id)
        case_id = industry_map.case_id
    stock_records = _create_company_snapshot(session_factory)
    claims = _create_company_claims(session_factory, case_id)
    assertions = _fixture_assertions(session_factory, map_id)
    commands = Stage1BeneficiaryCommandService(session_factory)

    direct = commands.create_beneficiary(
        case_id,
        map_id,
        source="fixture",
        stock_code="000001",
        selected_map_revision_id=industry_map_revision.id,
        stock_basic_record_id=stock_records["000001"].id,
        beneficiary_kind="direct",
        assessment_status="supported",
        rationale_summary="Exact attributable evidence supports a direct Stage 1 classification.",
        information_cutoff_date=date(2026, 7, 7),
        assertion_revisions=(assertions["upstream"],),
        claim_revision_ids=(claims["direct"].id,),
        recorded_at_utc=_recorded(7),
    )
    secondary = commands.create_beneficiary(
        case_id,
        map_id,
        source="fixture",
        stock_code="000002",
        selected_map_revision_id=industry_map_revision.id,
        stock_basic_record_id=stock_records["000002"].id,
        beneficiary_kind="secondary",
        assessment_status="supported",
        rationale_summary="Exact attributable evidence supports a secondary classification.",
        information_cutoff_date=date(2026, 7, 7),
        assertion_revisions=(assertions["relationship"],),
        claim_revision_ids=(claims["secondary"].id,),
        recorded_at_utc=_recorded(7),
    )
    draft = commands.create_beneficiary(
        case_id,
        map_id,
        source="fixture",
        stock_code="000003",
        selected_map_revision_id=industry_map_revision.id,
        stock_basic_record_id=stock_records["000003"].id,
        beneficiary_kind="potential",
        assessment_status="draft",
        rationale_summary="D-grade context is retained only as an unverified lead.",
        information_cutoff_date=date(2026, 7, 7),
        assertion_revisions=(assertions["value_pool"],),
        claim_revision_ids=(claims["draft"].id,),
        recorded_at_utc=_recorded(7),
    )
    disputed = commands.create_beneficiary(
        case_id,
        map_id,
        source="fixture",
        stock_code="000004",
        selected_map_revision_id=industry_map_revision.id,
        stock_basic_record_id=stock_records["000004"].id,
        beneficiary_kind="potential",
        assessment_status="disputed",
        rationale_summary="Attributable supporting and contradictory evidence coexist.",
        information_cutoff_date=date(2026, 7, 7),
        assertion_revisions=(assertions["bottleneck"],),
        claim_revision_ids=(claims["disputed"].id,),
        recorded_at_utc=_recorded(7),
    )
    direct_revision = _beneficiary_revision(session_factory, direct.id)
    secondary_revision = _beneficiary_revision(session_factory, secondary.id)
    pool = commands.create_candidate_pool(
        case_id,
        map_id,
        pool_key="fixture-stage2-handoff",
        selected_map_revision_id=industry_map_revision.id,
        title="Fixture unranked Stage 2 candidate handoff",
        scope="Only exact supported Stage 1 revisions; no scores, weights, or rank.",
        information_cutoff_date=date(2026, 7, 8),
        beneficiary_revision_ids=(direct_revision.id, secondary_revision.id),
        recorded_at_utc=_recorded(8),
    )
    commands.append_beneficiary_revision(
        direct.id,
        selected_map_revision_id=industry_map_revision.id,
        stock_basic_record_id=stock_records["000001"].id,
        beneficiary_kind="potential",
        assessment_status="supported",
        rationale_summary="A later append-only revision updates the descriptive classification.",
        information_cutoff_date=date(2026, 7, 9),
        assertion_revisions=(assertions["upstream"],),
        claim_revision_ids=(claims["direct"].id,),
        recorded_at_utc=_recorded(9),
    )
    return Stage1FixtureIds(
        map_id=map_id,
        direct_beneficiary_id=direct.id,
        secondary_beneficiary_id=secondary.id,
        draft_beneficiary_id=draft.id,
        disputed_beneficiary_id=disputed.id,
        candidate_pool_id=pool.id,
    )


def _create_company_snapshot(
    session_factory: sessionmaker[Session],
) -> dict[str, StockBasicRecord]:
    with session_factory.begin() as session:
        run = IngestionRun(
            batch_identifier="stage1-fixture-company-snapshot",
            series_key="1" * 64,
            series_identity={"fixture": "stage1-company-snapshot"},
            provider="fixture",
            dataset="stock_basic",
            imported_at=_recorded(6, 8),
            completed_at=_recorded(6, 9),
            requested_start_date=date(2026, 7, 1),
            requested_end_date=date(2026, 7, 6),
            information_cutoff_date=date(2026, 7, 6),
            requested_scope={"stock_codes": ["000001", "000002", "000003", "000004"]},
            provider_request_metadata={"network_access": False},
            adapter_version="stage1-fixture-v1",
            snapshot_mode="complete",
            contract_version="normalized-v1",
            status="succeeded",
            row_count_received=4,
            row_count_written=4,
            dataset_counts={"stock_basic": 4},
        )
        session.add(run)
        session.flush()
        rows = {}
        for code, name, exchange in (
            ("000001", "Fixture Direct Co", "SZSE"),
            ("000002", "Fixture Secondary Co", "SZSE"),
            ("000003", "Fixture Draft Co", "SZSE"),
            ("000004", "Fixture Disputed Co", "SZSE"),
        ):
            row = StockBasicRecord(
                ingestion_run_id=run.id,
                stock_code=code,
                stock_name=name,
                exchange=exchange,
                industry="Fixture industry",
                listing_date=date(2020, 1, 1),
                status="listed",
                source="fixture",
            )
            session.add(row)
            rows[code] = row
        session.flush()
    return rows


def _create_company_claims(
    session_factory: sessionmaker[Session], case_id: UUID
) -> dict[str, ClaimRevision]:
    ledger = EvidenceLedgerCommandService(session_factory)
    primary = ledger.add_evidence(
        case_id,
        evidence_grade="A",
        source_kind="official",
        source_title="Fixture attributable company disclosure",
        information_date=date(2026, 7, 6),
        summary="Exact fixture evidence for a direct beneficiary classification.",
        content_fingerprint="stage1-direct-primary",
        recorded_at_utc=_recorded(6),
    )
    study = ledger.add_evidence(
        case_id,
        evidence_grade="B",
        source_kind="research",
        source_title="Fixture attributable company study",
        information_date=date(2026, 7, 6),
        summary="Exact fixture evidence for a secondary classification.",
        content_fingerprint="stage1-secondary-study",
        recorded_at_utc=_recorded(6),
    )
    lead = ledger.add_evidence(
        case_id,
        evidence_grade="D",
        source_kind="community",
        source_title="Fixture unverified company lead",
        information_date=date(2026, 7, 6),
        summary="Unverified lead retained without promotion.",
        content_fingerprint="stage1-draft-lead",
        recorded_at_utc=_recorded(6),
    )
    conflict = ledger.add_evidence(
        case_id,
        evidence_grade="C",
        source_kind="industry",
        source_title="Fixture contradictory company evidence",
        information_date=date(2026, 7, 6),
        summary="Attributable evidence contradicts the beneficiary inference.",
        content_fingerprint="stage1-disputed-conflict",
        recorded_at_utc=_recorded(6),
    )
    direct = ledger.create_claim(
        case_id,
        claim_key="stage1-fixture-direct",
        statement="Fixture Direct Co has an evidence-backed direct classification.",
        claim_kind="fact",
        claim_status="supported",
        information_cutoff_date=date(2026, 7, 6),
        evidence_links=(EvidenceLinkInput(primary.id, "supports"),),
        recorded_at_utc=_recorded(6),
    )
    secondary = ledger.create_claim(
        case_id,
        claim_key="stage1-fixture-secondary",
        statement="Fixture Secondary Co has an evidence-backed secondary classification.",
        claim_kind="inference",
        claim_status="supported",
        inference_confidence="medium",
        inference_basis="One attributable fixture study supports this bounded classification.",
        information_cutoff_date=date(2026, 7, 6),
        evidence_links=(EvidenceLinkInput(study.id, "supports"),),
        recorded_at_utc=_recorded(6),
    )
    draft = ledger.create_claim(
        case_id,
        claim_key="stage1-fixture-draft",
        statement="Fixture Draft Co remains an unverified potential lead.",
        claim_kind="inference",
        claim_status="draft",
        inference_confidence="low",
        inference_basis="Only D-grade context is available.",
        information_cutoff_date=date(2026, 7, 6),
        evidence_links=(EvidenceLinkInput(lead.id, "context"),),
        recorded_at_utc=_recorded(6),
    )
    disputed = ledger.create_claim(
        case_id,
        claim_key="stage1-fixture-disputed",
        statement="Fixture Disputed Co has conflicting beneficiary evidence.",
        claim_kind="inference",
        claim_status="disputed",
        inference_confidence="low",
        inference_basis="Attributable supporting and contradictory records coexist.",
        information_cutoff_date=date(2026, 7, 6),
        evidence_links=(
            EvidenceLinkInput(study.id, "supports"),
            EvidenceLinkInput(conflict.id, "contradicts"),
        ),
        recorded_at_utc=_recorded(6),
    )
    with session_factory() as session:
        result = {}
        for key, claim in (
            ("direct", direct),
            ("secondary", secondary),
            ("draft", draft),
            ("disputed", disputed),
        ):
            result[key] = session.scalar(
                select(ClaimRevision).where(ClaimRevision.claim_id == claim.id)
            )
        return result


def _fixture_assertions(
    session_factory: sessionmaker[Session], map_id: UUID
) -> dict[str, MapAssertionRevisionInput]:
    with session_factory() as session:
        upstream = session.scalar(
            select(IndustryMapNodeRevision)
            .join(IndustryMapNode, IndustryMapNode.id == IndustryMapNodeRevision.node_id)
            .where(
                IndustryMapNode.map_id == map_id,
                IndustryMapNode.node_key == "upstream-input",
            )
        )
        relationship = session.scalar(
            select(IndustryMapRelationshipRevision)
            .join(
                IndustryMapRelationship,
                IndustryMapRelationship.id
                == IndustryMapRelationshipRevision.relationship_id,
            )
            .where(
                IndustryMapRelationship.map_id == map_id,
                IndustryMapRelationship.relationship_key
                == "input-supplies-manufacturing",
            )
        )
        value_pool = session.scalar(
            select(IndustryMapObservationRevision)
            .join(
                IndustryMapObservation,
                IndustryMapObservation.id
                == IndustryMapObservationRevision.observation_id,
            )
            .where(
                IndustryMapObservation.map_id == map_id,
                IndustryMapObservation.observation_key
                == "unverified-value-pool-lead",
            )
        )
        bottleneck = session.scalar(
            select(IndustryMapObservationRevision)
            .join(
                IndustryMapObservation,
                IndustryMapObservation.id
                == IndustryMapObservationRevision.observation_id,
            )
            .where(
                IndustryMapObservation.map_id == map_id,
                IndustryMapObservation.observation_key == "disputed-bottleneck",
            )
        )
    return {
        "upstream": MapAssertionRevisionInput("node", upstream.id),
        "relationship": MapAssertionRevisionInput(
            "relationship", relationship.id
        ),
        "value_pool": MapAssertionRevisionInput("observation", value_pool.id),
        "bottleneck": MapAssertionRevisionInput("observation", bottleneck.id),
    }


def _beneficiary_revision(
    session_factory: sessionmaker[Session], beneficiary_id: UUID
) -> Stage1BeneficiaryRevision:
    with session_factory() as session:
        return session.scalar(
            select(Stage1BeneficiaryRevision).where(
                Stage1BeneficiaryRevision.beneficiary_id == beneficiary_id
            )
        )

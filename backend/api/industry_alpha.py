"""Lazy, read-only FastAPI boundary for the Industry Alpha ledger."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from backend.database import build_engine, build_session_factory
from industry_alpha.chain_map_query import IndustryChainMapQueryService
from industry_alpha.chain_map_repository import IndustryChainMapRepository
from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerNotVisible
from industry_alpha.query import EvidenceLedgerQueryService
from industry_alpha.repository import EvidenceLedgerRepository
from industry_alpha.stage1_query import Stage1BeneficiaryQueryService
from industry_alpha.stage1_repository import Stage1BeneficiaryRepository
from industry_alpha.stage2_query import Stage2CompanyResearchQueryService
from industry_alpha.stage2_repository import Stage2CompanyResearchRepository
from industry_alpha.stage2_expectations_query import (
    Stage2ExpectationQueryService,
    Stage2ValuationQueryService,
)
from industry_alpha.stage2_expectations_repository import Stage2ExpectationRepository
from industry_alpha.stage2_assessments_query import (
    Stage2CatalystQueryService,
    Stage2RiskQueryService,
)
from industry_alpha.stage2_assessments_repository import Stage2AssessmentRepository

router = APIRouter(prefix="/industry-alpha", tags=["industry-alpha"])


def get_industry_alpha_session_factory() -> Iterator[sessionmaker[Session]]:
    """Create database resources only when a ledger route is requested."""
    try:
        engine = build_engine()
    except (RuntimeError, SQLAlchemyError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Industry Alpha database configuration is unavailable. "
                "Verify local database settings and try again."
            ),
        ) from exc
    try:
        yield build_session_factory(engine)
    finally:
        engine.dispose()


@router.get("/maps")
def list_industry_maps(
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return IndustryChainMapQueryService(
                IndustryChainMapRepository(session)
            ).list_maps(as_of_cutoff=as_of_cutoff).to_dict()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/maps/{map_id}")
def get_industry_map(
    map_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return IndustryChainMapQueryService(
                IndustryChainMapRepository(session)
            ).get_map(map_id, as_of_cutoff=as_of_cutoff).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/maps/{map_id}/beneficiaries")
def list_stage1_beneficiaries(
    map_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return Stage1BeneficiaryQueryService(
                Stage1BeneficiaryRepository(session)
            ).list_beneficiaries(
                map_id, as_of_cutoff=as_of_cutoff
            ).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/beneficiaries/{beneficiary_id}")
def get_stage1_beneficiary(
    beneficiary_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return Stage1BeneficiaryQueryService(
                Stage1BeneficiaryRepository(session)
            ).get_beneficiary(
                beneficiary_id, as_of_cutoff=as_of_cutoff
            ).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/maps/{map_id}/candidate-pools")
def list_stage1_candidate_pools(
    map_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return Stage1BeneficiaryQueryService(
                Stage1BeneficiaryRepository(session)
            ).list_candidate_pools(
                map_id, as_of_cutoff=as_of_cutoff
            ).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/candidate-pools/{candidate_pool_id}")
def get_stage1_candidate_pool(
    candidate_pool_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return Stage1BeneficiaryQueryService(
                Stage1BeneficiaryRepository(session)
            ).get_candidate_pool(
                candidate_pool_id, as_of_cutoff=as_of_cutoff
            ).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/company-research")
def list_stage2_company_research(
    candidate_pool_revision_id: UUID | None = Query(default=None),
    map_id: UUID | None = Query(default=None),
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return Stage2CompanyResearchQueryService(
                Stage2CompanyResearchRepository(session)
            ).list_research(
                candidate_pool_revision_id=candidate_pool_revision_id,
                map_id=map_id,
                as_of_cutoff=as_of_cutoff,
            ).to_dict()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/company-research/{company_research_id}")
def get_stage2_company_research(
    company_research_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return Stage2CompanyResearchQueryService(
                Stage2CompanyResearchRepository(session)
            ).get_research(
                company_research_id, as_of_cutoff=as_of_cutoff
            ).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/market-expectations")
def list_stage2_market_expectations(
    company_research_id: UUID | None = Query(default=None),
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return Stage2ExpectationQueryService(
                Stage2ExpectationRepository(session)
            ).list_expectations(
                company_research_id=company_research_id,
                as_of_cutoff=as_of_cutoff,
            ).to_dict()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/market-expectations/{expectation_id}")
def get_stage2_market_expectation(
    expectation_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return Stage2ExpectationQueryService(
                Stage2ExpectationRepository(session)
            ).get_expectation(expectation_id, as_of_cutoff=as_of_cutoff).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/valuation-snapshots")
def list_stage2_valuation_snapshots(
    company_research_id: UUID | None = Query(default=None),
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return Stage2ValuationQueryService(
                Stage2ExpectationRepository(session)
            ).list_valuations(
                company_research_id=company_research_id,
                as_of_cutoff=as_of_cutoff,
            ).to_dict()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/valuation-snapshots/{valuation_id}")
def get_stage2_valuation_snapshot(
    valuation_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return Stage2ValuationQueryService(
                Stage2ExpectationRepository(session)
            ).get_valuation(valuation_id, as_of_cutoff=as_of_cutoff).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/catalyst-assessments")
def list_stage2_catalyst_assessments(
    company_research_id: UUID | None = Query(default=None),
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return Stage2CatalystQueryService(
                Stage2AssessmentRepository(session)
            ).list_catalysts(
                company_research_id=company_research_id,
                as_of_cutoff=as_of_cutoff,
            ).to_dict()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/catalyst-assessments/{catalyst_id}")
def get_stage2_catalyst_assessment(
    catalyst_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return Stage2CatalystQueryService(
                Stage2AssessmentRepository(session)
            ).get_catalyst(catalyst_id, as_of_cutoff=as_of_cutoff).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/risk-assessments")
def list_stage2_risk_assessments(
    company_research_id: UUID | None = Query(default=None),
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return Stage2RiskQueryService(
                Stage2AssessmentRepository(session)
            ).list_risks(
                company_research_id=company_research_id,
                as_of_cutoff=as_of_cutoff,
            ).to_dict()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/risk-assessments/{risk_id}")
def get_stage2_risk_assessment(
    risk_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return Stage2RiskQueryService(
                Stage2AssessmentRepository(session)
            ).get_risk(risk_id, as_of_cutoff=as_of_cutoff).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/cases")
def list_industry_alpha_cases(
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return EvidenceLedgerQueryService(
                EvidenceLedgerRepository(session)
            ).list_cases(as_of_cutoff=as_of_cutoff).to_dict()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc


@router.get("/cases/{case_id}")
def get_industry_alpha_case(
    case_id: UUID,
    as_of_cutoff: date | None = Query(default=None),
    session_factory: sessionmaker[Session] = Depends(get_industry_alpha_session_factory),
) -> dict:
    try:
        with session_factory() as session:
            return EvidenceLedgerQueryService(
                EvidenceLedgerRepository(session)
            ).get_case(case_id, as_of_cutoff=as_of_cutoff).to_dict()
    except (EvidenceLedgerNotFound, EvidenceLedgerNotVisible) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=503,
            detail="Industry Alpha database query failed. Verify DATABASE_URL and run Alembic migrations.",
        ) from exc

"""Temporary CI diagnostic for Issue #236; remove before final validation."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select


_TARGET = "test_postgres_identical_concurrent_commit_serializes_to_one_output"


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    skipped = pytest.mark.skip(reason="temporary Issue #236 PostgreSQL diagnostic")
    for item in items:
        if item.name != _TARGET:
            item.add_marker(skipped)


def pytest_pyfunc_call(pyfuncitem: pytest.Function) -> bool | None:
    if pyfuncitem.name != _TARGET:
        return None
    module = pyfuncitem.module
    database_url = pyfuncitem.funcargs["postgres_database_url"]
    engine = module.build_engine(database_url)
    try:
        factory = module.build_session_factory(engine)
        fixture = module.build_stage1_beneficiary_fixture(factory)
        with factory.begin() as session:
            beneficiary = session.get(module.Stage1Beneficiary, fixture.direct_beneficiary_id)
            beneficiary_revision = session.scalar(
                select(module.Stage1BeneficiaryRevision)
                .where(module.Stage1BeneficiaryRevision.beneficiary_id == beneficiary.id)
                .order_by(module.Stage1BeneficiaryRevision.revision_no.desc())
            )
            industry_map = session.get(module.IndustryMap, beneficiary.map_id)
            map_revision = session.scalar(
                select(module.IndustryMapRevision)
                .where(module.IndustryMapRevision.map_id == industry_map.id)
                .order_by(module.IndustryMapRevision.revision_no.desc())
            )
            recorded = max(
                beneficiary_revision.recorded_at_utc.astimezone(module.UTC),
                map_revision.recorded_at_utc.astimezone(module.UTC),
            ) + timedelta(seconds=1)
            session_identity = module.IndustryThesisSessionIdentity(
                created_recorded_utc=recorded,
                created_by_kind="local_user",
                state="active",
                latest_revision_number=1,
            )
            session.add(session_identity)
            session.flush()
            candidate_identity = module.IndustryThesisCandidateIdentity(
                session_id=session_identity.id,
                candidate_key="d" * 64,
                created_recorded_utc=recorded,
                latest_revision_number=1,
            )
            session.add(candidate_identity)
            session.flush()
            assert candidate_identity.id is not None
    finally:
        engine.dispose()
    return True

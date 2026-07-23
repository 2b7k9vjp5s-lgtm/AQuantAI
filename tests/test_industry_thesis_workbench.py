from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from backend.database.canonical_price_models import (
    ListedInstrument,
    ListedInstrumentRevision,
)
from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
import industry_alpha.stage1_models  # noqa: F401 - register output-link FK targets
from industry_alpha.industry_thesis_models import (
    IndustryThesisSessionIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_workbench import (
    IndustryThesisWorkbenchError,
    IndustryThesisWorkbenchQueryService,
    validate_workbench_boundary,
)

UTC = timezone.utc
BASE_TIME = datetime(2026, 7, 23, 1, 0, tzinfo=UTC)


@pytest.fixture()
def database():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    try:
        yield factory
    finally:
        engine.dispose()


def _revision(
    *,
    revision_id: UUID,
    session_id: UUID,
    revision_number: int,
    title: str | None,
    text: str,
    recorded_at: datetime,
    cutoff: date,
    workflow_state: str = "draft",
    coverage_state: str = "partial_local_coverage",
    supersedes_revision_id: UUID | None = None,
) -> IndustryThesisSessionRevision:
    return IndustryThesisSessionRevision(
        id=revision_id,
        session_id=session_id,
        revision_number=revision_number,
        thesis_text_original=text,
        thesis_title_reviewed=title,
        driver_type="demand_expansion",
        analysis_horizon_kind="medium_term",
        analysis_start_date=None,
        analysis_end_date=None,
        market_scope_json='[{"market_namespace":"CN_A"}]',
        chain_boundary_json='{"included":["materials"]}',
        exclusions_json="[]",
        seed_companies_json="[]",
        seed_products_json="[]",
        seed_technologies_json="[]",
        seed_bottlenecks_json="[]",
        draft_graph_json='{"nodes":[],"relationships":[]}',
        coverage_state=coverage_state,
        workflow_state=workflow_state,
        information_cutoff_date=cutoff,
        recorded_at_utc=recorded_at,
        input_fingerprint_sha256=(f"{revision_number:x}" * 64)[:64],
        supersedes_revision_id=supersedes_revision_id,
        revision_note=f"revision {revision_number}",
    )


def _seed(database) -> dict[str, UUID]:
    session_a = UUID(int=10)
    session_b = UUID(int=20)
    revision_a1 = UUID(int=101)
    revision_a2 = UUID(int=102)
    revision_b1 = UUID(int=201)

    with database.begin() as db:
        db.add_all(
            [
                IndustryThesisSessionIdentity(
                    id=session_a,
                    created_recorded_utc=BASE_TIME,
                    created_by_kind="local_user",
                    state="active",
                    latest_revision_number=1,
                ),
                IndustryThesisSessionIdentity(
                    id=session_b,
                    created_recorded_utc=BASE_TIME + timedelta(minutes=5),
                    created_by_kind="local_user",
                    state="active",
                    latest_revision_number=1,
                ),
            ]
        )
        db.add_all(
            [
                _revision(
                    revision_id=revision_a1,
                    session_id=session_a,
                    revision_number=1,
                    title=None,
                    text="先进材料需求扩张\n第二行说明",
                    recorded_at=BASE_TIME + timedelta(minutes=10),
                    cutoff=date(2026, 7, 22),
                ),
                _revision(
                    revision_id=revision_b1,
                    session_id=session_b,
                    revision_number=1,
                    title="高纯电子气体",
                    text="高纯电子气体本地研究",
                    recorded_at=BASE_TIME + timedelta(minutes=20),
                    cutoff=date(2026, 7, 22),
                    workflow_state="awaiting_review",
                ),
            ]
        )

    with database.begin() as db:
        identity = db.get(IndustryThesisSessionIdentity, session_a)
        assert identity is not None
        identity.latest_revision_number = 2
        db.add(
            _revision(
                revision_id=revision_a2,
                session_id=session_a,
                revision_number=2,
                title="先进材料产业链",
                text="先进材料需求扩张与纯化瓶颈",
                recorded_at=BASE_TIME + timedelta(minutes=30),
                cutoff=date(2026, 7, 23),
                workflow_state="reviewed_plan_ready",
                coverage_state="reviewed_local_scope",
                supersedes_revision_id=revision_a1,
            )
        )

    return {
        "session_a": session_a,
        "session_b": session_b,
        "revision_a1": revision_a1,
        "revision_a2": revision_a2,
        "revision_b1": revision_b1,
    }


def _seed_local_options(database) -> dict[str, UUID]:
    map_a = UUID(int=1001)
    map_b = UUID(int=1002)
    map_a_revision_1 = UUID(int=1101)
    map_a_revision_2 = UUID(int=1102)
    map_b_revision_1 = UUID(int=1201)
    instrument_a = UUID(int=2001)
    instrument_b = UUID(int=2002)
    instrument_a_revision = UUID(int=2101)
    instrument_b_revision = UUID(int=2201)

    with database.begin() as db:
        db.add_all(
            [
                IndustryMap(
                    id=map_a,
                    case_id=UUID(int=3001),
                    map_key="gas-map",
                    created_at_utc=BASE_TIME,
                ),
                IndustryMap(
                    id=map_b,
                    case_id=UUID(int=3002),
                    map_key="advanced-material-map",
                    created_at_utc=BASE_TIME,
                ),
                ListedInstrument(
                    id=instrument_a,
                    instrument_key="CN_A:688001.SH",
                    created_at_utc=BASE_TIME,
                ),
                ListedInstrument(
                    id=instrument_b,
                    instrument_key="CN_A:600000.SH",
                    created_at_utc=BASE_TIME,
                ),
            ]
        )

    with database.begin() as db:
        db.add_all(
            [
                IndustryMapRevision(
                    id=map_a_revision_1,
                    map_id=map_a,
                    revision_no=1,
                    title="电子特气产业链",
                    scope="纯化、现场制气与客户认证",
                    information_cutoff_date=date(2026, 7, 22),
                    recorded_at_utc=BASE_TIME + timedelta(minutes=2),
                    supersedes_revision_id=None,
                ),
                IndustryMapRevision(
                    id=map_b_revision_1,
                    map_id=map_b,
                    revision_no=1,
                    title="先进材料产业链",
                    scope="上游材料与工艺瓶颈",
                    information_cutoff_date=date(2026, 7, 22),
                    recorded_at_utc=BASE_TIME + timedelta(minutes=3),
                    supersedes_revision_id=None,
                ),
                ListedInstrumentRevision(
                    id=instrument_a_revision,
                    instrument_id=instrument_a,
                    revision_no=1,
                    canonical_symbol="688001.SH",
                    security_type="common_equity",
                    market_code="CN_A",
                    exchange_code_namespace="SSE",
                    exchange_code="688001",
                    currency_code="CNY",
                    listing_date=date(2020, 1, 1),
                    delisting_date=None,
                    listing_status="active",
                    recorded_by="local-fixture",
                    information_cutoff_date=date(2026, 7, 22),
                    recorded_at_utc=BASE_TIME + timedelta(minutes=4),
                    supersedes_revision_id=None,
                ),
                ListedInstrumentRevision(
                    id=instrument_b_revision,
                    instrument_id=instrument_b,
                    revision_no=1,
                    canonical_symbol="600000.SH",
                    security_type="common_equity",
                    market_code="CN_A",
                    exchange_code_namespace="SSE",
                    exchange_code="600000",
                    currency_code="CNY",
                    listing_date=date(1999, 11, 10),
                    delisting_date=None,
                    listing_status="active",
                    recorded_by="local-fixture",
                    information_cutoff_date=date(2026, 7, 22),
                    recorded_at_utc=BASE_TIME + timedelta(minutes=5),
                    supersedes_revision_id=None,
                ),
            ]
        )

    with database.begin() as db:
        db.add(
            IndustryMapRevision(
                id=map_a_revision_2,
                map_id=map_a,
                revision_no=2,
                title="电子特气产业链（更新）",
                scope="新增海外产能与认证边界",
                information_cutoff_date=date(2026, 7, 24),
                recorded_at_utc=BASE_TIME + timedelta(days=1),
                supersedes_revision_id=map_a_revision_1,
            )
        )

    return {
        "map_a_revision_1": map_a_revision_1,
        "map_a_revision_2": map_a_revision_2,
        "instrument_a": instrument_a,
        "instrument_b": instrument_b,
    }


def test_empty_history_is_explicit(database) -> None:
    with database() as session:
        result = IndustryThesisWorkbenchQueryService(session).list_sessions(
            as_of_cutoff=date(2026, 7, 23),
            as_of_recorded_at_utc=BASE_TIME,
            limit=20,
        )

    assert result["sessions"] == []
    assert result["session_count"] == 0
    assert result["has_more"] is False
    assert result["notices"]["accepted_outputs_not_inferred"] is True


def test_history_uses_exact_visible_latest_revision_and_deterministic_order(database) -> None:
    ids = _seed(database)
    boundary = BASE_TIME + timedelta(minutes=25)

    with database() as session:
        result = IndustryThesisWorkbenchQueryService(session).list_sessions(
            as_of_cutoff=date(2026, 7, 22),
            as_of_recorded_at_utc=boundary,
            limit=20,
        )

    assert [item["session_id"] for item in result["sessions"]] == [
        str(ids["session_b"]),
        str(ids["session_a"]),
    ]
    assert result["sessions"][0]["visible_latest_revision_id"] == str(
        ids["revision_b1"]
    )
    assert result["sessions"][1]["visible_latest_revision_id"] == str(
        ids["revision_a1"]
    )
    assert result["sessions"][1]["visible_revision_count"] == 1
    assert result["sessions"][1]["thesis_title"] == "先进材料需求扩张"


def test_later_boundary_reveals_later_revision_without_rewriting_history(database) -> None:
    ids = _seed(database)

    with database() as session:
        result = IndustryThesisWorkbenchQueryService(session).list_sessions(
            as_of_cutoff=date(2026, 7, 23),
            as_of_recorded_at_utc=BASE_TIME + timedelta(minutes=35),
            limit=20,
        )

    first = result["sessions"][0]
    assert first["session_id"] == str(ids["session_a"])
    assert first["visible_latest_revision_id"] == str(ids["revision_a2"])
    assert first["visible_latest_revision_number"] == 2
    assert first["visible_revision_count"] == 2
    assert first["next_surface"] == "result"
    assert first["coverage_state"] == "reviewed_local_scope"


def test_limit_is_bounded_and_reports_more(database) -> None:
    _seed(database)
    with database() as session:
        result = IndustryThesisWorkbenchQueryService(session).list_sessions(
            as_of_cutoff=date(2026, 7, 23),
            as_of_recorded_at_utc=BASE_TIME + timedelta(minutes=35),
            limit=1,
        )

    assert result["session_count"] == 1
    assert result["has_more"] is True


def test_map_options_use_latest_visible_revision_and_deterministic_order(database) -> None:
    ids = _seed_local_options(database)
    with database() as session:
        result = IndustryThesisWorkbenchQueryService(session).list_map_options(
            as_of_cutoff=date(2026, 7, 23),
            as_of_recorded_at_utc=BASE_TIME + timedelta(hours=1),
            limit=20,
        )

    assert [item["title"] for item in result["options"]] == [
        "电子特气产业链",
        "先进材料产业链",
    ]
    assert result["options"][0]["map_revision_id"] == str(
        ids["map_a_revision_1"]
    )
    assert result["notices"]["explicit_selection_required"] is True
    assert result["notices"]["accepted_membership_not_inferred"] is True


def test_map_option_query_is_bounded_without_latest_fallback(database) -> None:
    ids = _seed_local_options(database)
    with database() as session:
        result = IndustryThesisWorkbenchQueryService(session).list_map_options(
            as_of_cutoff=date(2026, 7, 23),
            as_of_recorded_at_utc=BASE_TIME + timedelta(hours=1),
            query="电子特气",
            limit=1,
        )

    assert result["option_count"] == 1
    assert result["options"][0]["map_revision_id"] == str(
        ids["map_a_revision_1"]
    )
    assert result["options"][0]["map_revision_id"] != str(
        ids["map_a_revision_2"]
    )


def test_company_options_require_explicit_query_and_never_auto_select(database) -> None:
    _seed_local_options(database)
    with database() as session:
        service = IndustryThesisWorkbenchQueryService(session)
        with pytest.raises(IndustryThesisWorkbenchError):
            service.list_company_options(
                as_of_cutoff=date(2026, 7, 23),
                as_of_recorded_at_utc=BASE_TIME + timedelta(hours=1),
                query="6",
                limit=20,
            )
        result = service.list_company_options(
            as_of_cutoff=date(2026, 7, 23),
            as_of_recorded_at_utc=BASE_TIME + timedelta(hours=1),
            query=".SH",
            limit=20,
        )

    assert [item["code"] for item in result["options"]] == [
        "600000.SH",
        "688001.SH",
    ]
    assert all(item["source_kind"] == "listed_instrument" for item in result["options"])
    assert result["notices"]["first_result_not_selected"] is True
    assert result["notices"]["text_match_is_not_identity"] is True


def test_company_exact_code_exception_returns_exact_identity(database) -> None:
    ids = _seed_local_options(database)
    with database() as session:
        result = IndustryThesisWorkbenchQueryService(session).list_company_options(
            as_of_cutoff=date(2026, 7, 23),
            as_of_recorded_at_utc=BASE_TIME + timedelta(hours=1),
            query="688001.SH",
            limit=20,
        )

    assert result["option_count"] == 1
    assert result["options"][0]["listed_instrument_id"] == str(
        ids["instrument_a"]
    )


@pytest.mark.parametrize(
    ("cutoff", "recorded_at"),
    [
        (date(2026, 7, 23), datetime(2026, 7, 23, 1, 0)),
        (date(2026, 7, 24), BASE_TIME),
    ],
)
def test_invalid_boundaries_fail_closed(cutoff, recorded_at) -> None:
    with pytest.raises(IndustryThesisWorkbenchError):
        validate_workbench_boundary(cutoff, recorded_at)


def test_limits_outside_contract_fail_closed(database) -> None:
    with database() as session:
        service = IndustryThesisWorkbenchQueryService(session)
        with pytest.raises(IndustryThesisWorkbenchError):
            service.list_sessions(
                as_of_cutoff=date(2026, 7, 23),
                as_of_recorded_at_utc=BASE_TIME,
                limit=101,
            )
        with pytest.raises(IndustryThesisWorkbenchError):
            service.list_map_options(
                as_of_cutoff=date(2026, 7, 23),
                as_of_recorded_at_utc=BASE_TIME,
                limit=21,
            )

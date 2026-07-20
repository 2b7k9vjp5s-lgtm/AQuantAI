from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.evidence_intelligence_repository import (
    EVENT_TYPE_CASE_REVISION,
    EVENT_TYPE_COMPANY_RESEARCH_REVISION,
    EVENT_TYPE_EVIDENCE,
    EVENT_TYPE_INDUSTRY_MAP_REVISION,
    EvidenceIntelligenceRepository,
    FeedCursorPosition,
)
from industry_alpha.models import EvidenceItem, ResearchCase, ResearchCaseRevision
from industry_alpha.stage2_models import Stage2CompanyResearchRevision

UTC = timezone.utc
NOW = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)
CASE_ID = UUID("00000000-0000-0000-0000-000000000010")
MAP_ID = UUID("00000000-0000-0000-0000-000000000020")
COMPANY_RESEARCH_ID = UUID("00000000-0000-0000-0000-000000000030")
EVIDENCE_ID = UUID("00000000-0000-0000-0000-000000000101")
CASE_REVISION_ID = UUID("00000000-0000-0000-0000-000000000102")
MAP_REVISION_ID = UUID("00000000-0000-0000-0000-000000000103")
COMPANY_REVISION_ID = UUID("00000000-0000-0000-0000-000000000104")


def _session_factory() -> tuple[object, sessionmaker[Session]]:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (
        ResearchCase.__table__,
        ResearchCaseRevision.__table__,
        EvidenceItem.__table__,
        IndustryMap.__table__,
        IndustryMapRevision.__table__,
        Stage2CompanyResearchRevision.__table__,
    ):
        table.create(engine, checkfirst=True)
    return engine, sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def _seed(factory: sessionmaker[Session]) -> None:
    with factory() as session:
        session.add(
            ResearchCase(
                id=CASE_ID,
                case_key="memory-expansion",
                created_at_utc=NOW - timedelta(days=30),
                origin="manual",
            )
        )
        session.add(
            IndustryMap(
                id=MAP_ID,
                case_id=CASE_ID,
                map_key="memory-chain",
                created_at_utc=NOW - timedelta(days=20),
            )
        )
        session.add_all(
            [
                EvidenceItem(
                    id=EVIDENCE_ID,
                    case_id=CASE_ID,
                    evidence_grade="A",
                    source_kind="official",
                    source_title="Official capacity update",
                    publisher_or_author=None,
                    source_locator="https://example.com/source",
                    information_date=date(2026, 7, 19),
                    recorded_at_utc=NOW,
                    summary="Accepted evidence summary.",
                    content_fingerprint="feed-evidence",
                    supersedes_evidence_id=None,
                ),
                ResearchCaseRevision(
                    id=CASE_REVISION_ID,
                    case_id=CASE_ID,
                    revision_no=1,
                    title="Memory expansion case",
                    research_question="What changed?",
                    summary=None,
                    workflow_state="open",
                    conclusion_status="unassessed",
                    information_cutoff_date=date(2026, 7, 19),
                    recorded_at_utc=NOW,
                    supersedes_revision_id=None,
                ),
                IndustryMapRevision(
                    id=MAP_REVISION_ID,
                    map_id=MAP_ID,
                    revision_no=1,
                    title="Memory industry map",
                    scope="Map scope.",
                    information_cutoff_date=date(2026, 7, 19),
                    recorded_at_utc=NOW,
                    supersedes_revision_id=None,
                ),
                Stage2CompanyResearchRevision(
                    id=COMPANY_REVISION_ID,
                    company_research_id=COMPANY_RESEARCH_ID,
                    revision_no=1,
                    workflow_state="open",
                    conclusion_status="unassessed",
                    research_question="Can capacity transmit to earnings?",
                    summary="Company research summary.",
                    information_cutoff_date=date(2026, 7, 19),
                    recorded_at_utc=NOW,
                    supersedes_revision_id=None,
                ),
            ]
        )
        session.commit()


def test_repository_reads_four_sources_with_four_bounded_scalar_queries() -> None:
    engine, factory = _session_factory()
    _seed(factory)
    statements: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def _count_statement(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    with factory() as session:
        rows = EvidenceIntelligenceRepository(session).list_events(
            recorded_from=NOW - timedelta(days=1),
            recorded_to=NOW + timedelta(seconds=1),
            as_of_cutoff=None,
            event_type=None,
            cursor=None,
            per_source_limit=11,
        )

    assert {row.event_type for row in rows} == {
        EVENT_TYPE_EVIDENCE,
        EVENT_TYPE_CASE_REVISION,
        EVENT_TYPE_INDUSTRY_MAP_REVISION,
        EVENT_TYPE_COMPANY_RESEARCH_REVISION,
    }
    assert len(statements) == 4
    assert all("JOIN" not in statement.upper() for statement in statements)


def test_repository_applies_cutoff_and_event_type_inside_source_query() -> None:
    engine, factory = _session_factory()
    _seed(factory)
    statements: list[str] = []

    @event.listens_for(engine, "before_cursor_execute")
    def _count_statement(_conn, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    with factory() as session:
        rows = EvidenceIntelligenceRepository(session).list_events(
            recorded_from=NOW - timedelta(days=1),
            recorded_to=NOW + timedelta(seconds=1),
            as_of_cutoff=date(2026, 7, 18),
            event_type=EVENT_TYPE_EVIDENCE,
            cursor=None,
            per_source_limit=11,
        )

    assert rows == ()
    assert len(statements) == 1


def test_repository_cursor_preserves_cross_source_tie_order() -> None:
    _engine, factory = _session_factory()
    _seed(factory)
    cursor = FeedCursorPosition(
        recorded_at_utc=NOW,
        event_type=EVENT_TYPE_CASE_REVISION,
        event_id=CASE_REVISION_ID,
    )

    with factory() as session:
        rows = EvidenceIntelligenceRepository(session).list_events(
            recorded_from=NOW - timedelta(days=1),
            recorded_to=NOW + timedelta(seconds=1),
            as_of_cutoff=None,
            event_type=None,
            cursor=cursor,
            per_source_limit=11,
        )

    assert {row.event_type for row in rows} == {
        EVENT_TYPE_INDUSTRY_MAP_REVISION,
        EVENT_TYPE_COMPANY_RESEARCH_REVISION,
    }

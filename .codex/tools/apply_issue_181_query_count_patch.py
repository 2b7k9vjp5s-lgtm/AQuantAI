"""One-time deterministic patch for bounded snapshot-query verification."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "tests/test_investment_candidate_commands.py"
text = TARGET.read_text(encoding="utf-8")

text = text.replace(
    "from sqlalchemy import create_engine, func, select\n",
    "from sqlalchemy import create_engine, event, func, select\n",
)
old = '''    result = service.record_snapshot(payload)
    boundary = datetime(2026, 7, 22, 18, tzinfo=UTC)
    with database() as session:
        output = InvestmentCandidateQueryService(session).get_snapshot_revision(
            UUID(result["snapshot_revision_id"]),
            as_of_cutoff=CUTOFF,
            as_of_recorded_at_utc=boundary,
        )
'''
new = '''    result = service.record_snapshot(payload)
    boundary = datetime(2026, 7, 22, 18, tzinfo=UTC)
    query_count = 0

    def count_statement(*_args) -> None:
        nonlocal query_count
        query_count += 1

    engine = database.kw["bind"]
    event.listen(engine, "before_cursor_execute", count_statement)
    try:
        with database() as session:
            output = InvestmentCandidateQueryService(session).get_snapshot_revision(
                UUID(result["snapshot_revision_id"]),
                as_of_cutoff=CUTOFF,
                as_of_recorded_at_utc=boundary,
            )
    finally:
        event.remove(engine, "before_cursor_execute", count_statement)
    assert query_count == 9
'''
if old not in text:
    raise RuntimeError("snapshot query-count anchor is missing")
text = text.replace(old, new)

TARGET.write_text(text, encoding="utf-8")
compile(text, str(TARGET), "exec")

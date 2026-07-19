from __future__ import annotations

import pytest
from sqlalchemy import Integer, String, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from industry_alpha.stage2_expectations_repository import Stage2ExpectationRepository
from industry_alpha.stage2_repository_rows import load_ordered_rows


class _RepositoryRowsBase(DeclarativeBase):
    pass


class _RepositoryRow(_RepositoryRowsBase):
    __tablename__ = "stage2_repository_row_test"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bucket: Mapped[int] = mapped_column(Integer, nullable=False)
    sort_key: Mapped[str] = mapped_column(String(32), nullable=False)


@pytest.fixture
def engine():
    value = create_engine("sqlite+pysqlite:///:memory:")
    _RepositoryRowsBase.metadata.create_all(value)
    with Session(value) as session:
        session.add_all(
            [
                _RepositoryRow(id=1, bucket=7, sort_key="beta"),
                _RepositoryRow(id=2, bucket=7, sort_key="alpha"),
                _RepositoryRow(id=3, bucket=8, sort_key="beta"),
            ]
        )
        session.commit()
    yield value
    value.dispose()


def test_empty_ids_return_without_executing_a_select(engine):
    statements: list[str] = []

    def capture_statement(_connection, _cursor, statement, _parameters, _context, _executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", capture_statement)
    try:
        with Session(engine) as session:
            assert load_ordered_rows(
                session,
                _RepositoryRow,
                _RepositoryRow.id,
                [],
                _RepositoryRow.id,
            ) == ()
    finally:
        event.remove(engine, "before_cursor_execute", capture_statement)

    assert statements == []


def test_explicit_order_duplicate_ids_and_missing_ids(engine):
    with Session(engine) as session:
        rows = load_ordered_rows(
            session,
            _RepositoryRow,
            _RepositoryRow.id,
            [3, 2, 2, 999, 1],
            _RepositoryRow.sort_key,
            _RepositoryRow.id,
        )

    assert [row.id for row in rows] == [2, 1, 3]


def test_loader_leaves_transaction_ownership_with_caller(engine):
    with Session(engine) as session:
        row = session.get(_RepositoryRow, 1)
        assert row is not None
        row.sort_key = "changed-but-not-committed"

        loaded = load_ordered_rows(
            session,
            _RepositoryRow,
            _RepositoryRow.id,
            [1],
            _RepositoryRow.id,
        )

        assert [item.id for item in loaded] == [1]
        assert session.in_transaction()
        session.rollback()

    with Session(engine) as session:
        persisted = session.get(_RepositoryRow, 1)
        assert persisted is not None
        assert persisted.sort_key == "beta"


def test_expectation_wrapper_keeps_none_filtering_local(engine):
    with Session(engine) as session:
        repository = Stage2ExpectationRepository(session)
        rows = repository._rows(
            _RepositoryRow,
            _RepositoryRow.id,
            [None, 2, None],
            _RepositoryRow.id,
        )

    assert [row.id for row in rows] == [2]

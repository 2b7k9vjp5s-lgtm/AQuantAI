from __future__ import annotations

import importlib

import pytest

migration = importlib.import_module(
    "migrations.versions.20260721_0012_typed_beneficiary_evidence_semantics"
)


class _Result:
    def __init__(self, populated: bool) -> None:
        self._populated = populated

    def first(self):
        return object() if self._populated else None


class _Bind:
    def __init__(self, populated: bool) -> None:
        self._populated = populated
        self.queries: list[str] = []

    def execute(self, statement):
        self.queries.append(str(statement))
        return _Result(self._populated)


class _Operation:
    def __init__(self, populated: bool) -> None:
        self.bind = _Bind(populated)
        self.drops: list[tuple[str, str]] = []

    def get_bind(self):
        return self.bind

    def drop_index(self, name: str, *, table_name: str) -> None:
        self.drops.append(("index", f"{table_name}.{name}"))

    def drop_table(self, name: str) -> None:
        self.drops.append(("table", name))


def test_populated_downgrade_fails_before_schema_change(monkeypatch) -> None:
    operation = _Operation(populated=True)
    monkeypatch.setattr(migration, "op", operation)

    with pytest.raises(
        RuntimeError,
        match="Cannot downgrade typed beneficiary evidence semantics",
    ):
        migration.downgrade()

    assert operation.drops == []
    assert operation.bind.queries


def test_empty_downgrade_removes_all_five_tables(monkeypatch) -> None:
    operation = _Operation(populated=False)
    monkeypatch.setattr(migration, "op", operation)

    migration.downgrade()

    dropped_tables = {name for kind, name in operation.drops if kind == "table"}
    assert dropped_tables == set(migration._TABLES)
    assert len(operation.bind.queries) == len(migration._TABLES)

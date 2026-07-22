from __future__ import annotations

import importlib
import pytest

migration = importlib.import_module("migrations.versions.20260722_0013_canonical_price_comparison_eligibility")


class Result:
    def __init__(self, populated): self.populated = populated
    def first(self): return object() if self.populated else None


class Bind:
    def __init__(self, populated): self.populated = populated; self.queries = []
    def execute(self, statement): self.queries.append(str(statement)); return Result(self.populated)


class Operation:
    def __init__(self, populated): self.bind = Bind(populated); self.drops = []
    def get_bind(self): return self.bind
    def drop_index(self, name, *, table_name): self.drops.append(("index", name, table_name))
    def drop_table(self, name): self.drops.append(("table", name))


def test_populated_downgrade_fails_before_any_drop(monkeypatch):
    operation = Operation(True); monkeypatch.setattr(migration, "op", operation)
    with pytest.raises(RuntimeError, match="Cannot downgrade canonical price"):
        migration.downgrade()
    assert operation.drops == []


def test_empty_downgrade_removes_exactly_nine_tables(monkeypatch):
    operation = Operation(False); monkeypatch.setattr(migration, "op", operation)
    migration.downgrade()
    assert {x[1] for x in operation.drops if x[0] == "table"} == set(migration._TABLES)
    assert len(migration._TABLES) == 9

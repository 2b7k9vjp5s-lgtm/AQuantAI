from __future__ import annotations

import importlib
import inspect as pyinspect
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, func, inspect, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.errors import EvidenceLedgerImmutableError
import industry_alpha.orm_append_only as orm_append_only
from industry_alpha.orm_append_only import reject_append_only_mutation
import industry_alpha.stage2_assessments_models as v06c
import industry_alpha.stage2_expectations_models as v06b
from industry_alpha.stage2_judgments_fixtures import build_stage2_judgment_fixture
import industry_alpha.stage2_judgments_models as v06d
import industry_alpha.stage2_models as v06a


MODULES = (
    ("industry_alpha.stage2_models", v06a, "reject_stage2_mutation", "STAGE2_MODELS", 11),
    (
        "industry_alpha.stage2_expectations_models",
        v06b,
        "reject_stage2_expectation_mutation",
        "STAGE2_EXPECTATION_MODELS",
        10,
    ),
    (
        "industry_alpha.stage2_assessments_models",
        v06c,
        "reject_stage2_assessment_mutation",
        "STAGE2_ASSESSMENT_MODELS",
        14,
    ),
    (
        "industry_alpha.stage2_judgments_models",
        v06d,
        "reject_stage2_judgment_mutation",
        "STAGE2_JUDGMENT_MODELS",
        18,
    ),
)

V06C_DYNAMIC_MODELS = {
    "Stage2CatalystHypothesisLink": "stage2_catalyst_hypothesis_links",
    "Stage2CatalystExpectationLink": "stage2_catalyst_expectation_links",
    "Stage2CatalystValuationLink": "stage2_catalyst_valuation_links",
    "Stage2CatalystClaimLink": "stage2_catalyst_claim_links",
    "Stage2RiskHypothesisLink": "stage2_risk_hypothesis_links",
    "Stage2RiskExpectationLink": "stage2_risk_expectation_links",
    "Stage2RiskValuationLink": "stage2_risk_valuation_links",
    "Stage2RiskClaimLink": "stage2_risk_claim_links",
}

V06D_DYNAMIC_MODELS = {
    f"Stage2{kind}Judgment{upstream}Link": (
        f"stage2_{kind.lower()}_judgment_{upstream.lower()}_links"
    )
    for kind in ("Industry", "Company")
    for upstream in ("Hypothesis", "Expectation", "Valuation", "Catalyst", "Risk", "Claim")
}

MUTATION_CASES = (
    (v06a.Stage2CompanyResearch, "stock_code", "999999"),
    (v06b.Stage2MarketExpectation, "expectation_key", "contract-updated-expectation"),
    (v06c.Stage2CatalystAssessment, "catalyst_key", "contract-updated-catalyst"),
    (v06d.Stage2IndustryJudgment, "judgment_key", "contract-updated-judgment"),
)


@pytest.fixture(scope="module")
def lifecycle_store():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    build_stage2_judgment_fixture(factory)
    try:
        yield engine, factory
    finally:
        engine.dispose()


def _first_row(session: Session, model: type):
    row = session.scalars(select(model).order_by(model.id)).first()
    assert row is not None, model.__name__
    return row


def test_listener_registration_model_counts_and_shared_metadata_are_fixed():
    assert [size for *_rest, size in MODULES] == [11, 10, 14, 18]
    for _module_name, module, listener_name, tuple_name, expected_size in MODULES:
        listener = getattr(module, listener_name)
        models = getattr(module, tuple_name)
        assert event.contains(Session, "before_flush", listener)
        assert len(models) == expected_size
        assert all(model.__table__.metadata is Base.metadata for model in models)

    stage2_tables = sorted(
        table_name for table_name in Base.metadata.tables if table_name.startswith("stage2_")
    )
    assert len(stage2_tables) == 53


def test_dynamic_model_globals_and_tables_are_fixed():
    assert len(V06C_DYNAMIC_MODELS) == 8
    assert len(V06D_DYNAMIC_MODELS) == 12
    for module, expected in (
        (v06c, V06C_DYNAMIC_MODELS),
        (v06d, V06D_DYNAMIC_MODELS),
    ):
        for class_name, table_name in expected.items():
            model = getattr(module, class_name)
            assert model.__name__ == class_name
            assert model.__table__.name == table_name
            assert model.__table__ is Base.metadata.tables[table_name]


def test_ordinary_repeated_imports_preserve_module_listener_mapper_and_table_identity():
    metadata = Base.metadata
    snapshots = {}
    for module_name, module, listener_name, tuple_name, _expected_size in MODULES:
        models = getattr(module, tuple_name)
        snapshots[module_name] = {
            "module": module,
            "listener": getattr(module, listener_name),
            "tuple": models,
            "classes": tuple(models),
            "tables": tuple(model.__table__ for model in models),
        }

    dynamic_snapshots = {
        (module.__name__, class_name): getattr(module, class_name)
        for module, expected in ((v06c, V06C_DYNAMIC_MODELS), (v06d, V06D_DYNAMIC_MODELS))
        for class_name in expected
    }

    for _ in range(3):
        for module_name, *_rest in MODULES:
            assert importlib.import_module(module_name) is snapshots[module_name]["module"]

    assert Base.metadata is metadata
    for module_name, module, listener_name, tuple_name, _expected_size in MODULES:
        snapshot = snapshots[module_name]
        assert module is snapshot["module"]
        assert getattr(module, listener_name) is snapshot["listener"]
        assert getattr(module, tuple_name) is snapshot["tuple"]
        assert tuple(getattr(module, tuple_name)) == snapshot["classes"]
        assert tuple(model.__table__ for model in getattr(module, tuple_name)) == snapshot["tables"]

    for (module_name, class_name), model in dynamic_snapshots.items():
        module = importlib.import_module(module_name)
        assert getattr(module, class_name) is model
        assert model.__table__ is metadata.tables[model.__tablename__]


def test_repeated_imports_in_clean_process_invoke_each_listener_once_per_flush():
    project_root = Path(__file__).resolve().parents[1]
    script = textwrap.dedent(
        """
        import importlib
        import json
        import sys

        from sqlalchemy import create_engine, select
        from sqlalchemy.pool import StaticPool

        from backend.database.engine import build_session_factory
        from backend.database.models import Base
        from industry_alpha.stage2_judgments_fixtures import build_stage2_judgment_fixture
        import industry_alpha.stage2_assessments_models as v06c
        import industry_alpha.stage2_expectations_models as v06b
        import industry_alpha.stage2_judgments_models as v06d
        import industry_alpha.stage2_models as v06a

        modules = (
            "industry_alpha.stage2_models",
            "industry_alpha.stage2_expectations_models",
            "industry_alpha.stage2_assessments_models",
            "industry_alpha.stage2_judgments_models",
        )
        for _ in range(3):
            for module_name in modules:
                importlib.import_module(module_name)

        engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        factory = build_session_factory(engine)
        build_stage2_judgment_fixture(factory)

        listeners = (
            v06a.reject_stage2_mutation,
            v06b.reject_stage2_expectation_mutation,
            v06c.reject_stage2_assessment_mutation,
            v06d.reject_stage2_judgment_mutation,
        )
        code_names = {listener.__code__: listener.__name__ for listener in listeners}
        counts = {listener.__name__: 0 for listener in listeners}

        def profile(frame, event_name, _argument):
            if event_name == "call" and frame.f_code in code_names:
                counts[code_names[frame.f_code]] += 1

        with factory() as session:
            row = session.scalars(select(v06a.Stage2CompanyResearch)).first()
            row.stock_code = row.stock_code
            sys.setprofile(profile)
            try:
                session.flush()
            finally:
                sys.setprofile(None)
                session.rollback()

        engine.dispose()
        print(json.dumps(counts, sort_keys=True))
        """
    )
    environment = os.environ.copy()
    environment["PYTHONHASHSEED"] = "0"
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    counts = json.loads(completed.stdout.strip().splitlines()[-1])
    assert counts == {
        "reject_stage2_assessment_mutation": 1,
        "reject_stage2_expectation_mutation": 1,
        "reject_stage2_judgment_mutation": 1,
        "reject_stage2_mutation": 1,
    }


def test_pending_insert_and_dirty_but_unmodified_row_are_allowed(lifecycle_store):
    _engine, factory = lifecycle_store
    with factory() as session:
        row = _first_row(session, v06a.Stage2CompanyResearch)
        row.stock_code = row.stock_code
        assert row in session.dirty
        assert not session.is_modified(row, include_collections=False)
        session.flush()
        session.rollback()

    with factory() as session:
        revision_id = session.scalar(
            select(v06a.Stage2CompanyResearchRevision.id).order_by(
                v06a.Stage2CompanyResearchRevision.id
            )
        )
        assert revision_id is not None
        highest_item_no = session.scalar(
            select(func.max(v06a.Stage2VerificationItem.item_no)).where(
                v06a.Stage2VerificationItem.company_research_revision_id == revision_id
            )
        )
        item = v06a.Stage2VerificationItem(
            company_research_revision_id=revision_id,
            item_no=(highest_item_no or 0) + 1000,
            description="Lifecycle contract pending insert.",
            status="open",
            due_date=None,
            recorded_at_utc=datetime(2026, 7, 20, tzinfo=timezone.utc),
        )
        session.add(item)
        session.flush()
        assert item.id is not None
        session.rollback()


@pytest.mark.parametrize(
    "model,field,replacement",
    MUTATION_CASES,
    ids=[model.__name__ for model, _field, _replacement in MUTATION_CASES],
)
@pytest.mark.parametrize("operation", ("update", "delete"))
def test_each_stage_family_rejects_exact_mutation_and_rolls_back(
    lifecycle_store, model, field, replacement, operation
):
    _engine, factory = lifecycle_store
    with factory() as session:
        row = _first_row(session, model)
        identity = inspect(row).identity[0]
        original_value = getattr(row, field)
        if operation == "update":
            setattr(row, field, replacement)
            expected_message = (
                f"{model.__name__} rows are append-only and cannot be updated."
            )
        else:
            session.delete(row)
            expected_message = (
                f"{model.__name__} rows are append-only and cannot be deleted."
            )

        with pytest.raises(EvidenceLedgerImmutableError) as captured:
            session.flush()
        assert type(captured.value) is EvidenceLedgerImmutableError
        assert str(captured.value) == expected_message
        session.rollback()

    with factory() as session:
        restored = session.get(model, identity)
        assert restored is not None
        assert getattr(restored, field) == original_value


def test_global_listener_applies_to_custom_session_subclass(lifecycle_store):
    engine, _factory = lifecycle_store

    class CustomSession(Session):
        pass

    custom_factory = sessionmaker(
        bind=engine,
        class_=CustomSession,
        expire_on_commit=False,
    )
    with custom_factory() as session:
        row = _first_row(session, v06a.Stage2CompanyResearch)
        row.stock_code = "888888"
        with pytest.raises(EvidenceLedgerImmutableError) as captured:
            session.flush()
        assert type(captured.value) is EvidenceLedgerImmutableError
        assert str(captured.value) == (
            "Stage2CompanyResearch rows are append-only and cannot be updated."
        )
        session.rollback()


class _HelperModel:
    pass


class _OtherModel:
    pass


class _FakeSession:
    def __init__(self, *, deleted=(), dirty=(), modified=()):
        self.deleted = tuple(deleted)
        self.dirty = tuple(dirty)
        self.new = (object(),)
        self._modified = set(modified)
        self.modified_calls = []

    def is_modified(self, row, *, include_collections):
        self.modified_calls.append((row, include_collections))
        return row in self._modified


def test_neutral_helper_checks_delete_before_dirty_and_preserves_exact_error():
    deleted = _HelperModel()
    dirty = _HelperModel()
    session = _FakeSession(deleted=(deleted,), dirty=(dirty,), modified=(dirty,))

    with pytest.raises(EvidenceLedgerImmutableError) as captured:
        reject_append_only_mutation(session, (_HelperModel,))

    assert type(captured.value) is EvidenceLedgerImmutableError
    assert str(captured.value) == (
        "_HelperModel rows are append-only and cannot be deleted."
    )
    assert session.modified_calls == []


def test_neutral_helper_preserves_exact_update_error():
    dirty = _HelperModel()
    session = _FakeSession(dirty=(dirty,), modified=(dirty,))

    with pytest.raises(EvidenceLedgerImmutableError) as captured:
        reject_append_only_mutation(session, (_HelperModel,))

    assert type(captured.value) is EvidenceLedgerImmutableError
    assert str(captured.value) == (
        "_HelperModel rows are append-only and cannot be updated."
    )
    assert session.modified_calls == [(dirty, False)]


def test_neutral_helper_returns_none_for_noop_pending_and_unmodified_state():
    dirty = _HelperModel()
    other = _OtherModel()
    session = _FakeSession(deleted=(other,), dirty=(dirty, other), modified=(other,))

    assert reject_append_only_mutation(session, (_HelperModel,)) is None
    assert session.modified_calls == [(dirty, False)]
    assert session.new


def test_neutral_helper_module_has_no_event_or_stage2_ownership():
    source = pyinspect.getsource(orm_append_only)
    assert "event.listens_for" not in source
    assert "industry_alpha.stage2" not in source
    assert not any(name.startswith("STAGE2_") for name in vars(orm_append_only))
    assert "Session" in vars(orm_append_only)
    assert "reject_append_only_mutation" in vars(orm_append_only)

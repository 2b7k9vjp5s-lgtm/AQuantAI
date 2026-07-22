from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

import pytest

from industry_alpha.company_comparison_query import (
    CompanyComparisonQueryService,
    CompanyComparisonSelectorError,
)
from industry_alpha.company_comparison_repository import (
    COMPARISON_QUERY_COUNT,
    CompanyComparisonDataError,
    ComparisonReadSet,
)

UTC = timezone.utc
POOL_REVISION_ID = UUID(int=1)
POOL_ID = UUID(int=2)
CASE_ID = UUID(int=3)
MAP_ID = UUID(int=4)
MAP_REVISION_ID = UUID(int=5)
A_MEMBER = UUID(int=101)
B_MEMBER = UUID(int=102)
C_MEMBER = UUID(int=103)
A_BENEFICIARY = UUID(int=201)
B_BENEFICIARY = UUID(int=202)
C_BENEFICIARY = UUID(int=203)
A_BENEFICIARY_REVISION = UUID(int=301)
B_BENEFICIARY_REVISION = UUID(int=302)
C_BENEFICIARY_REVISION = UUID(int=303)
A_RESEARCH = UUID(int=401)
C_RESEARCH = UUID(int=403)
A_RESEARCH_REVISION = UUID(int=501)
C_RESEARCH_REVISION = UUID(int=503)
A_SEMANTIC_REVISION = UUID(int=601)
B_SEMANTIC_REVISION = UUID(int=602)
C_MISMATCHED_SEMANTIC_REVISION = UUID(int=603)
BASE_DATE = date(2026, 7, 20)
BASE_TIME = datetime(2026, 7, 20, 8, tzinfo=UTC)


def _header():
    return {
        "candidate_pool_revision_id": POOL_REVISION_ID,
        "candidate_pool_id": POOL_ID,
        "candidate_pool_revision_no": 1,
        "selected_map_revision_id": MAP_REVISION_ID,
        "candidate_pool_title": "Fixture Industry Pool",
        "candidate_pool_scope": "Explicit fixture scope",
        "candidate_pool_information_cutoff_date": BASE_DATE,
        "candidate_pool_recorded_at_utc": BASE_TIME,
        "candidate_pool_supersedes_revision_id": None,
        "case_id": CASE_ID,
        "map_id": MAP_ID,
        "candidate_pool_key": "fixture-pool",
        "candidate_pool_created_at_utc": BASE_TIME - timedelta(hours=2),
        "map_revision_map_id": MAP_ID,
        "map_revision_no": 2,
        "map_revision_title": "Fixture Industry Map",
        "map_revision_scope": "Fixture map scope",
        "map_information_cutoff_date": BASE_DATE,
        "map_recorded_at_utc": BASE_TIME - timedelta(hours=1),
    }


def _membership(
    member_id,
    beneficiary_id,
    beneficiary_revision_id,
    stock_code,
    stock_name,
    stock_basic_record_id,
):
    return {
        "candidate_pool_membership_id": member_id,
        "candidate_pool_revision_id": POOL_REVISION_ID,
        "beneficiary_id": beneficiary_id,
        "beneficiary_revision_id": beneficiary_revision_id,
        "membership_recorded_at_utc": BASE_TIME,
        "beneficiary_case_id": CASE_ID,
        "beneficiary_map_id": MAP_ID,
        "source": "fixture",
        "stock_code": stock_code,
        "beneficiary_created_at_utc": BASE_TIME - timedelta(days=2),
        "beneficiary_revision_no": 1,
        "beneficiary_selected_map_revision_id": MAP_REVISION_ID,
        "stock_basic_record_id": stock_basic_record_id,
        "beneficiary_kind": "direct",
        "beneficiary_assessment_status": "supported",
        "beneficiary_rationale_summary": "fixture rationale",
        "beneficiary_information_cutoff_date": BASE_DATE,
        "beneficiary_recorded_at_utc": BASE_TIME,
        "stock_name": stock_name,
        "exchange": "SZSE",
        "stock_record_source": "fixture",
        "stock_record_code": stock_code,
    }


def _research_root(
    research_id,
    membership_id,
    beneficiary_id,
    beneficiary_revision_id,
    stock_code,
    stock_basic_record_id,
):
    return {
        "company_research_id": research_id,
        "case_id": CASE_ID,
        "map_id": MAP_ID,
        "candidate_pool_id": POOL_ID,
        "candidate_pool_revision_id": POOL_REVISION_ID,
        "candidate_pool_membership_id": membership_id,
        "beneficiary_id": beneficiary_id,
        "beneficiary_revision_id": beneficiary_revision_id,
        "selected_map_revision_id": MAP_REVISION_ID,
        "stock_basic_record_id": stock_basic_record_id,
        "source": "fixture",
        "stock_code": stock_code,
        "created_at_utc": BASE_TIME,
    }


def _research_revision(research_id, revision_id, conclusion="supported"):
    return {
        "company_research_id": research_id,
        "revision_id": revision_id,
        "revision_no": 1,
        "workflow_state": "open",
        "conclusion_status": conclusion,
        "information_cutoff_date": BASE_DATE,
        "recorded_at_utc": BASE_TIME,
        "supersedes_revision_id": None,
    }


def _semantic_revision(
    beneficiary_id,
    profile_revision_id,
    frozen_beneficiary_revision_id,
):
    return {
        "profile_id": UUID(int=700 + beneficiary_id.int),
        "beneficiary_id": beneficiary_id,
        "profile_created_at_utc": BASE_TIME,
        "profile_revision_id": profile_revision_id,
        "revision_no": 1,
        "beneficiary_revision_id": frozen_beneficiary_revision_id,
        "selected_map_revision_id": MAP_REVISION_ID,
        "taxonomy_version": "aquantai.typed-beneficiary-evidence-semantics.v1",
        "overall_status": "supported",
        "information_cutoff_date": BASE_DATE,
        "recorded_at_utc": BASE_TIME,
        "supersedes_revision_id": None,
    }


def _assertion(profile_revision_id, assertion_id, state_code="direct"):
    return {
        "assertion_id": assertion_id,
        "profile_revision_id": profile_revision_id,
        "assertion_key": "exposure",
        "field_kind": "exposure",
        "state_code": state_code,
        "evidence_state": "supported",
        "subject_text": None,
        "map_observation_revision_id": None,
        "position": 0,
    }


def _module_row(research_id, research_revision_id, item_seed, item_key, **fields):
    return {
        "company_research_id": research_id,
        "item_id": UUID(int=item_seed),
        "item_key": item_key,
        "created_at_utc": BASE_TIME,
        "revision_id": UUID(int=item_seed + 1000),
        "revision_no": 1,
        "information_cutoff_date": BASE_DATE,
        "recorded_at_utc": BASE_TIME,
        "supersedes_revision_id": None,
        "company_research_revision_id": research_revision_id,
        **fields,
    }


def _read_set():
    memberships = (
        _membership(
            A_MEMBER,
            A_BENEFICIARY,
            A_BENEFICIARY_REVISION,
            "000002.SZ",
            "Company A",
            11,
        ),
        _membership(
            C_MEMBER,
            C_BENEFICIARY,
            C_BENEFICIARY_REVISION,
            "000003.SZ",
            "Company C",
            13,
        ),
        _membership(
            B_MEMBER,
            B_BENEFICIARY,
            B_BENEFICIARY_REVISION,
            "000001.SZ",
            "Company B",
            12,
        ),
    )
    research_roots = (
        _research_root(
            A_RESEARCH,
            A_MEMBER,
            A_BENEFICIARY,
            A_BENEFICIARY_REVISION,
            "000002.SZ",
            11,
        ),
        _research_root(
            C_RESEARCH,
            C_MEMBER,
            C_BENEFICIARY,
            C_BENEFICIARY_REVISION,
            "000003.SZ",
            13,
        ),
    )
    research_revisions = (
        _research_revision(A_RESEARCH, A_RESEARCH_REVISION),
        _research_revision(C_RESEARCH, C_RESEARCH_REVISION, "disputed"),
    )
    semantic_revisions = (
        _semantic_revision(
            A_BENEFICIARY,
            A_SEMANTIC_REVISION,
            A_BENEFICIARY_REVISION,
        ),
        _semantic_revision(
            B_BENEFICIARY,
            B_SEMANTIC_REVISION,
            B_BENEFICIARY_REVISION,
        ),
        _semantic_revision(
            C_BENEFICIARY,
            C_MISMATCHED_SEMANTIC_REVISION,
            UUID(int=9999),
        ),
    )
    assertions = (
        _assertion(A_SEMANTIC_REVISION, UUID(int=801), "direct"),
        _assertion(B_SEMANTIC_REVISION, UUID(int=802), "conditional"),
        _assertion(C_MISMATCHED_SEMANTIC_REVISION, UUID(int=803), "indirect"),
    )
    modules = {
        "hypothesis": (
            _module_row(
                A_RESEARCH,
                A_RESEARCH_REVISION,
                900,
                "revenue-transmission",
                hypothesis_status="supported",
                direction="positive",
                confidence="high",
            ),
        ),
        "expectation": (
            _module_row(
                A_RESEARCH,
                A_RESEARCH_REVISION,
                901,
                "market-expectation",
                subject="earnings",
                direction="mixed",
                status="supported",
                confidence="medium",
            ),
        ),
        "valuation": (
            _module_row(
                A_RESEARCH,
                A_RESEARCH_REVISION,
                902,
                "valuation-context",
                valuation_method="PE context",
                metric_context="research context only",
                status="supported",
                confidence="medium",
            ),
        ),
        "catalyst": (
            _module_row(
                A_RESEARCH,
                A_RESEARCH_REVISION,
                903,
                "capacity-catalyst",
                catalyst_category="capacity",
                subject="commissioning",
                expected_observation_window="next reporting period",
                status="supported",
                confidence="medium",
            ),
        ),
        "risk": (
            _module_row(
                C_RESEARCH,
                C_RESEARCH_REVISION,
                904,
                "execution-risk",
                risk_category="execution",
                subject="qualification delay",
                thesis_invalidation_condition="approval is withdrawn",
                status="disputed",
                confidence="low",
            ),
        ),
        "industry_judgment": (),
        "company_judgment": (),
    }
    return ComparisonReadSet(
        memberships=memberships,
        research_roots=research_roots,
        research_revisions=research_revisions,
        semantic_revisions=semantic_revisions,
        semantic_assertions=assertions,
        modules=modules,
        query_count=COMPARISON_QUERY_COUNT,
    )


class FakeRepository:
    def __init__(self, header=None, read_set=None):
        self.header = _header() if header is None else header
        self.read_set = _read_set() if read_set is None else read_set
        self.component_calls = 0

    def load_header(self, candidate_pool_revision_id):
        assert candidate_pool_revision_id == POOL_REVISION_ID
        return deepcopy(self.header)

    def load_components(self, candidate_pool_revision_id, **kwargs):
        assert candidate_pool_revision_id == POOL_REVISION_ID
        assert kwargs["as_of_cutoff"] == date(2026, 7, 22)
        assert kwargs["as_of_recorded_at_utc"] == datetime(
            2026, 7, 22, tzinfo=UTC
        )
        self.component_calls += 1
        return deepcopy(self.read_set)


def test_golden_path_keeps_complete_universe_and_missing_components_visible() -> None:
    service = CompanyComparisonQueryService(FakeRepository())

    contract = service.get_comparison(
        POOL_REVISION_ID,
        as_of_cutoff=date(2026, 7, 22),
        as_of_recorded_at_utc=datetime(2026, 7, 22, tzinfo=UTC),
    ).to_dict()

    assert contract["query_count"] == COMPARISON_QUERY_COUNT == 13
    assert contract["universe"]["member_count"] == 3
    assert [row["identity"]["stock_code"] for row in contract["rows"]] == [
        "000001.SZ",
        "000002.SZ",
        "000003.SZ",
    ]

    company_b, company_a, company_c = contract["rows"]
    assert company_b["typed_semantics"]["state"] == "available"
    assert company_b["company_research"]["state"] == "missing"

    assert company_a["typed_semantics"]["state"] == "available"
    assert company_a["company_research"]["state"] == "available"
    valuation = company_a["company_research"]["components"]["valuation_contexts"]
    assert valuation["state"] == "available"
    assert valuation["items"][0]["valuation_method"] == "PE context"
    assert "observed_value" not in valuation["items"][0]

    assert company_c["typed_semantics"]["state"] == "historical_mismatch"
    assert company_c["typed_semantics"]["assertions"] == {}
    assert company_c["company_research"]["state"] == "disputed"
    assert company_c["company_research"]["components"]["risks"]["state"] == "disputed"

    assert contract["notices"]["no_scores_rankings_or_priority_labels"] is True
    assert contract["notices"]["no_valuation_attractiveness_or_expectation_gap"] is True


def test_invalid_chronology_fails_before_component_projection() -> None:
    repository = FakeRepository()
    service = CompanyComparisonQueryService(repository)

    with pytest.raises(CompanyComparisonSelectorError):
        service.get_comparison(
            POOL_REVISION_ID,
            as_of_cutoff=date(2026, 7, 19),
            as_of_recorded_at_utc=datetime(2026, 7, 22, tzinfo=UTC),
        )

    assert repository.component_calls == 0


def test_non_utc_recorded_boundary_is_rejected() -> None:
    repository = FakeRepository()
    service = CompanyComparisonQueryService(repository)

    with pytest.raises(CompanyComparisonSelectorError):
        service.get_comparison(
            POOL_REVISION_ID,
            as_of_cutoff=date(2026, 7, 22),
            as_of_recorded_at_utc=datetime(
                2026, 7, 22, 8, tzinfo=timezone(timedelta(hours=8))
            ),
        )

    assert repository.component_calls == 0


def test_company_research_frozen_boundary_mismatch_fails_whole_projection() -> None:
    read_set = _read_set()
    roots = [dict(row) for row in read_set.research_roots]
    roots[0]["beneficiary_revision_id"] = UUID(int=9998)
    bad_read_set = ComparisonReadSet(
        memberships=read_set.memberships,
        research_roots=tuple(roots),
        research_revisions=read_set.research_revisions,
        semantic_revisions=read_set.semantic_revisions,
        semantic_assertions=read_set.semantic_assertions,
        modules=read_set.modules,
        query_count=read_set.query_count,
    )
    service = CompanyComparisonQueryService(
        FakeRepository(read_set=bad_read_set)
    )

    with pytest.raises(CompanyComparisonDataError, match="frozen beneficiary_revision_id"):
        service.get_comparison(
            POOL_REVISION_ID,
            as_of_cutoff=date(2026, 7, 22),
            as_of_recorded_at_utc=datetime(2026, 7, 22, tzinfo=UTC),
        )

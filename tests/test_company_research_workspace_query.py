from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from industry_alpha.company_research_workspace_query import (
    CompanyResearchWorkspaceQueryService,
)
from industry_alpha.company_research_workspace_repository import (
    CompanyResearchWorkspaceDataError,
    WorkspaceReadSet,
)

UTC = timezone.utc
NOW = datetime(2026, 7, 21, 2, 0, tzinfo=UTC)
CUTOFF = date(2026, 7, 21)


def valid_root() -> dict:
    return {
        "company_research_id": UUID(int=1),
        "case_id": UUID(int=2),
        "map_id": UUID(int=3),
        "candidate_pool_id": UUID(int=4),
        "candidate_pool_revision_id": UUID(int=5),
        "candidate_pool_membership_id": UUID(int=6),
        "beneficiary_id": UUID(int=7),
        "beneficiary_revision_id": UUID(int=8),
        "selected_map_revision_id": UUID(int=9),
        "stock_basic_record_id": 10,
        "source": "fixture",
        "stock_code": "000001.SZ",
        "created_at_utc": NOW,
        "candidate_pool_key": "memory-beneficiaries",
        "candidate_pool_created_at_utc": NOW,
        "candidate_pool_revision_no": 1,
        "pool_selected_map_revision_id": UUID(int=9),
        "candidate_pool_title": "Memory beneficiaries",
        "candidate_pool_scope": "Persisted Stage 1 pool",
        "candidate_pool_information_cutoff_date": date(2026, 7, 20),
        "candidate_pool_recorded_at_utc": NOW,
        "candidate_pool_supersedes_revision_id": None,
        "membership_recorded_at_utc": NOW,
        "beneficiary_case_id": UUID(int=2),
        "beneficiary_map_id": UUID(int=3),
        "beneficiary_source": "fixture",
        "beneficiary_stock_code": "000001.SZ",
        "beneficiary_created_at_utc": NOW,
        "beneficiary_revision_no": 2,
        "beneficiary_selected_map_revision_id": UUID(int=9),
        "beneficiary_stock_basic_record_id": 10,
        "beneficiary_kind": "direct",
        "beneficiary_assessment_status": "supported",
        "beneficiary_rationale_summary": "Exact Stage 1 frozen rationale",
        "beneficiary_information_cutoff_date": date(2026, 7, 20),
        "beneficiary_recorded_at_utc": NOW,
        "beneficiary_supersedes_revision_id": UUID(int=80),
        "map_revision_map_id": UUID(int=3),
        "map_revision_no": 2,
        "map_revision_title": "Memory industry chain",
        "map_revision_scope": "Frozen map scope",
        "map_information_cutoff_date": date(2026, 7, 20),
        "map_recorded_at_utc": NOW,
        "map_supersedes_revision_id": UUID(int=90),
        "ingestion_run_id": 11,
        "stock_record_code": "000001.SZ",
        "stock_name": "Fixture Company",
        "exchange": "SZSE",
        "provider_industry": "Semiconductors",
        "listing_date": date(2000, 1, 1),
        "stock_status": "listed",
        "stock_record_source": "fixture",
        "ingestion_series_key": "a" * 64,
        "ingestion_provider": "fixture-provider",
        "ingestion_dataset": "stock_basic",
        "ingestion_information_cutoff_date": date(2026, 7, 20),
        "ingestion_completed_at_utc": NOW,
        "ingestion_status": "succeeded",
    }


def research_revision(revision_id: int, revision_no: int) -> dict:
    return {
        "company_research_id": UUID(int=1),
        "revision_id": UUID(int=revision_id),
        "revision_no": revision_no,
        "workflow_state": "open",
        "conclusion_status": "unassessed",
        "research_question": "How does the industry bottleneck transmit?",
        "summary": f"Research revision {revision_no}",
        "information_cutoff_date": date(2026, 7, 19 + revision_no),
        "recorded_at_utc": NOW,
        "supersedes_revision_id": None if revision_no == 1 else UUID(int=201),
    }


def expectation_row() -> dict:
    return {
        "item_id": UUID(int=301),
        "company_research_id": UUID(int=1),
        "item_key": "market-demand-expectation",
        "created_at_utc": NOW,
        "revision_id": UUID(int=302),
        "company_research_revision_id": UUID(int=201),
        "revision_no": 1,
        "subject": "Demand expectation",
        "period_horizon": "12 months",
        "expectation_kind": "research_assumption",
        "direction": "positive",
        "status": "supported",
        "confidence": "medium",
        "basis": "Persisted evidence-bound basis",
        "information_cutoff_date": date(2026, 7, 20),
        "recorded_at_utc": NOW,
        "supersedes_revision_id": None,
    }


def expectation_claim() -> dict:
    return {
        "module": "expectation",
        "owner_revision_id": UUID(int=302),
        "claim_link_id": UUID(int=401),
        "claim_revision_id": UUID(int=402),
        "claim_id": UUID(int=403),
        "claim_key": "demand-growth",
        "claim_revision_no": 1,
        "statement": "Demand is expected to grow.",
        "claim_kind": "inference",
        "claim_status": "supported",
        "inference_confidence": "medium",
        "information_cutoff_date": date(2026, 7, 20),
        "claim_recorded_at_utc": NOW,
        "recorded_at_utc": NOW,
    }


class StubRepository:
    def __init__(self, rows: WorkspaceReadSet):
        self.rows = rows

    def list_selector_roots(self, *, as_of_cutoff=None):
        return (valid_root(),)

    def list_research_revisions(self, _ids, *, as_of_cutoff=None):
        return (research_revision(201, 1), research_revision(202, 2))

    def list_availability(self, _ids, *, as_of_cutoff=None):
        return ({"company_research_id": UUID(int=1), "module": "expectation", "visible_count": 1},)

    def load_workspace(self, _research_id):
        return self.rows


def workspace_rows(**overrides) -> WorkspaceReadSet:
    values = {
        "root": valid_root(),
        "research_revisions": (research_revision(201, 1), research_revision(202, 2)),
        "verification_items": (),
        "hypotheses": (),
        "expectations": (expectation_row(),),
        "valuations": (),
        "catalysts": (),
        "risks": (),
        "industry_judgments": (),
        "company_judgments": (),
        "frozen_links": (),
        "claim_links": (expectation_claim(),),
        "evidence_links": (),
        "handoff_links": (),
        "query_count": 14,
    }
    values.update(overrides)
    return WorkspaceReadSet(**values)


def test_selector_preserves_exact_identity_and_neutral_availability_counts() -> None:
    payload = CompanyResearchWorkspaceQueryService(StubRepository(workspace_rows())).list_research(as_of_cutoff=CUTOFF).to_dict()
    assert payload["research"][0]["company_research_id"] == str(UUID(int=1))
    assert payload["research"][0]["stock_code"] == "000001.SZ"
    assert payload["research"][0]["latest_revision"]["revision_id"] == str(UUID(int=202))
    assert payload["research"][0]["availability"]["expectation_count"] == 1
    assert payload["notices"]["no_scores_rankings_or_recommendations"] is True


def test_workspace_exposes_historical_mismatch_and_explicit_empty_modules() -> None:
    payload = CompanyResearchWorkspaceQueryService(StubRepository(workspace_rows())).get_workspace(UUID(int=1), as_of_cutoff=CUTOFF).to_dict()
    expectation = payload["expectations"][0]["latest_revision"]
    assert expectation["company_research_revision_id"] == str(UUID(int=201))
    assert expectation["historical_revision_mismatch"] is True
    assert expectation["evidence_summary"]["missing_evidence_count"] == 1
    assert payload["valuation_observations"] == ()
    assert payload["catalysts"] == ()
    assert payload["risks"] == ()
    assert payload["company_research"]["latest_revision"]["revision_id"] == str(UUID(int=202))
    assert payload["frozen_stage1"]["beneficiary_revision"]["beneficiary_kind"] == "direct"


def test_cutoff_invisible_frozen_research_revision_fails_closed() -> None:
    row = expectation_row()
    row["company_research_revision_id"] = UUID(int=999)
    service = CompanyResearchWorkspaceQueryService(StubRepository(workspace_rows(expectations=(row,))))
    with pytest.raises(CompanyResearchWorkspaceDataError, match="cutoff-invisible"):
        service.get_workspace(UUID(int=1), as_of_cutoff=CUTOFF)


def test_exact_stock_provenance_mismatch_fails_closed() -> None:
    root = valid_root()
    root["stock_record_code"] = "999999.SZ"
    service = CompanyResearchWorkspaceQueryService(StubRepository(workspace_rows(root=root)))
    with pytest.raises(CompanyResearchWorkspaceDataError, match="provenance"):
        service.get_workspace(UUID(int=1), as_of_cutoff=CUTOFF)

from datetime import date, datetime, timezone
from uuid import UUID

from industry_alpha.beneficiary_workspace_repository import (
    BENEFICIARY_KIND_ORDER,
    IndustryBeneficiaryWorkspaceRepository,
)

UTC = timezone.utc
NOW = datetime(2026, 7, 21, 1, 0, tzinfo=UTC)


class FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return iter(self._rows)


class FakeSession:
    def __init__(self, result_sets):
        self._result_sets = list(result_sets)
        self.execute_count = 0

    def execute(self, _statement):
        self.execute_count += 1
        return FakeResult(self._result_sets.pop(0))


def test_selector_uses_one_scalar_query_and_latest_visible_revision() -> None:
    map_id = UUID(int=1)
    session = FakeSession(
        [
            [
                {
                    "map_id": map_id,
                    "case_id": UUID(int=2),
                    "map_key": "memory",
                    "created_at_utc": NOW,
                    "revision_id": UUID(int=3),
                    "revision_no": 1,
                    "title": "Memory chain",
                    "scope": "Initial",
                    "information_cutoff_date": date(2026, 7, 1),
                    "recorded_at_utc": NOW,
                    "supersedes_revision_id": None,
                },
                {
                    "map_id": map_id,
                    "case_id": UUID(int=2),
                    "map_key": "memory",
                    "created_at_utc": NOW,
                    "revision_id": UUID(int=4),
                    "revision_no": 2,
                    "title": "Memory chain updated",
                    "scope": "Updated",
                    "information_cutoff_date": date(2026, 7, 20),
                    "recorded_at_utc": NOW,
                    "supersedes_revision_id": UUID(int=3),
                },
            ]
        ]
    )

    rows = IndustryBeneficiaryWorkspaceRepository(session).list_map_selectors(
        as_of_cutoff=date(2026, 7, 21)
    )

    assert session.execute_count == 1
    assert len(rows) == 1
    assert rows[0].revision_no == 2
    assert rows[0].title == "Memory chain updated"


def test_workspace_overview_has_fixed_three_scalar_queries_and_exact_stage2_history() -> None:
    map_id = UUID(int=10)
    first_beneficiary = UUID(int=11)
    second_beneficiary = UUID(int=12)
    older_revision = UUID(int=21)
    latest_revision = UUID(int=22)
    second_revision = UUID(int=23)
    map_revision_id = UUID(int=30)
    session = FakeSession(
        [
            [
                {
                    "beneficiary_id": first_beneficiary,
                    "case_id": UUID(int=40),
                    "map_id": map_id,
                    "source": "fixture",
                    "stock_code": "000002.SZ",
                    "created_at_utc": NOW,
                    "revision_id": older_revision,
                    "revision_no": 1,
                    "selected_map_revision_id": map_revision_id,
                    "stock_basic_record_id": 101,
                    "beneficiary_kind": "secondary",
                    "assessment_status": "draft",
                    "rationale_summary": "Older rationale",
                    "information_cutoff_date": date(2026, 7, 10),
                    "recorded_at_utc": NOW,
                    "supersedes_revision_id": None,
                },
                {
                    "beneficiary_id": first_beneficiary,
                    "case_id": UUID(int=40),
                    "map_id": map_id,
                    "source": "fixture",
                    "stock_code": "000002.SZ",
                    "created_at_utc": NOW,
                    "revision_id": latest_revision,
                    "revision_no": 2,
                    "selected_map_revision_id": map_revision_id,
                    "stock_basic_record_id": 101,
                    "beneficiary_kind": "secondary",
                    "assessment_status": "supported",
                    "rationale_summary": "Latest rationale",
                    "information_cutoff_date": date(2026, 7, 20),
                    "recorded_at_utc": NOW,
                    "supersedes_revision_id": older_revision,
                },
                {
                    "beneficiary_id": second_beneficiary,
                    "case_id": UUID(int=40),
                    "map_id": map_id,
                    "source": "fixture",
                    "stock_code": "000001.SZ",
                    "created_at_utc": NOW,
                    "revision_id": second_revision,
                    "revision_no": 1,
                    "selected_map_revision_id": map_revision_id,
                    "stock_basic_record_id": 102,
                    "beneficiary_kind": "direct",
                    "assessment_status": "disputed",
                    "rationale_summary": "Direct rationale",
                    "information_cutoff_date": date(2026, 7, 20),
                    "recorded_at_utc": NOW,
                    "supersedes_revision_id": None,
                },
            ],
            [
                {
                    "stock_basic_record_id": 101,
                    "ingestion_run_id": 501,
                    "stock_record_code": "000002.SZ",
                    "stock_name": "Company B",
                    "exchange": "SZSE",
                    "provider_industry": "Provider sector",
                    "listing_date": date(2000, 1, 1),
                    "stock_status": "listed",
                    "stock_record_source": "fixture",
                    "ingestion_series_key": "a" * 64,
                    "ingestion_provider": "fixture-provider",
                    "ingestion_information_cutoff_date": date(2026, 7, 20),
                    "ingestion_completed_at_utc": NOW,
                    "ingestion_status": "succeeded",
                },
                {
                    "stock_basic_record_id": 102,
                    "ingestion_run_id": 502,
                    "stock_record_code": "000001.SZ",
                    "stock_name": "Company A",
                    "exchange": "SZSE",
                    "provider_industry": "",
                    "listing_date": None,
                    "stock_status": "listed",
                    "stock_record_source": "fixture",
                    "ingestion_series_key": "b" * 64,
                    "ingestion_provider": "fixture-provider",
                    "ingestion_information_cutoff_date": date(2026, 7, 20),
                    "ingestion_completed_at_utc": NOW,
                    "ingestion_status": "succeeded",
                },
            ],
            [
                {
                    "company_research_id": UUID(int=60),
                    "beneficiary_id": first_beneficiary,
                    "stage2_frozen_beneficiary_revision_id": older_revision,
                    "stage2_selected_map_revision_id": map_revision_id,
                    "stage2_stock_basic_record_id": 101,
                    "stage2_source": "fixture",
                    "stage2_stock_code": "000002.SZ",
                    "company_research_revision_id": UUID(int=61),
                    "company_research_revision_no": 1,
                    "company_research_workflow_state": "open",
                    "company_research_conclusion_status": "unassessed",
                    "company_research_question": "How does the bottleneck transmit?",
                    "company_research_summary": "Historical hypothesis context.",
                    "company_research_information_cutoff_date": date(2026, 7, 10),
                    "company_research_recorded_at_utc": NOW,
                    "company_research_supersedes_revision_id": None,
                }
            ],
        ]
    )

    rows = IndustryBeneficiaryWorkspaceRepository(session).list_beneficiaries(
        map_id,
        as_of_cutoff=date(2026, 7, 21),
        visible_map_revision_ids={map_revision_id},
    )

    assert session.execute_count == 3
    assert len(rows) == 2
    assert [BENEFICIARY_KIND_ORDER[row.beneficiary_kind] for row in rows] == [0, 1]
    direct, secondary = rows
    assert direct.company_research_id is None
    assert secondary.revision_id == latest_revision
    assert secondary.stage2_frozen_beneficiary_revision_id == older_revision
    assert secondary.company_research_id == UUID(int=60)
    assert secondary.ingestion_run_id == 501


def test_empty_beneficiary_set_still_uses_fixed_queries_without_fallback() -> None:
    session = FakeSession([[], [], []])

    rows = IndustryBeneficiaryWorkspaceRepository(session).list_beneficiaries(
        UUID(int=80),
        as_of_cutoff=None,
        visible_map_revision_ids={UUID(int=81)},
    )

    assert rows == ()
    assert session.execute_count == 3

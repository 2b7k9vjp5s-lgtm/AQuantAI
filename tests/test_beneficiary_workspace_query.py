from datetime import date, datetime, timezone
from uuid import UUID

from industry_alpha.beneficiary_workspace_query import (
    IndustryBeneficiaryWorkspaceQueryService,
)
from industry_alpha.beneficiary_workspace_repository import (
    BeneficiaryOverviewRow,
    MapSelectorRow,
)

UTC = timezone.utc
NOW = datetime(2026, 7, 21, 1, 0, tzinfo=UTC)


class FakeMapContract:
    def to_dict(self):
        return {
            "industry_map": {
                "map_id": str(UUID(int=1)),
                "case_id": str(UUID(int=2)),
                "map_key": "memory",
                "created_at_utc": "2026-07-21T01:00:00Z",
            },
            "latest_revision": {
                "revision_id": str(UUID(int=3)),
                "revision_no": 2,
                "title": "Memory chain",
                "scope": "Semiconductor memory",
                "information_cutoff_date": "2026-07-20",
                "recorded_at_utc": "2026-07-21T01:00:00Z",
                "supersedes_revision_id": str(UUID(int=4)),
                "frozen_membership": {
                    "node_revision_ids": [],
                    "relationship_revision_ids": [],
                    "observation_revision_ids": [],
                },
            },
            "revision_history": [
                {
                    "revision_id": str(UUID(int=4)),
                    "revision_no": 1,
                    "title": "Memory chain",
                    "scope": "Initial",
                    "information_cutoff_date": "2026-07-10",
                    "recorded_at_utc": "2026-07-11T01:00:00Z",
                    "supersedes_revision_id": None,
                    "frozen_membership": {
                        "node_revision_ids": [],
                        "relationship_revision_ids": [],
                        "observation_revision_ids": [],
                    },
                },
                {
                    "revision_id": str(UUID(int=3)),
                    "revision_no": 2,
                    "title": "Memory chain",
                    "scope": "Semiconductor memory",
                    "information_cutoff_date": "2026-07-20",
                    "recorded_at_utc": "2026-07-21T01:00:00Z",
                    "supersedes_revision_id": str(UUID(int=4)),
                    "frozen_membership": {
                        "node_revision_ids": [],
                        "relationship_revision_ids": [],
                        "observation_revision_ids": [],
                    },
                },
            ],
            "frozen_snapshot": {
                "map_revision_id": str(UUID(int=3)),
                "nodes": [],
                "relationships": [],
                "observations": [
                    {
                        "observation_id": str(UUID(int=5)),
                        "observation_key": "demand",
                        "observation_kind": "driver",
                        "created_at_utc": "2026-07-20T01:00:00Z",
                        "revision": {
                            "revision_id": str(UUID(int=6)),
                            "revision_no": 1,
                            "title": "AI demand",
                            "description": "Demand expansion",
                            "assertion_status": "supported",
                            "information_cutoff_date": "2026-07-20",
                            "recorded_at_utc": "2026-07-21T01:00:00Z",
                        },
                    }
                ],
                "counts": {
                    "nodes": 0,
                    "relationships": 0,
                    "drivers": 1,
                    "bottlenecks": 0,
                    "value_pool_shifts": 0,
                },
            },
            "evidence_grade_summary": {"A": 1, "B": 0, "C": 0, "D": 0},
            "conflicts": [],
            "missing_evidence": [],
            "notices": {},
        }


class FakeMapService:
    def get_map(self, map_id, *, as_of_cutoff=None):
        assert map_id == UUID(int=1)
        assert as_of_cutoff == date(2026, 7, 21)
        return FakeMapContract()


class FakeRepository:
    def __init__(self, rows):
        self.rows = rows
        self.visible_revision_ids = None

    def list_map_selectors(self, *, as_of_cutoff=None):
        return (
            MapSelectorRow(
                map_id=UUID(int=1),
                case_id=UUID(int=2),
                map_key="memory",
                created_at_utc=NOW,
                revision_id=UUID(int=3),
                revision_no=2,
                title="Memory chain",
                scope="Semiconductor memory",
                information_cutoff_date=date(2026, 7, 20),
                recorded_at_utc=NOW,
                supersedes_revision_id=UUID(int=4),
            ),
        )

    def list_beneficiaries(
        self, map_id, *, as_of_cutoff, visible_map_revision_ids
    ):
        assert map_id == UUID(int=1)
        self.visible_revision_ids = visible_map_revision_ids
        return self.rows


def make_row(
    *,
    beneficiary_id: int,
    stock_code: str,
    kind: str,
    research: bool,
    frozen_revision: int | None = None,
) -> BeneficiaryOverviewRow:
    revision_id = UUID(int=beneficiary_id + 100)
    return BeneficiaryOverviewRow(
        beneficiary_id=UUID(int=beneficiary_id),
        case_id=UUID(int=2),
        map_id=UUID(int=1),
        source="fixture",
        stock_code=stock_code,
        created_at_utc=NOW,
        revision_id=revision_id,
        revision_no=2,
        selected_map_revision_id=UUID(int=3),
        stock_basic_record_id=beneficiary_id,
        beneficiary_kind=kind,
        assessment_status="supported",
        rationale_summary=f"{kind} rationale",
        information_cutoff_date=date(2026, 7, 20),
        recorded_at_utc=NOW,
        supersedes_revision_id=None,
        stock_name=f"Company {beneficiary_id}",
        exchange="SZSE",
        provider_industry="Provider sector",
        listing_date=None,
        stock_status="listed",
        ingestion_run_id=beneficiary_id + 500,
        ingestion_series_key="a" * 64,
        ingestion_provider="fixture-provider",
        ingestion_information_cutoff_date=date(2026, 7, 20),
        ingestion_completed_at_utc=NOW,
        company_research_id=UUID(int=beneficiary_id + 200) if research else None,
        stage2_frozen_beneficiary_revision_id=(
            UUID(int=frozen_revision) if frozen_revision is not None else None
        ),
        stage2_selected_map_revision_id=UUID(int=3) if research else None,
        stage2_stock_basic_record_id=beneficiary_id if research else None,
        company_research_revision_id=UUID(int=beneficiary_id + 300) if research else None,
        company_research_revision_no=1 if research else None,
        company_research_workflow_state="open" if research else None,
        company_research_conclusion_status="unassessed" if research else None,
        company_research_question="Transmission question" if research else None,
        company_research_summary="Summary" if research else None,
        company_research_information_cutoff_date=(
            date(2026, 7, 10) if research else None
        ),
        company_research_recorded_at_utc=NOW if research else None,
        company_research_supersedes_revision_id=None,
    )


def test_map_selector_contract_is_scalar_and_neutral() -> None:
    service = IndustryBeneficiaryWorkspaceQueryService(
        FakeRepository(()), FakeMapService()
    )

    payload = service.list_maps(
        as_of_cutoff=date(2026, 7, 21)
    ).to_dict()

    assert payload["maps"][0]["map_key"] == "memory"
    assert payload["maps"][0]["latest_revision"]["revision_no"] == 2
    assert payload["notices"]["not_investment_advice"] is True


def test_workspace_preserves_raw_taxonomy_and_visible_historical_mismatch() -> None:
    direct = make_row(
        beneficiary_id=10,
        stock_code="000001.SZ",
        kind="direct",
        research=False,
    )
    secondary = make_row(
        beneficiary_id=20,
        stock_code="000002.SZ",
        kind="secondary",
        research=True,
        frozen_revision=999,
    )
    repository = FakeRepository((direct, secondary))
    service = IndustryBeneficiaryWorkspaceQueryService(
        repository, FakeMapService()
    )

    payload = service.get_workspace(
        UUID(int=1), as_of_cutoff=date(2026, 7, 21)
    ).to_dict()

    assert repository.visible_revision_ids == {UUID(int=3), UUID(int=4)}
    assert [item["latest_revision"]["beneficiary_kind"] for item in payload["beneficiaries"]] == [
        "direct",
        "secondary",
    ]
    assert payload["beneficiaries"][0]["company_research"] is None
    research = payload["beneficiaries"][1]["company_research"]
    assert research["historical_revision_mismatch"] is True
    assert "未自动重绑" in research["history_notice"]
    assert payload["notices"]["complete_set_meaning"].startswith(
        "The company table is the complete"
    )


def test_workspace_empty_set_remains_empty() -> None:
    payload = IndustryBeneficiaryWorkspaceQueryService(
        FakeRepository(()), FakeMapService()
    ).get_workspace(
        UUID(int=1), as_of_cutoff=date(2026, 7, 21)
    ).to_dict()

    assert payload["beneficiaries"] == ()
    assert "valuation" in " ".join(payload["notices"]["unsupported_fields"])

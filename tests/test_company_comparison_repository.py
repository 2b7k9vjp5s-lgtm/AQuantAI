from datetime import date, datetime, timezone
from uuid import UUID

from industry_alpha.company_comparison_repository import (
    COMPARISON_QUERY_COUNT,
    CompanyComparisonRepository,
)


class StubResult:
    def __init__(self, rows):
        self._rows = rows

    def mappings(self):
        return iter(self._rows)


class StubSession:
    def __init__(self, result_sets):
        self._result_sets = list(result_sets)
        self.execute_count = 0

    def execute(self, _statement):
        self.execute_count += 1
        return StubResult(self._result_sets.pop(0))


def _component_results(member_count: int):
    memberships = [
        {
            "candidate_pool_membership_id": UUID(int=100 + index),
            "beneficiary_id": UUID(int=200 + index),
        }
        for index in range(member_count)
    ]
    research_roots = [
        {
            "company_research_id": UUID(int=300 + index),
            "candidate_pool_membership_id": UUID(int=100 + index),
        }
        for index in range(member_count)
    ]
    research_revisions = [
        {
            "company_research_id": UUID(int=300 + index),
            "revision_id": UUID(int=400 + index),
        }
        for index in range(member_count)
    ]
    semantic_revisions = [
        {
            "beneficiary_id": UUID(int=200 + index),
            "profile_revision_id": UUID(int=500 + index),
        }
        for index in range(member_count)
    ]
    semantic_assertions = [
        {
            "profile_revision_id": UUID(int=500 + index),
            "assertion_id": UUID(int=600 + index),
        }
        for index in range(member_count)
    ]
    module_rows = [
        [
            {
                "company_research_id": UUID(int=300 + index),
                "item_id": UUID(int=700 + module_offset * 100 + index),
            }
            for index in range(member_count)
        ]
        for module_offset in range(7)
    ]
    results = [
        memberships,
        research_roots,
        research_revisions,
        semantic_revisions,
        semantic_assertions,
        *module_rows,
    ]
    assert len(results) == COMPARISON_QUERY_COUNT - 1 == 12
    return results


def test_full_comparison_query_count_is_constant_under_member_growth() -> None:
    cutoff = date(2026, 7, 22)
    recorded = datetime(2026, 7, 22, tzinfo=timezone.utc)
    pool_revision_id = UUID(int=1)

    small_session = StubSession(
        [[{"candidate_pool_revision_id": pool_revision_id}], *_component_results(1)]
    )
    large_session = StubSession(
        [[{"candidate_pool_revision_id": pool_revision_id}], *_component_results(50)]
    )

    small_repository = CompanyComparisonRepository(small_session)
    large_repository = CompanyComparisonRepository(large_session)

    assert small_repository.load_header(pool_revision_id) is not None
    assert large_repository.load_header(pool_revision_id) is not None
    small = small_repository.load_components(
        pool_revision_id,
        as_of_cutoff=cutoff,
        as_of_recorded_at_utc=recorded,
    )
    large = large_repository.load_components(
        pool_revision_id,
        as_of_cutoff=cutoff,
        as_of_recorded_at_utc=recorded,
    )

    assert small.query_count == large.query_count == COMPARISON_QUERY_COUNT == 13
    assert small_session.execute_count == large_session.execute_count == 13
    assert len(small.memberships) == 1
    assert len(large.memberships) == 50


def test_missing_pool_stops_after_header_query() -> None:
    session = StubSession([[]])
    repository = CompanyComparisonRepository(session)

    assert repository.load_header(UUID(int=999)) is None
    assert session.execute_count == 1

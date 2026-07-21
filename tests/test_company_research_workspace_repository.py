from uuid import UUID

from industry_alpha.company_research_workspace_repository import (
    SELECTOR_QUERY_COUNT,
    WORKSPACE_QUERY_COUNT,
    CompanyResearchWorkspaceRepository,
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


def test_selector_uses_three_fixed_scalar_queries() -> None:
    research_id = UUID(int=1)
    session = StubSession([
        [{"company_research_id": research_id}],
        [{"company_research_id": research_id, "revision_id": UUID(int=2)}],
        [{"company_research_id": research_id, "module": "expectation", "visible_count": 2}],
    ])
    repository = CompanyResearchWorkspaceRepository(session)
    roots = repository.list_selector_roots()
    research_ids = tuple(row["company_research_id"] for row in roots)
    revisions = repository.list_research_revisions(research_ids)
    availability = repository.list_availability(research_ids)
    assert roots[0]["company_research_id"] == research_id
    assert revisions[0]["revision_id"] == UUID(int=2)
    assert availability[0]["visible_count"] == 2
    assert session.execute_count == SELECTOR_QUERY_COUNT == 3


def _workspace_results(item_count: int):
    research_id = UUID(int=10)
    results = [[{"company_research_id": research_id}]]
    results.append([{"revision_id": UUID(int=100 + i)} for i in range(item_count)])
    results.append([])
    for offset in range(7):
        results.append([{"revision_id": UUID(int=1000 + offset * 100 + i)} for i in range(item_count)])
    results.extend([[], [], [], []])
    assert len(results) == WORKSPACE_QUERY_COUNT
    return results


def test_workspace_query_count_is_constant_under_row_growth() -> None:
    small_session = StubSession(_workspace_results(1))
    large_session = StubSession(_workspace_results(50))
    small = CompanyResearchWorkspaceRepository(small_session).load_workspace(UUID(int=10))
    large = CompanyResearchWorkspaceRepository(large_session).load_workspace(UUID(int=10))
    assert small.query_count == large.query_count == WORKSPACE_QUERY_COUNT == 14
    assert small_session.execute_count == large_session.execute_count == 14
    assert len(large.hypotheses) == 50


def test_missing_identity_stops_after_one_root_query() -> None:
    session = StubSession([[]])
    rows = CompanyResearchWorkspaceRepository(session).load_workspace(UUID(int=999))
    assert rows.root is None
    assert rows.query_count == 1
    assert session.execute_count == 1

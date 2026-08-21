from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_candidate_review_requires_explicit_case_and_map_revision_pair() -> None:
    html = (ROOT / "industry_analysis/static/candidate_review.html").read_text(
        encoding="utf-8"
    )
    script = (ROOT / "industry_analysis/static/candidate_review.js").read_text(
        encoding="utf-8"
    )

    assert 'id="owner-context-fieldset"' in html
    assert 'id="owner-context-options"' in html
    assert "Case Revision + Map Revision" in html
    assert 'aquantai.industry-thesis-acceptance-plan.v3' in script
    assert "/owner-context-options?" in script
    assert 'name = "owner-context-pair"' in script
    assert "research_case_revision_id: selected.dataset.researchCaseRevisionId" in script
    assert "industry_map_revision_id: selected.dataset.industryMapRevisionId" in script
    assert "owner_context: ownerContext" in script
    assert "请先明确选择一组 Case Revision + Map Revision" in script
    assert ".checked = true" not in script
    assert "items[0]" not in script
    assert "innerHTML" not in script
    assert "eval(" not in script


def test_review_result_activates_v3_and_renders_frozen_context() -> None:
    script = (ROOT / "industry_analysis/static/review_result.js").read_text(
        encoding="utf-8"
    )

    assert 'aquantai.industry-thesis-acceptance-plan.v3' in script
    assert "result.owner_context.research_case_revision_id" in script
    assert "result.owner_context.industry_map_revision_id" in script
    assert "innerHTML" not in script
    assert "eval(" not in script

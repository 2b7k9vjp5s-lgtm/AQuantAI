"""One-time deterministic patch for supported evidence-quality overlap."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected patch anchor missing in {path}")
    target.write_text(text.replace(old, new), encoding="utf-8")


replace(
    "industry_alpha/investment_candidate_commands.py",
    '''    other_claims = {\n        link.claim_revision_id\n        for link in links\n        if link.component_revision_id != quality.id and link.claim_revision_id is not None\n    }\n    other_evidence = {\n        link.evidence_id\n        for link in links\n        if link.component_revision_id != quality.id and link.evidence_id is not None\n    }\n    if not quality_claims.intersection(other_claims) or not quality_evidence.intersection(other_evidence):\n''',
    '''    supported_other_ids = {\n        revision.id\n        for code, revision in components.items()\n        if code != "evidence_quality" and revision.assessment_state == "supported"\n    }\n    other_claims = {\n        link.claim_revision_id\n        for link in links\n        if link.component_revision_id in supported_other_ids and link.claim_revision_id is not None\n    }\n    other_evidence = {\n        link.evidence_id\n        for link in links\n        if link.component_revision_id in supported_other_ids and link.evidence_id is not None\n    }\n    if (\n        not quality_claims\n        or not quality_evidence\n        or not quality_claims.issubset(other_claims)\n        or not quality_evidence.issubset(other_evidence)\n    ):\n''',
)

replace(
    "tests/test_investment_candidate_models.py",
    '''    commands._validate_evidence_quality_overlap(_ScalarsSession(rows), components)\n    with pytest.raises(InvestmentCandidateError, match="reuse exact claim and evidence"):\n        commands._validate_evidence_quality_overlap(_ScalarsSession(rows[:2]), components)\n''',
    '''    commands._validate_evidence_quality_overlap(_ScalarsSession(rows), components)\n    with pytest.raises(InvestmentCandidateError, match="reuse exact claim and evidence"):\n        commands._validate_evidence_quality_overlap(_ScalarsSession(rows[:2]), components)\n    components["industry_opportunity"].assessment_state = "missing"\n    with pytest.raises(InvestmentCandidateError, match="reuse exact claim and evidence"):\n        commands._validate_evidence_quality_overlap(_ScalarsSession(rows), components)\n''',
)

for relative in (
    "industry_alpha/investment_candidate_commands.py",
    "tests/test_investment_candidate_models.py",
):
    source = (ROOT / relative).read_text(encoding="utf-8")
    compile(source, relative, "exec")

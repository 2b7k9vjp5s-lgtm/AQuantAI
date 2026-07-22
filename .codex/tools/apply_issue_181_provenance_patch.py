"""One-time deterministic patch for Issue #181 exact provenance gates."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected patch anchor missing in {path}")
    target.write_text(text.replace(old, new), encoding="utf-8")


commands_path = ROOT / "industry_alpha/investment_candidate_commands.py"
commands_text = commands_path.read_text(encoding="utf-8")

if "Stage2HandoffClaimLink" not in commands_text:
    replace(
        "industry_alpha/investment_candidate_commands.py",
        "    Stage2FinancialHypothesisRevision,\n    Stage2ResearchHypothesisLink,\n",
        "    Stage2FinancialHypothesisRevision,\n"
        "    Stage2HandoffClaimLink,\n"
        "    Stage2HandoffEvidenceLink,\n"
        "    Stage2ResearchHypothesisLink,\n",
    )

if "def _require_exact_research_provenance" not in commands_path.read_text(encoding="utf-8"):
    replace(
        "industry_alpha/investment_candidate_commands.py",
        "\n\ndef _price_graph(\n",
        '''\n\ndef _require_exact_research_provenance(\n    session: Session, *, kind: str, target_id: UUID, company_research_id: UUID\n) -> None:\n    if kind == "claim":\n        linked = session.scalar(\n            select(Stage2HandoffClaimLink.id).where(\n                Stage2HandoffClaimLink.company_research_id == company_research_id,\n                Stage2HandoffClaimLink.claim_revision_id == target_id,\n            )\n        )\n    elif kind == "evidence":\n        linked = session.scalar(\n            select(Stage2HandoffEvidenceLink.id).where(\n                Stage2HandoffEvidenceLink.company_research_id == company_research_id,\n                Stage2HandoffEvidenceLink.evidence_id == target_id,\n            )\n        )\n    else:\n        return\n    if linked is None:\n        raise InvestmentCandidateError(\n            "investment_candidate_input_invalid",\n            f"{kind} input is not frozen by the exact company research handoff",\n        )\n\n\ndef _validate_member_price_manifest(\n    session: Session, manifest: dict[str, Any], cutoff: date, recorded_at: datetime\n) -> None:\n    price_id = manifest["canonical_price_revision_id"]\n    eligibility_id = manifest["comparison_eligibility_revision_id"]\n    if (price_id is None) != (eligibility_id is None):\n        raise InvestmentCandidateError(\n            "investment_candidate_universe_mismatch",\n            "canonical price and comparison eligibility must be supplied as one exact pair",\n        )\n    if price_id is not None and eligibility_id is not None:\n        _price_graph(session, price_id, eligibility_id, cutoff, recorded_at)\n\n\ndef _validate_evidence_quality_overlap(\n    session: Session, components: dict[str, InvestmentCandidateComponentRevision]\n) -> None:\n    quality = components.get("evidence_quality")\n    if quality is None or quality.assessment_state != "supported":\n        return\n    revision_ids = [revision.id for revision in components.values()]\n    links = list(\n        session.scalars(\n            select(InvestmentCandidateComponentInputLink).where(\n                InvestmentCandidateComponentInputLink.component_revision_id.in_(revision_ids)\n            )\n        )\n    )\n    quality_claims = {\n        link.claim_revision_id\n        for link in links\n        if link.component_revision_id == quality.id and link.claim_revision_id is not None\n    }\n    quality_evidence = {\n        link.evidence_id\n        for link in links\n        if link.component_revision_id == quality.id and link.evidence_id is not None\n    }\n    other_claims = {\n        link.claim_revision_id\n        for link in links\n        if link.component_revision_id != quality.id and link.claim_revision_id is not None\n    }\n    other_evidence = {\n        link.evidence_id\n        for link in links\n        if link.component_revision_id != quality.id and link.evidence_id is not None\n    }\n    if not quality_claims.intersection(other_claims) or not quality_evidence.intersection(other_evidence):\n        raise InvestmentCandidateError(\n            "investment_candidate_input_invalid",\n            "supported evidence quality must reuse exact claim and evidence inputs from another supported component",\n        )\n\n\ndef _price_graph(\n''',
    )

commands_text = commands_path.read_text(encoding="utf-8")
if "_require_exact_research_provenance(\n                    session" not in commands_text:
    replace(
        "industry_alpha/investment_candidate_commands.py",
        '''            if kind == "claim":\n                if row.claim_status != "supported":\n                    raise InvestmentCandidateError(\n                        "investment_candidate_input_invalid", "claim revision must be supported"\n                    )\n                claim_ids.add(row.id)\n            if kind == "evidence":\n                evidence_ids.add(row.id)\n''',
        '''            if kind == "claim":\n                if row.claim_status != "supported":\n                    raise InvestmentCandidateError(\n                        "investment_candidate_input_invalid", "claim revision must be supported"\n                    )\n                _require_exact_research_provenance(\n                    session, kind=kind, target_id=row.id, company_research_id=research.id\n                )\n                claim_ids.add(row.id)\n            if kind == "evidence":\n                _require_exact_research_provenance(\n                    session, kind=kind, target_id=row.id, company_research_id=research.id\n                )\n                evidence_ids.add(row.id)\n''',
    )

commands_text = commands_path.read_text(encoding="utf-8")
if "_validate_evidence_quality_overlap(session, components)" not in commands_text:
    replace(
        "industry_alpha/investment_candidate_commands.py",
        '''        result = evaluate_candidate(states)\n        valuation = components.get("valuation_context")\n''',
        '''        _validate_evidence_quality_overlap(session, components)\n        _validate_member_price_manifest(session, manifest, cutoff, recorded_at)\n        result = evaluate_candidate(states)\n        valuation = components.get("valuation_context")\n''',
    )
    replace(
        "industry_alpha/investment_candidate_commands.py",
        '''            _price_graph(session, price_ids[0], eligibility_ids[0], cutoff, recorded_at)\n        return {"manifest": manifest, "components": components, "result": result, "priority_ordinal": None}\n''',
        '''        return {"manifest": manifest, "components": components, "result": result, "priority_ordinal": None}\n''',
    )

models_test_path = ROOT / "tests/test_investment_candidate_models.py"
models_test_text = models_test_path.read_text(encoding="utf-8")
if "test_price_manifest_requires_exact_pair_and_validation" not in models_test_text:
    models_test_text = models_test_text.replace(
        "from uuid import uuid4\n",
        "from datetime import date, datetime, timezone\nfrom types import SimpleNamespace\nfrom uuid import uuid4\n",
    )
    models_test_text = models_test_text.replace(
        "from industry_alpha.investment_candidate_commands import (\n",
        "import industry_alpha.investment_candidate_commands as commands\nfrom industry_alpha.investment_candidate_commands import (\n",
    )
    models_test_text += '''\n\ndef test_price_manifest_requires_exact_pair_and_validation(monkeypatch) -> None:\n    manifest = {\n        "canonical_price_revision_id": uuid4(),\n        "comparison_eligibility_revision_id": None,\n    }\n    with pytest.raises(InvestmentCandidateError, match="one exact pair"):\n        commands._validate_member_price_manifest(\n            object(), manifest, date(2026, 7, 22), datetime(2026, 7, 22, tzinfo=timezone.utc)\n        )\n\n    calls = []\n    monkeypatch.setattr(commands, "_price_graph", lambda *args: calls.append(args))\n    manifest["comparison_eligibility_revision_id"] = uuid4()\n    commands._validate_member_price_manifest(\n        object(), manifest, date(2026, 7, 22), datetime(2026, 7, 22, tzinfo=timezone.utc)\n    )\n    assert len(calls) == 1\n\n\nclass _ScalarSession:\n    def __init__(self, scalar_value):\n        self.scalar_value = scalar_value\n\n    def scalar(self, _statement):\n        return self.scalar_value\n\n\ndef test_claim_and_evidence_require_exact_research_handoff() -> None:\n    with pytest.raises(InvestmentCandidateError, match="exact company research handoff"):\n        commands._require_exact_research_provenance(\n            _ScalarSession(None), kind="claim", target_id=uuid4(), company_research_id=uuid4()\n        )\n    commands._require_exact_research_provenance(\n        _ScalarSession(object()), kind="evidence", target_id=uuid4(), company_research_id=uuid4()\n    )\n\n\nclass _ScalarsSession:\n    def __init__(self, rows):\n        self.rows = rows\n\n    def scalars(self, _statement):\n        return self.rows\n\n\ndef test_supported_evidence_quality_reuses_other_component_provenance() -> None:\n    quality_id = uuid4()\n    other_id = uuid4()\n    claim_id = uuid4()\n    evidence_id = uuid4()\n    components = {\n        "evidence_quality": SimpleNamespace(id=quality_id, assessment_state="supported"),\n        "industry_opportunity": SimpleNamespace(id=other_id, assessment_state="supported"),\n    }\n    rows = [\n        SimpleNamespace(component_revision_id=quality_id, claim_revision_id=claim_id, evidence_id=None),\n        SimpleNamespace(component_revision_id=quality_id, claim_revision_id=None, evidence_id=evidence_id),\n        SimpleNamespace(component_revision_id=other_id, claim_revision_id=claim_id, evidence_id=None),\n        SimpleNamespace(component_revision_id=other_id, claim_revision_id=None, evidence_id=evidence_id),\n    ]\n    commands._validate_evidence_quality_overlap(_ScalarsSession(rows), components)\n    with pytest.raises(InvestmentCandidateError, match="reuse exact claim and evidence"):\n        commands._validate_evidence_quality_overlap(_ScalarsSession(rows[:2]), components)\n'''
    models_test_path.write_text(models_test_text, encoding="utf-8")

for relative in (
    "industry_alpha/investment_candidate_commands.py",
    "tests/test_investment_candidate_models.py",
):
    source = (ROOT / relative).read_text(encoding="utf-8")
    compile(source, relative, "exec")

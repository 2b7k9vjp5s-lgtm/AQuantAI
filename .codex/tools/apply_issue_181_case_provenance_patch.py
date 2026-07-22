"""One-time deterministic patch for case-owned claim/evidence provenance."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "industry_alpha/investment_candidate_commands.py"
text = TARGET.read_text(encoding="utf-8")

replacements = [
    (
        "from industry_alpha.models import ClaimEvidenceLink, ClaimRevision, EvidenceItem\n",
        "from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem\n",
    ),
    (
        "    Stage2FinancialHypothesisRevision,\n    Stage2HandoffClaimLink,\n    Stage2HandoffEvidenceLink,\n    Stage2ResearchHypothesisLink,\n",
        "    Stage2FinancialHypothesisRevision,\n    Stage2ResearchHypothesisLink,\n",
    ),
    (
        '''def _require_exact_research_provenance(\n    session: Session, *, kind: str, target_id: UUID, company_research_id: UUID\n) -> None:\n    if kind == "claim":\n        linked = session.scalar(\n            select(Stage2HandoffClaimLink.id).where(\n                Stage2HandoffClaimLink.company_research_id == company_research_id,\n                Stage2HandoffClaimLink.claim_revision_id == target_id,\n            )\n        )\n    elif kind == "evidence":\n        linked = session.scalar(\n            select(Stage2HandoffEvidenceLink.id).where(\n                Stage2HandoffEvidenceLink.company_research_id == company_research_id,\n                Stage2HandoffEvidenceLink.evidence_id == target_id,\n            )\n        )\n    else:\n        return\n    if linked is None:\n        raise InvestmentCandidateError(\n            "investment_candidate_input_invalid",\n            f"{kind} input is not frozen by the exact company research handoff",\n        )\n''',
        '''def _require_case_provenance(\n    session: Session, *, kind: str, row: ClaimRevision | EvidenceItem, case_id: UUID\n) -> None:\n    if kind == "claim":\n        claim = session.get(Claim, row.claim_id)\n        owned = claim is not None and claim.case_id == case_id\n    elif kind == "evidence":\n        owned = row.case_id == case_id\n    else:\n        return\n    if not owned:\n        raise InvestmentCandidateError(\n            "investment_candidate_input_invalid",\n            f"{kind} input does not belong to the exact research case",\n        )\n''',
    ),
    (
        '''                _require_exact_research_provenance(\n                    session, kind=kind, target_id=row.id, company_research_id=research.id\n                )\n''',
        '''                _require_case_provenance(\n                    session, kind=kind, row=row, case_id=research.case_id\n                )\n''',
    ),
]

for old, new in replacements:
    if old not in text:
        raise RuntimeError("expected case-provenance patch anchor is missing")
    text = text.replace(old, new)

TARGET.write_text(text, encoding="utf-8")
compile(text, str(TARGET), "exec")

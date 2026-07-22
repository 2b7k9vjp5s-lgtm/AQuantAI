"""One-time deterministic patch for case-owned claim/evidence provenance."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "industry_alpha/investment_candidate_commands.py"
text = TARGET.read_text(encoding="utf-8")

text = text.replace(
    "from industry_alpha.models import ClaimEvidenceLink, ClaimRevision, EvidenceItem",
    "from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem",
)
text = re.sub(r"\n    Stage2HandoffClaimLink,\n    Stage2HandoffEvidenceLink,", "", text)

start = text.index("def _require_exact_research_provenance(")
end = text.index("\ndef _validate_member_price_manifest(", start)
helper = '''def _require_case_provenance(
    session: Session, *, kind: str, row: ClaimRevision | EvidenceItem, case_id: UUID
) -> None:
    if kind == "claim":
        claim = session.get(Claim, row.claim_id)
        owned = claim is not None and claim.case_id == case_id
    elif kind == "evidence":
        owned = row.case_id == case_id
    else:
        return
    if not owned:
        raise InvestmentCandidateError(
            "investment_candidate_input_invalid",
            f"{kind} input does not belong to the exact research case",
        )

'''
text = text[:start] + helper + text[end + 1 :]
text = text.replace("_require_exact_research_provenance(", "_require_case_provenance(")
text = text.replace(
    "session, kind=kind, target_id=row.id, company_research_id=research.id",
    "session, kind=kind, row=row, case_id=research.case_id",
)

for forbidden in ("Stage2HandoffClaimLink", "Stage2HandoffEvidenceLink", "_require_exact_research_provenance"):
    if forbidden in text:
        raise RuntimeError(f"case-provenance patch left forbidden symbol: {forbidden}")
if "def _require_case_provenance(" not in text or "case_id=research.case_id" not in text:
    raise RuntimeError("case-provenance patch did not establish required symbols")

TARGET.write_text(text, encoding="utf-8")
compile(text, str(TARGET), "exec")

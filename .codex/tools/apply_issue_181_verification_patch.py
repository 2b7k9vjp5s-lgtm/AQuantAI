"""One-time deterministic patch for Issue #181 verification contract synchronization."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace(path: str, old: str, new: str) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected patch anchor missing in {path}")
    target.write_text(text.replace(old, new), encoding="utf-8")


commands = ROOT / "industry_alpha/investment_candidate_commands.py"
if '"verification_item_code", "verification_question"' not in commands.read_text(encoding="utf-8"):
    replace(
        "industry_alpha/investment_candidate_commands.py",
        "    FALSIFICATION_STATES,\n    VERIFICATION_STATES,\n",
        "    FALSIFICATION_STATES,\n    VERIFICATION_ITEM_CODES,\n    VERIFICATION_STATES,\n",
    )
    replace(
        "industry_alpha/investment_candidate_commands.py",
        '        "verification_state", "verification_material", "score_text", "missing_reason",\n',
        '        "verification_state", "verification_material", "verification_item_code",\n'
        '        "verification_question", "score_text", "missing_reason",\n',
    )
    replace(
        "industry_alpha/investment_candidate_commands.py",
        '    _keys(raw, fields, fields - {"score_text", "missing_reason", "expected_latest_revision_id"})\n',
        '    _keys(\n'
        '        raw,\n'
        '        fields,\n'
        '        fields\n'
        '        - {\n'
        '            "verification_item_code",\n'
        '            "verification_question",\n'
        '            "score_text",\n'
        '            "missing_reason",\n'
        '            "expected_latest_revision_id",\n'
        '        },\n'
        '    )\n',
    )
    replace(
        "industry_alpha/investment_candidate_commands.py",
        '    if not isinstance(raw["verification_material"], bool):\n'
        '        raise InvestmentCandidateError(\n'
        '            "investment_candidate_input_invalid", "verification_material must be boolean"\n'
        '        )\n'
        '    source_text, score = decimal_score(raw.get("score_text"), required=state == "supported")\n',
        '    if not isinstance(raw["verification_material"], bool):\n'
        '        raise InvestmentCandidateError(\n'
        '            "investment_candidate_input_invalid", "verification_material must be boolean"\n'
        '        )\n'
        '    verification_item_code = _text(\n'
        '        raw.get("verification_item_code"), "verification_item_code", 40, optional=True\n'
        '    )\n'
        '    verification_question = _text(\n'
        '        raw.get("verification_question"), "verification_question", 2000, optional=True\n'
        '    )\n'
        '    if verification in {"pending", "failed"}:\n'
        '        if (\n'
        '            raw["verification_material"] is not True\n'
        '            or verification_item_code not in VERIFICATION_ITEM_CODES\n'
        '            or verification_question is None\n'
        '        ):\n'
        '            raise InvestmentCandidateError(\n'
        '                "investment_candidate_verification_invalid",\n'
        '                "pending or failed verification requires material=true, a closed item code and a question",\n'
        '            )\n'
        '    elif (\n'
        '        raw["verification_material"] is not False\n'
        '        or verification_item_code is not None\n'
        '        or verification_question is not None\n'
        '    ):\n'
        '        raise InvestmentCandidateError(\n'
        '            "investment_candidate_verification_invalid",\n'
        '            "verified or not-applicable verification forbids material state and verification item fields",\n'
        '        )\n'
        '    source_text, score = decimal_score(raw.get("score_text"), required=state == "supported")\n',
    )
    replace(
        "industry_alpha/investment_candidate_commands.py",
        '        "verification_state": verification,\n'
        '        "verification_material": raw["verification_material"],\n'
        '        "source_score_text": source_text, "score_value": score,\n',
        '        "verification_state": verification,\n'
        '        "verification_material": raw["verification_material"],\n'
        '        "verification_item_code": verification_item_code,\n'
        '        "verification_question": verification_question,\n'
        '        "source_score_text": source_text, "score_value": score,\n',
    )
    replace(
        "industry_alpha/investment_candidate_commands.py",
        '            "standardized_score_text": None if data["score_value"] is None else format(data["score_value"], ".2f"),\n'
        '            "input_count": len(validated),\n',
        '            "standardized_score_text": None if data["score_value"] is None else format(data["score_value"], ".2f"),\n'
        '            "verification_state": data["verification_state"],\n'
        '            "verification_item_code": data["verification_item_code"],\n'
        '            "verification_question": data["verification_question"],\n'
        '            "input_count": len(validated),\n',
    )
    replace(
        "industry_alpha/investment_candidate_commands.py",
        '            verification_material=data["verification_material"], source_score_text=data["source_score_text"],\n',
        '            verification_material=data["verification_material"],\n'
        '            verification_item_code=data["verification_item_code"],\n'
        '            verification_question=data["verification_question"],\n'
        '            source_score_text=data["source_score_text"],\n',
    )

rules = ROOT / "industry_alpha/investment_candidate_rules.py"
if 'c.verification_state == "failed" and c.verification_material' in rules.read_text(encoding="utf-8"):
    replace(
        "industry_alpha/investment_candidate_rules.py",
        '    if any(\n'
        '        c.verification_state == "failed" and c.verification_material\n'
        '        for c in components.values()\n'
        '    ):\n',
        '    if any(c.verification_state == "failed" for c in components.values()):\n',
    )

query = ROOT / "industry_alpha/investment_candidate_query.py"
if '"verification_item_code": revision.verification_item_code' not in query.read_text(encoding="utf-8"):
    replace(
        "industry_alpha/investment_candidate_query.py",
        '            "verification_state": revision.verification_state,\n'
        '            "verification_material": revision.verification_material,\n'
        '            "source_score_text": revision.source_score_text,\n',
        '            "verification_state": revision.verification_state,\n'
        '            "verification_material": revision.verification_material,\n'
        '            "verification_item_code": revision.verification_item_code,\n'
        '            "verification_question": revision.verification_question,\n'
        '            "source_score_text": revision.source_score_text,\n',
    )
    replace(
        "industry_alpha/investment_candidate_query.py",
        '                    "verification_state": component_revision.verification_state,\n'
        '                    "falsification_state": component_revision.falsification_state,\n',
        '                    "verification_state": component_revision.verification_state,\n'
        '                    "verification_material": component_revision.verification_material,\n'
        '                    "verification_item_code": component_revision.verification_item_code,\n'
        '                    "verification_question": component_revision.verification_question,\n'
        '                    "falsification_state": component_revision.falsification_state,\n',
    )

model_tests = ROOT / "tests/test_investment_candidate_models.py"
if "test_verification_item_contract_is_closed_and_explicit" not in model_tests.read_text(encoding="utf-8"):
    text = model_tests.read_text(encoding="utf-8")
    text = text.replace(
        "from fastapi.testclient import TestClient\n",
        "from uuid import uuid4\n\nimport pytest\nfrom fastapi.testclient import TestClient\n",
    )
    text = text.replace(
        "from backend.main import app\n",
        "from backend.main import app\n"
        "from industry_alpha.investment_candidate_commands import (\n"
        "    InvestmentCandidateError,\n"
        "    _parse_component,\n"
        ")\n",
    )
    text = text.replace(
        "    INVESTMENT_CANDIDATE_MODELS,\n",
        "    INVESTMENT_CANDIDATE_MODELS,\n    VERIFICATION_ITEM_CODES,\n",
    )
    text = text.replace(
        '        "risk_penalty",\n    )\n\n\ndef test_read_routes_are_get_only_and_page_is_non_advisory() -> None:\n',
        '        "risk_penalty",\n    )\n'
        '    assert VERIFICATION_ITEM_CODES == (\n'
        '        "certification",\n'
        '        "order",\n'
        '        "capacity",\n'
        '        "production",\n'
        '        "financial_confirmation",\n'
        '        "customer_confirmation",\n'
        '        "other_explicit",\n'
        '    )\n\n\n'
        'def test_read_routes_are_get_only_and_page_is_non_advisory() -> None:\n',
    )
    text += '''\n\ndef _component_input(**overrides):\n    raw = {\n        "assessment_key": "verification-contract",\n        "beneficiary_id": str(uuid4()),\n        "beneficiary_revision_id": str(uuid4()),\n        "company_research_revision_id": str(uuid4()),\n        "component_code": "catalyst_readiness",\n        "assessment_state": "missing",\n        "verification_state": "verified",\n        "verification_material": False,\n        "missing_reason": "not yet assessed",\n        "rationale": "bounded rationale",\n        "falsification_condition": "bounded falsification condition",\n        "falsification_state": "inactive",\n        "information_cutoff_date": "2026-07-22",\n        "recorded_at_utc": "2026-07-22T06:00:00+00:00",\n        "recorded_by": "test",\n        "inputs": [],\n    }\n    raw.update(overrides)\n    return raw\n\n\ndef test_verification_item_contract_is_closed_and_explicit() -> None:\n    parsed = _parse_component(\n        _component_input(\n            verification_state="pending",\n            verification_material=True,\n            verification_item_code="certification",\n            verification_question="Has the customer certification completed?",\n        )\n    )\n    assert parsed["verification_item_code"] == "certification"\n    assert parsed["verification_question"].startswith("Has the customer")\n\n    with pytest.raises(InvestmentCandidateError, match="closed item code"):\n        _parse_component(\n            _component_input(\n                verification_state="pending",\n                verification_material=True,\n                verification_item_code="social_buzz",\n                verification_question="Is attention rising?",\n            )\n        )\n    with pytest.raises(InvestmentCandidateError, match="forbids"):\n        _parse_component(\n            _component_input(\n                verification_state="verified",\n                verification_material=False,\n                verification_item_code="certification",\n                verification_question="This must not be stored for verified state",\n            )\n        )\n'''
    model_tests.write_text(text, encoding="utf-8")

rules_tests = ROOT / "tests/test_investment_candidate_rules.py"
if "failed_result = evaluate_candidate(failed)" not in rules_tests.read_text(encoding="utf-8"):
    replace(
        "tests/test_investment_candidate_rules.py",
        '    assert evaluate_candidate(pending).candidate_status == "awaiting_verification"\n\n    missing = complete()\n',
        '    pending_result = evaluate_candidate(pending)\n'
        '    assert pending_result.candidate_status == "awaiting_verification"\n'
        '    assert pending_result.final_score is None\n\n'
        '    failed = complete()\n'
        '    failed["catalyst_readiness"] = component(\n'
        '        "catalyst_readiness", "75", verification_state="failed", verification_material=True\n'
        '    )\n'
        '    failed_result = evaluate_candidate(failed)\n'
        '    assert failed_result.candidate_status == "not_current_candidate"\n'
        '    assert failed_result.final_score is None\n\n'
        '    missing = complete()\n',
    )

for relative in (
    "industry_alpha/investment_candidate_commands.py",
    "industry_alpha/investment_candidate_models.py",
    "industry_alpha/investment_candidate_query.py",
    "industry_alpha/investment_candidate_rules.py",
    "tests/test_investment_candidate_models.py",
    "tests/test_investment_candidate_rules.py",
):
    source = (ROOT / relative).read_text(encoding="utf-8")
    compile(source, relative, "exec")

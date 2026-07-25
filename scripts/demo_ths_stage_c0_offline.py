"""Run the production-reachable THS Stage C0 offline golden path."""

from __future__ import annotations

import json
from pathlib import Path

from datasource.ths_structured_provider import (
    CapabilityReadiness,
    INDEX_DAILY_HISTORY_CONTRACT,
    IndexHistorySelector,
    build_index_history_plan,
    index_history_schema_fingerprint,
    load_synthetic_fixture,
    redact_mapping,
    validate_index_history_envelope,
)


def build_demo_summary() -> dict[str, object]:
    repository_root = Path(__file__).resolve().parents[1]
    fixture_path = repository_root / "tests" / "fixtures" / "ths_stage_c0" / "index_history_success.synthetic.json"

    selector = IndexHistorySelector("SYNTH.IDX.C0", 1000, 2000)
    readiness = CapabilityReadiness(reviewed_evidence_fingerprints=("c" * 64,))
    plan = build_index_history_plan(selector, readiness)
    validated = validate_index_history_envelope(load_synthetic_fixture(fixture_path))

    diagnostics = redact_mapping(
        {
            "request_id": "synthetic-request-id",
            "credential_profile": "synthetic-profile",
            "safe_contract_key": plan.contract_key,
        }
    )
    return {
        "stage": "THS Stage C0 offline foundation",
        "contract_key": INDEX_DAILY_HISTORY_CONTRACT.contract_key,
        "contract_fingerprint": INDEX_DAILY_HISTORY_CONTRACT.contract_fingerprint,
        "request_fingerprint": plan.request_fingerprint,
        "schema_fingerprint": index_history_schema_fingerprint(),
        "validated_row_count": len(validated.data.item),
        "blocked_reason_codes": plan.blocked_reason_codes,
        "blocked_messages_zh": plan.blocked_messages_zh,
        "synthetic_only": plan.synthetic_only,
        "remote_executable": plan.remote_executable,
        "diagnostics": diagnostics,
    }


def main() -> None:
    print(json.dumps(build_demo_summary(), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

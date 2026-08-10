"""Zero-network deterministic Research Evidence Pack v1 demo."""

from __future__ import annotations

from datetime import date, datetime, timezone
import json

from sqlalchemy import create_engine, select
from sqlalchemy.pool import StaticPool

from backend.database.engine import build_session_factory
from backend.database.models import Base
from industry_alpha.commands import (
    CaseClaimInput,
    EvidenceLedgerCommandService,
    EvidenceLinkInput,
)
from industry_alpha.models import ClaimRevision
from industry_alpha.research_evidence_pack_contracts import EvidencePackRequest
from industry_alpha.research_evidence_pack_query import ResearchEvidencePackQueryService


def _utc(hour: int) -> datetime:
    return datetime(2026, 8, 5, hour, tzinfo=timezone.utc)


def run_demo() -> dict[str, object]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    ledger = EvidenceLedgerCommandService(factory)
    information_date = date(2026, 8, 5)
    case = ledger.create_case(
        case_key="research-evidence-pack-demo",
        title="Research Evidence Pack v1 Demo",
        research_question="只读证据包是否可由已接受本地 Ledger 确定性重建？",
        information_cutoff_date=information_date,
        recorded_at_utc=_utc(8),
        origin="fixture",
    )
    evidence = ledger.add_evidence(
        case.id,
        evidence_grade="B",
        source_kind="research",
        source_title="零网络示例证据",
        information_date=information_date,
        summary="该示例只读取本地已接受 Evidence Ledger。",
        content_fingerprint="research-evidence-pack-demo-evidence",
        recorded_at_utc=_utc(9),
    )
    claim = ledger.create_claim(
        case.id,
        claim_key="research-evidence-pack-demo-claim",
        statement="Research Evidence Pack v1 可重建本地只读证据关系。",
        claim_kind="fact",
        claim_status="supported",
        information_cutoff_date=information_date,
        evidence_links=(EvidenceLinkInput(evidence.id, "supports"),),
        recorded_at_utc=_utc(10),
    )
    with factory() as session:
        claim_revision_id = session.scalar(
            select(ClaimRevision.id).where(
                ClaimRevision.claim_id == claim.id,
                ClaimRevision.revision_no == 1,
            )
        )
    selected = ledger.append_case_revision(
        case.id,
        title="Research Evidence Pack v1 Demo",
        research_question="只读证据包是否可由已接受本地 Ledger 确定性重建？",
        information_cutoff_date=information_date,
        workflow_state="open",
        conclusion_status="unassessed",
        claim_links=(CaseClaimInput(claim_revision_id, "context"),),
        recorded_at_utc=_utc(11),
    )
    payload = ResearchEvidencePackQueryService(factory).get_pack(
        EvidencePackRequest(
            research_case_id=case.id,
            research_case_revision_id=selected.id,
            information_cutoff_date=information_date,
            recorded_at_utc=_utc(11),
            limit=50,
        )
    ).to_dict()
    assert payload["contract_version"] == "aquantai.research-evidence-pack.v1"
    assert payload["visible_evidence_count"] == 1
    assert payload["entries"][0]["integrity_state"] == "ledger_only"
    assert payload["entries"][0]["membership_summary"] == "all_bindings_linked"
    assert payload["notices"]["writes_per_get"] == 0
    assert payload["notices"]["network_calls"] == 0
    engine.dispose()
    return payload


def main() -> None:
    payload = run_demo()
    print(
        json.dumps(
            {
                "contract_version": payload["contract_version"],
                "visible_evidence_count": payload["visible_evidence_count"],
                "membership_summary": payload["entries"][0]["membership_summary"],
                "integrity_state": payload["entries"][0]["integrity_state"],
                "writes_per_get": payload["notices"]["writes_per_get"],
                "network_calls": payload["notices"]["network_calls"],
                "ocr_calls": payload["notices"]["ocr_calls"],
                "ai_calls": payload["notices"]["ai_calls"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

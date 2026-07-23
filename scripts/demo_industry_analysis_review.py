"""Offline production-route golden path for Workbench UI Phase 1D."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.pool import StaticPool

import backend.api.industry_analysis as industry_api
from backend.database.engine import build_session_factory
from backend.database.models import Base, IngestionRun, StockBasicRecord
from backend.main import app
from industry_alpha.chain_map_models import IndustryMap
from industry_alpha.industry_thesis_models import (
    IndustryThesisCandidateIdentity,
    IndustryThesisCandidateRevision,
    IndustryThesisOutputLinkIdentity,
    IndustryThesisSessionRevision,
)
from industry_alpha.industry_thesis_review import ACCEPTANCE_PLAN_VERSION
from industry_alpha.stage1_models import Stage1Beneficiary
import industry_alpha.stage1_models  # noqa: F401 - register exact FK targets

UTC = timezone.utc
BASE = datetime(2026, 7, 23, 7, 0, tzinfo=UTC)
CUTOFF = date(2026, 7, 23)


def _ingestion() -> IngestionRun:
    return IngestionRun(
        batch_identifier="phase1d-production-route-demo",
        series_key="d" * 64,
        series_identity={"kind": "stock_basic", "demo": "phase1d"},
        provider="fixture",
        dataset="stock_basic",
        imported_at=BASE,
        completed_at=BASE,
        requested_start_date=CUTOFF,
        requested_end_date=CUTOFF,
        information_cutoff_date=CUTOFF,
        requested_scope={"market": "CN_A"},
        provider_request_metadata={},
        adapter_version="fixture-v1",
        snapshot_mode="complete",
        contract_version="v1",
        status="succeeded",
        row_count_received=3,
        row_count_written=3,
        dataset_counts={"stock_basic": 3},
    )


def _session_payload(stocks: list[dict]) -> dict:
    return {
        "thesis_text_original": "AI 数据中心扩张带动电子特气需求",
        "thesis_title_reviewed": "电子特气需求",
        "driver_type": "demand_expansion",
        "analysis_horizon_kind": "medium_term",
        "analysis_start_date": None,
        "analysis_end_date": None,
        "market_scope": [
            {
                "market_namespace": "CN_A",
                "exchange_namespace": None,
                "security_type": "common_equity",
                "include_status": "active",
                "listed_instrument_ids": [],
            }
        ],
        "chain_boundary": {
            "kind": "user_confirmed_text",
            "text": "纯化、供应与客户认证",
        },
        "exclusions": [],
        "seed_companies": [
            {
                "source_kind": "stock_basic_record",
                "exact_id": str(stock["id"]),
                "stock_basic_record_id": stock["id"],
                "listed_instrument_id": None,
                "label": stock["label"],
                "code": stock["code"],
            }
            for stock in stocks
        ],
        "seed_products": ["高纯电子气体"],
        "seed_technologies": [],
        "seed_bottlenecks": ["客户认证"],
        "draft_graph": {
            "workbench_contract": "aquantai.personal-research-workbench.scope.v1",
            "exact_industry_map_references": [],
            "nodes": [],
            "relationships": [],
        },
        "coverage_state": "reviewed_local_scope",
        "workflow_state": "candidate_build_ready",
        "information_cutoff_date": CUTOFF.isoformat(),
        "revision_note": "Phase 1D production-route demo scope",
    }


def _json(response, expected_status: int = 200) -> dict:
    assert response.status_code == expected_status, response.text
    return response.json()


def _exact_query(*, session_id: str, boundary: datetime, dry_run: bool | None = None) -> str:
    from urllib.parse import urlencode

    values = {
        "session_id": session_id,
        "as_of_cutoff": CUTOFF.isoformat(),
        "as_of_recorded_at_utc": boundary.isoformat(),
    }
    if dry_run is not None:
        values["dry_run"] = "true" if dry_run else "false"
    return urlencode(values)


def run_demo() -> dict:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = build_session_factory(engine)
    app.dependency_overrides[industry_api.get_industry_analysis_session_factory] = (
        lambda: factory
    )
    app.dependency_overrides[industry_api.get_industry_analysis_write_factory] = (
        lambda: factory
    )
    try:
        with factory.begin() as session:
            run = _ingestion()
            session.add(run)
            session.flush()
            rows = [
                StockBasicRecord(
                    ingestion_run_id=run.id,
                    stock_code=f"68810{index}.SH",
                    stock_name=label,
                    exchange="SSE",
                    industry="电子特气",
                    listing_date=date(2020, 1, index),
                    status="active",
                    source="fixture",
                )
                for index, label in enumerate(
                    ("演示公司甲", "演示公司乙", "演示公司丙"),
                    start=1,
                )
            ]
            session.add_all(rows)
            session.flush()
            stocks = [
                {"id": row.id, "label": row.stock_name, "code": row.stock_code}
                for row in rows
            ]

        with TestClient(app) as http:
            created = _json(
                http.post(
                    "/industry-analysis/api/sessions?dry_run=false",
                    json=_session_payload(stocks),
                )
            )
            session_id = created["session_id"]
            source_revision_id = created["session_revision_id"]
            read_boundary = datetime.now(UTC) + timedelta(minutes=2)

            candidate_build = _json(
                http.post(
                    "/industry-analysis/api/session-revisions/"
                    f"{source_revision_id}/candidate-builds?"
                    f"{_exact_query(session_id=session_id, boundary=read_boundary, dry_run=False)}",
                    json={
                        "expected_session_latest_revision_number": 1,
                        "selected_candidate_pool_revision_ids": [],
                    },
                )
            )
            assert candidate_build["candidate_count"] == 3

            review_page = http.get(candidate_build["review_path"])
            assert review_page.status_code == 200
            assert "逐条完成三态审阅" in review_page.text

            review_view = _json(
                http.get(
                    "/industry-analysis/api/session-revisions/"
                    f"{source_revision_id}/review-view?"
                    f"{_exact_query(session_id=session_id, boundary=read_boundary)}"
                )
            )
            assert review_view["candidate_count"] == 3
            states = (
                (
                    "selected_for_acceptance",
                    "direct",
                    "产品和认证路径直接对应需求扩张。",
                    "limited_evidence",
                    "仍需核对收入占比。",
                ),
                (
                    "rejected_by_user",
                    None,
                    "当前受益证据不足以进入后续研究。",
                    "not_current_priority",
                    "新增客户证据后再复核。",
                ),
                (
                    "unresolved",
                    None,
                    "受益方向存在但关键环节尚未验证。",
                    "awaiting_verification",
                    "等待客户认证与产能信息。",
                ),
            )
            decisions = []
            for candidate, values in zip(
                review_view["candidates"], states, strict=True
            ):
                decision, exposure, rationale, uncertainty_state, uncertainty_note = values
                decisions.append(
                    {
                        "candidate_revision_id": candidate["candidate_revision_id"],
                        "expected_latest_revision_number": candidate["revision_number"],
                        "decision": decision,
                        "final_proposed_exposure_type": exposure,
                        "rationale_text": rationale,
                        "uncertainty_state": uncertainty_state,
                        "uncertainty_note": uncertainty_note,
                    }
                )
            review_payload = {
                "expected_session_latest_revision_number": 1,
                "acceptance_plan_version": ACCEPTANCE_PLAN_VERSION,
                "decisions": decisions,
                "revision_note": "完成三条精确候选路径审阅",
            }

            with factory() as session:
                session_revision_count_before = session.scalar(
                    select(func.count()).select_from(IndustryThesisSessionRevision)
                )
                candidate_revision_count_before = session.scalar(
                    select(func.count()).select_from(IndustryThesisCandidateRevision)
                )

            dry_run = _json(
                http.post(
                    "/industry-analysis/api/session-revisions/"
                    f"{source_revision_id}/reviews?"
                    f"{_exact_query(session_id=session_id, boundary=read_boundary, dry_run=True)}",
                    json=review_payload,
                )
            )
            assert dry_run["selected_count"] == 1
            assert dry_run["rejected_count"] == 1
            assert dry_run["unresolved_count"] == 1
            with factory() as session:
                assert session.scalar(
                    select(func.count()).select_from(IndustryThesisSessionRevision)
                ) == session_revision_count_before
                assert session.scalar(
                    select(func.count()).select_from(IndustryThesisCandidateRevision)
                ) == candidate_revision_count_before

            committed = _json(
                http.post(
                    "/industry-analysis/api/session-revisions/"
                    f"{source_revision_id}/reviews?"
                    f"{_exact_query(session_id=session_id, boundary=read_boundary, dry_run=False)}",
                    json=review_payload,
                )
            )
            assert committed["acceptance_plan"] == dry_run["acceptance_plan"]
            assert committed["acceptance_plan_fingerprint_sha256"] == dry_run[
                "acceptance_plan_fingerprint_sha256"
            ]
            assert committed["result_path"]

            result_page = http.get(committed["result_path"])
            assert result_page.status_code == 200
            assert "审阅计划已生成，但尚未写入正式产业地图" in result_page.text

            parsed = urlparse(committed["result_path"])
            result_query = parse_qs(parsed.query)
            result_boundary = datetime.fromisoformat(
                result_query["as_of_recorded_at_utc"][0]
            )
            result = _json(
                http.get(
                    "/industry-analysis/api/reviewed-plans/"
                    f"{committed['reviewed_session_revision_id']}?"
                    f"{_exact_query(session_id=session_id, boundary=result_boundary)}"
                )
            )
            assert result["candidate_count"] == 3
            assert result["selected_count"] == 1
            assert result["rejected_count"] == 1
            assert result["unresolved_count"] == 1
            assert result["acceptance_plan_fingerprint_sha256"] == committed[
                "acceptance_plan_fingerprint_sha256"
            ]

            history = _json(
                http.get(
                    "/industry-analysis/api/sessions?"
                    f"as_of_cutoff={CUTOFF.isoformat()}&"
                    f"as_of_recorded_at_utc={result_boundary.isoformat()}&limit=20"
                )
            )
            assert history["sessions"][0]["next_surface"] == "result"
            assert history["sessions"][0]["visible_latest_revision_id"] == committed[
                "reviewed_session_revision_id"
            ]

        with factory() as session:
            counts = {
                "session_revisions": session.scalar(
                    select(func.count()).select_from(IndustryThesisSessionRevision)
                ),
                "candidate_identities": session.scalar(
                    select(func.count()).select_from(IndustryThesisCandidateIdentity)
                ),
                "candidate_revisions": session.scalar(
                    select(func.count()).select_from(IndustryThesisCandidateRevision)
                ),
                "output_links": session.scalar(
                    select(func.count()).select_from(IndustryThesisOutputLinkIdentity)
                ),
                "industry_maps": session.scalar(
                    select(func.count()).select_from(IndustryMap)
                ),
                "stage1_beneficiaries": session.scalar(
                    select(func.count()).select_from(Stage1Beneficiary)
                ),
            }
        assert counts == {
            "session_revisions": 2,
            "candidate_identities": 3,
            "candidate_revisions": 6,
            "output_links": 0,
            "industry_maps": 0,
            "stage1_beneficiaries": 0,
        }
        return {
            "session_id": session_id,
            "source_session_revision_id": source_revision_id,
            "reviewed_session_revision_id": committed[
                "reviewed_session_revision_id"
            ],
            "candidate_count": result["candidate_count"],
            "selected_count": result["selected_count"],
            "rejected_count": result["rejected_count"],
            "unresolved_count": result["unresolved_count"],
            "acceptance_plan_fingerprint_sha256": result[
                "acceptance_plan_fingerprint_sha256"
            ],
            "history_next_surface": history["sessions"][0]["next_surface"],
            "ownership_notice": result["ownership_notice"],
            "counts": counts,
        }
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def main() -> None:
    print(json.dumps(run_demo(), ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()

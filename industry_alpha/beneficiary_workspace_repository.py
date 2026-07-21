"""Fixed-count scalar reads for the Industry Beneficiary Workspace."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import IngestionRun, StockBasicRecord
from industry_alpha.chain_map_models import IndustryMap, IndustryMapRevision
from industry_alpha.stage1_models import Stage1Beneficiary, Stage1BeneficiaryRevision
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
)
from industry_alpha.stage2_query_values import stored_utc

BENEFICIARY_KIND_ORDER = {"direct": 0, "secondary": 1, "potential": 2}


class IndustryBeneficiaryWorkspaceDataError(RuntimeError):
    """Required accepted workspace data could not be projected safely."""


@dataclass(frozen=True)
class MapSelectorRow:
    map_id: UUID
    case_id: UUID
    map_key: str
    created_at_utc: datetime
    revision_id: UUID
    revision_no: int
    title: str
    scope: str
    information_cutoff_date: date
    recorded_at_utc: datetime
    supersedes_revision_id: UUID | None


@dataclass(frozen=True)
class BeneficiaryOverviewRow:
    beneficiary_id: UUID
    case_id: UUID
    map_id: UUID
    source: str
    stock_code: str
    created_at_utc: datetime
    revision_id: UUID
    revision_no: int
    selected_map_revision_id: UUID
    stock_basic_record_id: int
    beneficiary_kind: str
    assessment_status: str
    rationale_summary: str
    information_cutoff_date: date
    recorded_at_utc: datetime
    supersedes_revision_id: UUID | None
    stock_name: str
    exchange: str
    provider_industry: str
    listing_date: date | None
    stock_status: str
    ingestion_run_id: int
    ingestion_series_key: str
    ingestion_provider: str
    ingestion_information_cutoff_date: date
    ingestion_completed_at_utc: datetime
    company_research_id: UUID | None
    stage2_frozen_beneficiary_revision_id: UUID | None
    stage2_selected_map_revision_id: UUID | None
    stage2_stock_basic_record_id: int | None
    company_research_revision_id: UUID | None
    company_research_revision_no: int | None
    company_research_workflow_state: str | None
    company_research_conclusion_status: str | None
    company_research_question: str | None
    company_research_summary: str | None
    company_research_information_cutoff_date: date | None
    company_research_recorded_at_utc: datetime | None
    company_research_supersedes_revision_id: UUID | None


class IndustryBeneficiaryWorkspaceRepository:
    """Read overview scalars with a query count independent of company count."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_map_selectors(
        self, *, as_of_cutoff: date | None = None
    ) -> tuple[MapSelectorRow, ...]:
        statement = (
            select(
                IndustryMap.id.label("map_id"),
                IndustryMap.case_id.label("case_id"),
                IndustryMap.map_key.label("map_key"),
                IndustryMap.created_at_utc.label("created_at_utc"),
                IndustryMapRevision.id.label("revision_id"),
                IndustryMapRevision.revision_no.label("revision_no"),
                IndustryMapRevision.title.label("title"),
                IndustryMapRevision.scope.label("scope"),
                IndustryMapRevision.information_cutoff_date.label(
                    "information_cutoff_date"
                ),
                IndustryMapRevision.recorded_at_utc.label("recorded_at_utc"),
                IndustryMapRevision.supersedes_revision_id.label(
                    "supersedes_revision_id"
                ),
            )
            .join(IndustryMapRevision, IndustryMapRevision.map_id == IndustryMap.id)
            .where(
                *_dated_visibility_conditions(
                    IndustryMapRevision.information_cutoff_date,
                    IndustryMapRevision.recorded_at_utc,
                    as_of_cutoff,
                )
            )
            .order_by(
                IndustryMap.map_key.asc(),
                IndustryMap.id.asc(),
                IndustryMapRevision.revision_no.asc(),
                IndustryMapRevision.recorded_at_utc.asc(),
                IndustryMapRevision.id.asc(),
            )
        )
        latest_by_map: dict[UUID, MapSelectorRow] = {}
        for mapping in self._session.execute(statement).mappings():
            row = _map_selector_row(mapping)
            current = latest_by_map.get(row.map_id)
            if current is None or _revision_key(row) > _revision_key(current):
                latest_by_map[row.map_id] = row
        rows = list(latest_by_map.values())
        rows.sort(key=lambda item: (item.map_key, str(item.map_id)))
        return tuple(rows)

    def list_beneficiaries(
        self,
        map_id: UUID,
        *,
        as_of_cutoff: date | None,
        visible_map_revision_ids: set[UUID],
    ) -> tuple[BeneficiaryOverviewRow, ...]:
        beneficiary_statement = (
            select(
                Stage1Beneficiary.id.label("beneficiary_id"),
                Stage1Beneficiary.case_id.label("case_id"),
                Stage1Beneficiary.map_id.label("map_id"),
                Stage1Beneficiary.source.label("source"),
                Stage1Beneficiary.stock_code.label("stock_code"),
                Stage1Beneficiary.created_at_utc.label("created_at_utc"),
                Stage1BeneficiaryRevision.id.label("revision_id"),
                Stage1BeneficiaryRevision.revision_no.label("revision_no"),
                Stage1BeneficiaryRevision.selected_map_revision_id.label(
                    "selected_map_revision_id"
                ),
                Stage1BeneficiaryRevision.stock_basic_record_id.label(
                    "stock_basic_record_id"
                ),
                Stage1BeneficiaryRevision.beneficiary_kind.label("beneficiary_kind"),
                Stage1BeneficiaryRevision.assessment_status.label("assessment_status"),
                Stage1BeneficiaryRevision.rationale_summary.label("rationale_summary"),
                Stage1BeneficiaryRevision.information_cutoff_date.label(
                    "information_cutoff_date"
                ),
                Stage1BeneficiaryRevision.recorded_at_utc.label("recorded_at_utc"),
                Stage1BeneficiaryRevision.supersedes_revision_id.label(
                    "supersedes_revision_id"
                ),
            )
            .join(
                Stage1BeneficiaryRevision,
                Stage1BeneficiaryRevision.beneficiary_id == Stage1Beneficiary.id,
            )
            .where(
                Stage1Beneficiary.map_id == map_id,
                *_dated_visibility_conditions(
                    Stage1BeneficiaryRevision.information_cutoff_date,
                    Stage1BeneficiaryRevision.recorded_at_utc,
                    as_of_cutoff,
                ),
            )
            .order_by(
                Stage1Beneficiary.id.asc(),
                Stage1BeneficiaryRevision.revision_no.asc(),
                Stage1BeneficiaryRevision.recorded_at_utc.asc(),
                Stage1BeneficiaryRevision.id.asc(),
            )
        )
        latest_mappings: dict[UUID, dict[str, Any]] = {}
        all_visible_revision_ids_by_beneficiary: dict[UUID, set[UUID]] = {}
        for raw_mapping in self._session.execute(beneficiary_statement).mappings():
            mapping = dict(raw_mapping)
            beneficiary_id = _required_uuid(
                mapping["beneficiary_id"], "beneficiary_id"
            )
            revision_id = _required_uuid(mapping["revision_id"], "revision_id")
            all_visible_revision_ids_by_beneficiary.setdefault(
                beneficiary_id, set()
            ).add(revision_id)
            current = latest_mappings.get(beneficiary_id)
            if current is None or _mapping_revision_key(mapping) > _mapping_revision_key(
                current
            ):
                latest_mappings[beneficiary_id] = mapping

        stock_ids = {
            _required_int(mapping["stock_basic_record_id"], "stock_basic_record_id")
            for mapping in latest_mappings.values()
        }
        stock_statement = (
            select(
                StockBasicRecord.id.label("stock_basic_record_id"),
                StockBasicRecord.ingestion_run_id.label("ingestion_run_id"),
                StockBasicRecord.stock_code.label("stock_record_code"),
                StockBasicRecord.stock_name.label("stock_name"),
                StockBasicRecord.exchange.label("exchange"),
                StockBasicRecord.industry.label("provider_industry"),
                StockBasicRecord.listing_date.label("listing_date"),
                StockBasicRecord.status.label("stock_status"),
                StockBasicRecord.source.label("stock_record_source"),
                IngestionRun.series_key.label("ingestion_series_key"),
                IngestionRun.provider.label("ingestion_provider"),
                IngestionRun.information_cutoff_date.label(
                    "ingestion_information_cutoff_date"
                ),
                IngestionRun.completed_at.label("ingestion_completed_at_utc"),
                IngestionRun.status.label("ingestion_status"),
            )
            .join(IngestionRun, IngestionRun.id == StockBasicRecord.ingestion_run_id)
            .where(StockBasicRecord.id.in_(stock_ids))
            .order_by(StockBasicRecord.id.asc())
        )
        stock_by_id: dict[int, dict[str, Any]] = {}
        for raw_mapping in self._session.execute(stock_statement).mappings():
            mapping = dict(raw_mapping)
            stock_id = _required_int(
                mapping["stock_basic_record_id"], "stock_basic_record_id"
            )
            if stock_id in stock_by_id:
                raise IndustryBeneficiaryWorkspaceDataError(
                    f"duplicate exact stock row {stock_id}"
                )
            stock_by_id[stock_id] = mapping

        stage2_statement = (
            select(
                Stage2CompanyResearch.id.label("company_research_id"),
                Stage2CompanyResearch.beneficiary_id.label("beneficiary_id"),
                Stage2CompanyResearch.beneficiary_revision_id.label(
                    "stage2_frozen_beneficiary_revision_id"
                ),
                Stage2CompanyResearch.selected_map_revision_id.label(
                    "stage2_selected_map_revision_id"
                ),
                Stage2CompanyResearch.stock_basic_record_id.label(
                    "stage2_stock_basic_record_id"
                ),
                Stage2CompanyResearch.source.label("stage2_source"),
                Stage2CompanyResearch.stock_code.label("stage2_stock_code"),
                Stage2CompanyResearchRevision.id.label(
                    "company_research_revision_id"
                ),
                Stage2CompanyResearchRevision.revision_no.label(
                    "company_research_revision_no"
                ),
                Stage2CompanyResearchRevision.workflow_state.label(
                    "company_research_workflow_state"
                ),
                Stage2CompanyResearchRevision.conclusion_status.label(
                    "company_research_conclusion_status"
                ),
                Stage2CompanyResearchRevision.research_question.label(
                    "company_research_question"
                ),
                Stage2CompanyResearchRevision.summary.label(
                    "company_research_summary"
                ),
                Stage2CompanyResearchRevision.information_cutoff_date.label(
                    "company_research_information_cutoff_date"
                ),
                Stage2CompanyResearchRevision.recorded_at_utc.label(
                    "company_research_recorded_at_utc"
                ),
                Stage2CompanyResearchRevision.supersedes_revision_id.label(
                    "company_research_supersedes_revision_id"
                ),
            )
            .join(
                Stage2CompanyResearchRevision,
                Stage2CompanyResearchRevision.company_research_id
                == Stage2CompanyResearch.id,
            )
            .where(
                Stage2CompanyResearch.map_id == map_id,
                *_dated_visibility_conditions(
                    Stage2CompanyResearchRevision.information_cutoff_date,
                    Stage2CompanyResearchRevision.recorded_at_utc,
                    as_of_cutoff,
                ),
            )
            .order_by(
                Stage2CompanyResearch.beneficiary_id.asc(),
                Stage2CompanyResearch.id.asc(),
                Stage2CompanyResearchRevision.revision_no.asc(),
                Stage2CompanyResearchRevision.recorded_at_utc.asc(),
                Stage2CompanyResearchRevision.id.asc(),
            )
        )
        stage2_by_beneficiary: dict[UUID, dict[str, Any]] = {}
        identity_by_beneficiary: dict[UUID, UUID] = {}
        for raw_mapping in self._session.execute(stage2_statement).mappings():
            mapping = dict(raw_mapping)
            beneficiary_id = _required_uuid(
                mapping["beneficiary_id"], "stage2 beneficiary_id"
            )
            research_id = _required_uuid(
                mapping["company_research_id"], "company_research_id"
            )
            prior_identity = identity_by_beneficiary.setdefault(
                beneficiary_id, research_id
            )
            if prior_identity != research_id:
                raise IndustryBeneficiaryWorkspaceDataError(
                    f"multiple incompatible Stage 2 identities for beneficiary {beneficiary_id}"
                )
            current = stage2_by_beneficiary.get(beneficiary_id)
            if current is None or _mapping_stage2_revision_key(
                mapping
            ) > _mapping_stage2_revision_key(current):
                stage2_by_beneficiary[beneficiary_id] = mapping

        rows: list[BeneficiaryOverviewRow] = []
        for beneficiary_id, mapping in latest_mappings.items():
            selected_map_revision_id = _required_uuid(
                mapping["selected_map_revision_id"], "selected_map_revision_id"
            )
            if selected_map_revision_id not in visible_map_revision_ids:
                raise IndustryBeneficiaryWorkspaceDataError(
                    "Stage 1 beneficiary references a map revision that is not "
                    "visible in the selected map context."
                )
            stock_id = _required_int(
                mapping["stock_basic_record_id"], "stock_basic_record_id"
            )
            stock = stock_by_id.get(stock_id)
            if stock is None:
                raise IndustryBeneficiaryWorkspaceDataError(
                    f"exact stock row {stock_id} is unavailable"
                )
            source = _required_text(mapping["source"], "beneficiary source")
            stock_code = _required_text(mapping["stock_code"], "beneficiary stock_code")
            if (
                _required_text(stock["stock_record_source"], "stock source") != source
                or _required_text(stock["stock_record_code"], "stock code") != stock_code
            ):
                raise IndustryBeneficiaryWorkspaceDataError(
                    "exact stock provenance does not match the beneficiary identity"
                )
            if stock["ingestion_status"] != "succeeded":
                raise IndustryBeneficiaryWorkspaceDataError(
                    "exact stock provenance is not from a succeeded ingestion run"
                )
            completed_at = stock["ingestion_completed_at_utc"]
            if completed_at is None:
                raise IndustryBeneficiaryWorkspaceDataError(
                    "exact stock provenance has no completion timestamp"
                )

            stage2 = stage2_by_beneficiary.get(beneficiary_id)
            if stage2 is not None:
                frozen_revision_id = _required_uuid(
                    stage2["stage2_frozen_beneficiary_revision_id"],
                    "Stage 2 frozen beneficiary revision",
                )
                if frozen_revision_id not in all_visible_revision_ids_by_beneficiary.get(
                    beneficiary_id, set()
                ):
                    raise IndustryBeneficiaryWorkspaceDataError(
                        "Stage 2 references a beneficiary revision that is not visible "
                        "in the requested historical context."
                    )
                if (
                    _required_text(stage2["stage2_source"], "Stage 2 source") != source
                    or _required_text(
                        stage2["stage2_stock_code"], "Stage 2 stock_code"
                    )
                    != stock_code
                ):
                    raise IndustryBeneficiaryWorkspaceDataError(
                        "Stage 2 identity does not match its exact Stage 1 beneficiary"
                    )

            kind = _required_text(mapping["beneficiary_kind"], "beneficiary_kind")
            if kind not in BENEFICIARY_KIND_ORDER:
                raise IndustryBeneficiaryWorkspaceDataError(
                    f"unsupported persisted beneficiary kind: {kind}"
                )
            rows.append(
                BeneficiaryOverviewRow(
                    beneficiary_id=beneficiary_id,
                    case_id=_required_uuid(mapping["case_id"], "case_id"),
                    map_id=_required_uuid(mapping["map_id"], "map_id"),
                    source=source,
                    stock_code=stock_code,
                    created_at_utc=_required_utc(
                        mapping["created_at_utc"], "beneficiary created_at_utc"
                    ),
                    revision_id=_required_uuid(mapping["revision_id"], "revision_id"),
                    revision_no=_required_int(mapping["revision_no"], "revision_no"),
                    selected_map_revision_id=selected_map_revision_id,
                    stock_basic_record_id=stock_id,
                    beneficiary_kind=kind,
                    assessment_status=_required_text(
                        mapping["assessment_status"], "assessment_status"
                    ),
                    rationale_summary=_required_text(
                        mapping["rationale_summary"], "rationale_summary"
                    ),
                    information_cutoff_date=_required_date(
                        mapping["information_cutoff_date"],
                        "information_cutoff_date",
                    ),
                    recorded_at_utc=_required_utc(
                        mapping["recorded_at_utc"], "recorded_at_utc"
                    ),
                    supersedes_revision_id=_optional_uuid(
                        mapping["supersedes_revision_id"]
                    ),
                    stock_name=_required_text(stock["stock_name"], "stock_name"),
                    exchange=_required_text(stock["exchange"], "exchange"),
                    provider_industry=_required_text(
                        stock["provider_industry"], "provider_industry", allow_empty=True
                    ),
                    listing_date=_optional_date(stock["listing_date"]),
                    stock_status=_required_text(stock["stock_status"], "stock_status"),
                    ingestion_run_id=_required_int(
                        stock["ingestion_run_id"], "ingestion_run_id"
                    ),
                    ingestion_series_key=_required_text(
                        stock["ingestion_series_key"], "ingestion_series_key"
                    ),
                    ingestion_provider=_required_text(
                        stock["ingestion_provider"], "ingestion_provider"
                    ),
                    ingestion_information_cutoff_date=_required_date(
                        stock["ingestion_information_cutoff_date"],
                        "ingestion information cutoff",
                    ),
                    ingestion_completed_at_utc=_required_utc(
                        completed_at, "ingestion completed_at"
                    ),
                    company_research_id=(
                        None
                        if stage2 is None
                        else _required_uuid(
                            stage2["company_research_id"], "company_research_id"
                        )
                    ),
                    stage2_frozen_beneficiary_revision_id=(
                        None
                        if stage2 is None
                        else _required_uuid(
                            stage2["stage2_frozen_beneficiary_revision_id"],
                            "Stage 2 frozen beneficiary revision",
                        )
                    ),
                    stage2_selected_map_revision_id=(
                        None
                        if stage2 is None
                        else _required_uuid(
                            stage2["stage2_selected_map_revision_id"],
                            "Stage 2 selected map revision",
                        )
                    ),
                    stage2_stock_basic_record_id=(
                        None
                        if stage2 is None
                        else _required_int(
                            stage2["stage2_stock_basic_record_id"],
                            "Stage 2 stock record",
                        )
                    ),
                    company_research_revision_id=(
                        None
                        if stage2 is None
                        else _required_uuid(
                            stage2["company_research_revision_id"],
                            "company research revision",
                        )
                    ),
                    company_research_revision_no=(
                        None
                        if stage2 is None
                        else _required_int(
                            stage2["company_research_revision_no"],
                            "company research revision_no",
                        )
                    ),
                    company_research_workflow_state=(
                        None
                        if stage2 is None
                        else _required_text(
                            stage2["company_research_workflow_state"],
                            "company research workflow_state",
                        )
                    ),
                    company_research_conclusion_status=(
                        None
                        if stage2 is None
                        else _required_text(
                            stage2["company_research_conclusion_status"],
                            "company research conclusion_status",
                        )
                    ),
                    company_research_question=(
                        None
                        if stage2 is None
                        else _required_text(
                            stage2["company_research_question"],
                            "company research question",
                        )
                    ),
                    company_research_summary=(
                        None if stage2 is None else stage2["company_research_summary"]
                    ),
                    company_research_information_cutoff_date=(
                        None
                        if stage2 is None
                        else _required_date(
                            stage2["company_research_information_cutoff_date"],
                            "company research information cutoff",
                        )
                    ),
                    company_research_recorded_at_utc=(
                        None
                        if stage2 is None
                        else _required_utc(
                            stage2["company_research_recorded_at_utc"],
                            "company research recorded_at_utc",
                        )
                    ),
                    company_research_supersedes_revision_id=(
                        None
                        if stage2 is None
                        else _optional_uuid(
                            stage2["company_research_supersedes_revision_id"]
                        )
                    ),
                )
            )
        rows.sort(
            key=lambda item: (
                BENEFICIARY_KIND_ORDER[item.beneficiary_kind],
                item.source,
                item.stock_code,
                str(item.beneficiary_id),
            )
        )
        return tuple(rows)


def _dated_visibility_conditions(
    information_column: Any, recorded_column: Any, cutoff: date | None
) -> tuple[Any, ...]:
    if cutoff is None:
        return ()
    return (
        information_column <= cutoff,
        recorded_column < _cutoff_exclusive_utc(cutoff),
    )


def _cutoff_exclusive_utc(cutoff: date) -> datetime:
    return datetime.combine(cutoff + timedelta(days=1), time.min, tzinfo=timezone.utc)


def _revision_key(row: MapSelectorRow) -> tuple[int, datetime, str]:
    return row.revision_no, stored_utc(row.recorded_at_utc), str(row.revision_id)


def _mapping_revision_key(mapping: dict[str, Any]) -> tuple[int, datetime, str]:
    return (
        _required_int(mapping["revision_no"], "revision_no"),
        _required_utc(mapping["recorded_at_utc"], "recorded_at_utc"),
        str(_required_uuid(mapping["revision_id"], "revision_id")),
    )


def _mapping_stage2_revision_key(
    mapping: dict[str, Any],
) -> tuple[int, datetime, str]:
    return (
        _required_int(
            mapping["company_research_revision_no"],
            "company research revision_no",
        ),
        _required_utc(
            mapping["company_research_recorded_at_utc"],
            "company research recorded_at_utc",
        ),
        str(
            _required_uuid(
                mapping["company_research_revision_id"],
                "company research revision_id",
            )
        ),
    )


def _map_selector_row(mapping: Any) -> MapSelectorRow:
    return MapSelectorRow(
        map_id=_required_uuid(mapping["map_id"], "map_id"),
        case_id=_required_uuid(mapping["case_id"], "case_id"),
        map_key=_required_text(mapping["map_key"], "map_key"),
        created_at_utc=_required_utc(mapping["created_at_utc"], "created_at_utc"),
        revision_id=_required_uuid(mapping["revision_id"], "revision_id"),
        revision_no=_required_int(mapping["revision_no"], "revision_no"),
        title=_required_text(mapping["title"], "title"),
        scope=_required_text(mapping["scope"], "scope"),
        information_cutoff_date=_required_date(
            mapping["information_cutoff_date"], "information_cutoff_date"
        ),
        recorded_at_utc=_required_utc(
            mapping["recorded_at_utc"], "recorded_at_utc"
        ),
        supersedes_revision_id=_optional_uuid(mapping["supersedes_revision_id"]),
    )


def _required_uuid(value: Any, field_name: str) -> UUID:
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise IndustryBeneficiaryWorkspaceDataError(
            f"{field_name} is not a valid UUID"
        ) from exc


def _optional_uuid(value: Any) -> UUID | None:
    return None if value is None else _required_uuid(value, "optional UUID")


def _required_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise IndustryBeneficiaryWorkspaceDataError(
            f"{field_name} is not an integer"
        )
    return value


def _required_text(value: Any, field_name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise IndustryBeneficiaryWorkspaceDataError(f"{field_name} is not text")
    normalized = value.strip()
    if not normalized and not allow_empty:
        raise IndustryBeneficiaryWorkspaceDataError(f"{field_name} is empty")
    return normalized if not allow_empty else value


def _required_date(value: Any, field_name: str) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise IndustryBeneficiaryWorkspaceDataError(f"{field_name} is not a date")
    return value


def _optional_date(value: Any) -> date | None:
    if value is None:
        return None
    return _required_date(value, "optional date")


def _required_utc(value: Any, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise IndustryBeneficiaryWorkspaceDataError(
            f"{field_name} is not a timestamp"
        )
    return stored_utc(value)

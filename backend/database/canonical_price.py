"""Transactional canonical-price commands and exact as-of reads."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
import math
from threading import Lock, RLock
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from backend.database.canonical_price_models import (
    CanonicalPrice,
    CanonicalPriceRevision,
    CanonicalPriceSeries,
    CanonicalPriceSeriesRevision,
    ComparisonEligibilityAssessment,
    ComparisonEligibilityMember,
    ComparisonEligibilityRevision,
    ListedInstrument,
    ListedInstrumentRevision,
)
from backend.database.models import DailyPriceRecord, IngestionRun


PURPOSE = "company_research_price_context_v1"
RULE_VERSION = "aquantai.company-research-price-context-eligibility.v1"
REASON_CODES = frozenset(
    {
        "canonical_price_accepted", "canonical_price_missing",
        "canonical_price_not_visible", "canonical_price_conflicting",
        "canonical_price_rejected", "instrument_revision_mismatch",
        "market_missing", "exchange_missing", "currency_missing", "unit_mismatch",
        "price_kind_mismatch", "adjustment_basis_mismatch", "trade_date_mismatch",
        "source_contract_mismatch", "source_run_not_succeeded",
        "source_numeric_fidelity_disclosed", "stale_for_requested_context",
        "purpose_not_supported",
    }
)
ELIGIBILITY_STATES = frozenset(
    {"eligible", "ineligible", "missing", "stale", "conflicting", "not_applicable"}
)
_LOCK_GUARD = Lock()
_LOCKS: dict[tuple[str, str], RLock] = {}


class CanonicalPriceError(RuntimeError):
    """Stable public failure with credential-safe text."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class CanonicalPriceNotFound(CanonicalPriceError):
    pass


def _lock(kind: str, key: str) -> RLock:
    with _LOCK_GUARD:
        return _LOCKS.setdefault((kind, key), RLock())


def canonicalize_float(value: float, scale: int) -> tuple[str, str, Decimal]:
    """Apply the reviewed float round-trip Decimal rule."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise CanonicalPriceError("canonical_source_value_invalid", "source close must be numeric")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise CanonicalPriceError("canonical_source_value_invalid", "source close must be finite and positive")
    if not isinstance(scale, int) or isinstance(scale, bool) or not 0 <= scale <= 10:
        raise CanonicalPriceError("canonical_contract_invalid", "decimal_scale must be between 0 and 10")
    source_text = repr(number)
    try:
        source_decimal = Decimal(source_text)
        standardized = source_decimal.quantize(Decimal(1).scaleb(-scale), rounding=ROUND_HALF_EVEN)
    except (InvalidOperation, ValueError) as exc:
        raise CanonicalPriceError("canonical_source_value_invalid", "source close cannot be canonicalized") from exc
    integer_digits = max(1, standardized.adjusted() + 1)
    if standardized <= 0 or integer_digits > 18 or len(format(standardized, "f")) > 64:
        raise CanonicalPriceError("canonical_source_value_invalid", "canonical value is outside the accepted bounds")
    return source_text, format(standardized, "f"), standardized


class CanonicalPriceCommandService:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def record_listed_instrument(self, raw: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
        data = _listed_input(raw)
        return self._execute("instrument", data["instrument_key"], dry_run, lambda s: self._listed(s, data, dry_run))

    def record_series(self, raw: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
        data = _series_input(raw)
        return self._execute("series", data["series_contract_key"], dry_run, lambda s: self._series(s, data, dry_run))

    def record_price(self, raw: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
        data = _price_input(raw)
        key = f"{data['series_id']}:{data['trade_date']}"
        return self._execute("price", key, dry_run, lambda s: self._price(s, data, dry_run))

    def record_eligibility(self, raw: dict[str, Any], *, dry_run: bool = False) -> dict[str, Any]:
        data = _eligibility_input(raw)
        return self._execute("eligibility", f"{data['assessment_key']}:{data['purpose_code']}", dry_run, lambda s: self._eligibility(s, data, dry_run))

    def _execute(self, kind: str, key: str, dry_run: bool, action: Callable[[Session], dict[str, Any]]) -> dict[str, Any]:
        try:
            with _lock(kind, key):
                if dry_run:
                    with self._session_factory() as session:
                        return action(session)
                with self._session_factory.begin() as session:
                    return action(session)
        except IntegrityError as exc:
            raise CanonicalPriceError("canonical_revision_conflict", "canonical history conflicts with an accepted revision") from exc

    def _listed(self, session: Session, data: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        identity = session.scalar(select(ListedInstrument).where(ListedInstrument.instrument_key == data["instrument_key"]).with_for_update())
        latest = _latest(session, ListedInstrumentRevision, "instrument_id", None if identity is None else identity.id)
        _expected(data["expected_latest_revision_id"], latest)
        _chronology(data, latest)
        result = {"dry_run": dry_run, "instrument_key": data["instrument_key"], "next_revision_no": 1 if latest is None else latest.revision_no + 1}
        if dry_run:
            return result
        if identity is None:
            identity = ListedInstrument(instrument_key=data["instrument_key"], created_at_utc=data["recorded_at_utc"])
            session.add(identity); session.flush()
        revision = ListedInstrumentRevision(
            instrument_id=identity.id, revision_no=result["next_revision_no"],
            supersedes_revision_id=None if latest is None else latest.id,
            **{k: data[k] for k in ("canonical_symbol", "security_type", "market_code", "exchange_code_namespace", "exchange_code", "currency_code", "listing_date", "delisting_date", "listing_status", "recorded_by", "information_cutoff_date", "recorded_at_utc")},
        )
        session.add(revision); session.flush()
        return {**result, "instrument_id": str(identity.id), "instrument_revision_id": str(revision.id)}

    def _series(self, session: Session, data: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        instrument = session.get(ListedInstrument, data["instrument_id"])
        revision = session.get(ListedInstrumentRevision, data["instrument_revision_id"])
        if instrument is None or revision is None or revision.instrument_id != instrument.id:
            raise CanonicalPriceError("canonical_identity_incomplete", "exact listed instrument revision is required")
        _visible_upstream(revision, data)
        if revision.currency_code != data["currency_code"]:
            raise CanonicalPriceError("canonical_contract_invalid", "series currency must match the listed instrument revision")
        identity = session.scalar(select(CanonicalPriceSeries).where(CanonicalPriceSeries.series_contract_key == data["series_contract_key"]).with_for_update())
        if identity is not None and identity.instrument_id != instrument.id:
            raise CanonicalPriceError("canonical_contract_invalid", "series contract key belongs to another instrument")
        latest = _latest(session, CanonicalPriceSeriesRevision, "series_id", None if identity is None else identity.id)
        _expected(data["expected_latest_revision_id"], latest); _chronology(data, latest)
        result = {"dry_run": dry_run, "series_contract_key": data["series_contract_key"], "next_revision_no": 1 if latest is None else latest.revision_no + 1}
        if dry_run: return result
        if identity is None:
            identity = CanonicalPriceSeries(series_contract_key=data["series_contract_key"], instrument_id=instrument.id, created_at_utc=data["recorded_at_utc"])
            session.add(identity); session.flush()
        fields = ("instrument_revision_id", "provider", "dataset", "series_key", "source_stock_code", "source_adjust_type", "price_kind", "adjustment_basis", "unit_code", "currency_code", "decimal_scale", "decimal_rule_code", "rounding_mode", "status", "recorded_by", "information_cutoff_date", "recorded_at_utc")
        row = CanonicalPriceSeriesRevision(series_id=identity.id, revision_no=result["next_revision_no"], supersedes_revision_id=None if latest is None else latest.id, **{k: data[k] for k in fields})
        session.add(row); session.flush()
        return {**result, "series_id": str(identity.id), "series_revision_id": str(row.id)}

    def _price(self, session: Session, data: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        series = session.get(CanonicalPriceSeries, data["series_id"])
        contract = session.get(CanonicalPriceSeriesRevision, data["series_revision_id"])
        instrument_revision = session.get(ListedInstrumentRevision, data["instrument_revision_id"])
        source = session.get(DailyPriceRecord, data["source_daily_price_id"])
        run = session.get(IngestionRun, data["source_ingestion_run_id"])
        if series is None or contract is None or contract.series_id != series.id or contract.status != "accepted":
            raise CanonicalPriceError("source_contract_mismatch", "exact accepted series contract revision is required")
        if instrument_revision is None or contract.instrument_revision_id != instrument_revision.id:
            raise CanonicalPriceError("instrument_revision_mismatch", "instrument revision does not match the series contract")
        if source is None or run is None or source.ingestion_run_id != run.id:
            raise CanonicalPriceError("source_contract_mismatch", "exact source row and ingestion run relationship is required")
        if run.status != "succeeded" or run.completed_at is None:
            raise CanonicalPriceError("source_run_not_succeeded", "source ingestion run must be succeeded")
        if _stored_utc(run.completed_at) < _stored_utc(run.imported_at):
            raise CanonicalPriceError("source_contract_mismatch", "source ingestion completion chronology is invalid")
        if run.provider != contract.provider or run.dataset != contract.dataset or run.series_key != contract.series_key:
            raise CanonicalPriceError("source_contract_mismatch", "source run does not match the frozen series contract")
        if source.source != contract.provider or source.stock_code != contract.source_stock_code or source.adjust_type != contract.source_adjust_type or source.trade_date != data["trade_date"]:
            raise CanonicalPriceError("source_contract_mismatch", "source row does not match the frozen series contract")
        if source.trade_date < instrument_revision.listing_date or (
            instrument_revision.delisting_date is not None
            and source.trade_date > instrument_revision.delisting_date
        ):
            raise CanonicalPriceError("canonical_identity_invalid", "source trade date is outside the explicit listing chronology")
        for upstream in (contract, instrument_revision): _visible_upstream(upstream, data)
        completed = _stored_utc(run.completed_at)
        if run.information_cutoff_date > data["information_cutoff_date"] or completed > data["recorded_at_utc"]:
            raise CanonicalPriceError("source_contract_mismatch", "source run is later than the canonical revision boundary")
        source_text, standardized_text, decimal_value = canonicalize_float(source.close, contract.decimal_scale)
        identity = session.scalar(select(CanonicalPrice).where(
            CanonicalPrice.series_id == series.id, CanonicalPrice.trade_date == data["trade_date"],
            CanonicalPrice.price_kind == contract.price_kind, CanonicalPrice.adjustment_basis == contract.adjustment_basis,
        ).with_for_update())
        latest = _latest(session, CanonicalPriceRevision, "canonical_price_id", None if identity is None else identity.id)
        _expected(data["expected_latest_revision_id"], latest); _chronology(data, latest)
        result = {"dry_run": dry_run, "next_revision_no": 1 if latest is None else latest.revision_no + 1, "source_value_text": source_text, "standardized_value_text": standardized_text, "value_decimal": standardized_text, "numeric_fidelity": "binary_float_normalized"}
        if dry_run: return result
        if identity is None:
            identity = CanonicalPrice(series_id=series.id, trade_date=data["trade_date"], price_kind=contract.price_kind, adjustment_basis=contract.adjustment_basis, created_at_utc=data["recorded_at_utc"])
            session.add(identity); session.flush()
        row = CanonicalPriceRevision(
            canonical_price_id=identity.id, revision_no=result["next_revision_no"], series_revision_id=contract.id,
            instrument_revision_id=instrument_revision.id, source_daily_price_id=source.id, source_ingestion_run_id=run.id,
            source_value_text=source_text, standardized_value_text=standardized_text, value_decimal=decimal_value,
            numeric_fidelity="binary_float_normalized", currency_code=contract.currency_code, unit_code=contract.unit_code,
            trade_date=data["trade_date"], canonical_status=data["canonical_status"], conflict_summary=data["conflict_summary"],
            recorded_by=data["recorded_by"], information_cutoff_date=data["information_cutoff_date"], recorded_at_utc=data["recorded_at_utc"],
            supersedes_revision_id=None if latest is None else latest.id,
        )
        session.add(row); session.flush()
        return {**result, "canonical_price_id": str(identity.id), "canonical_price_revision_id": str(row.id)}

    def _eligibility(self, session: Session, data: dict[str, Any], dry_run: bool) -> dict[str, Any]:
        prices: list[CanonicalPriceRevision] = []
        for price_id in data["canonical_price_revision_ids"]:
            row = session.get(CanonicalPriceRevision, price_id)
            if row is None: raise CanonicalPriceError("canonical_price_missing", "exact canonical price revision was not found")
            _visible_upstream(row, data); prices.append(row)
        _validate_eligibility(data, prices)
        identity = session.scalar(select(ComparisonEligibilityAssessment).where(
            ComparisonEligibilityAssessment.assessment_key == data["assessment_key"],
            ComparisonEligibilityAssessment.purpose_code == data["purpose_code"],
        ).with_for_update())
        latest = _latest(session, ComparisonEligibilityRevision, "assessment_id", None if identity is None else identity.id)
        _expected(data["expected_latest_revision_id"], latest); _chronology(data, latest)
        result = {"dry_run": dry_run, "assessment_key": data["assessment_key"], "next_revision_no": 1 if latest is None else latest.revision_no + 1, "state": data["state"], "reason_codes": list(data["reason_codes"]), "member_count": len(prices)}
        if dry_run: return result
        if identity is None:
            identity = ComparisonEligibilityAssessment(assessment_key=data["assessment_key"], purpose_code=data["purpose_code"], created_at_utc=data["recorded_at_utc"])
            session.add(identity); session.flush()
        revision = ComparisonEligibilityRevision(
            assessment_id=identity.id, revision_no=result["next_revision_no"], rule_version=data["rule_version"], state=data["state"], reason_codes=list(data["reason_codes"]),
            requested_trade_date=data["requested_trade_date"], recorded_by=data["recorded_by"], information_cutoff_date=data["information_cutoff_date"], recorded_at_utc=data["recorded_at_utc"], supersedes_revision_id=None if latest is None else latest.id,
        )
        session.add(revision); session.flush()
        for position, price in enumerate(prices):
            session.add(ComparisonEligibilityMember(eligibility_revision_id=revision.id, position=position, canonical_price_revision_id=price.id, recorded_at_utc=data["recorded_at_utc"]))
        session.flush()
        return {**result, "assessment_id": str(identity.id), "eligibility_revision_id": str(revision.id)}


class CanonicalPriceQueryService:
    def __init__(self, session: Session) -> None: self._session = session

    def get_instrument(self, identity_id: UUID, *, as_of_cutoff: date, as_of_recorded_at_utc: datetime) -> dict[str, Any]:
        as_of_recorded_at_utc = _read_boundary(as_of_cutoff, as_of_recorded_at_utc)
        identity = self._session.get(ListedInstrument, identity_id)
        if identity is None: raise CanonicalPriceNotFound("listed_instrument_not_found", "listed instrument was not found")
        revision = _as_of_revision(self._session, ListedInstrumentRevision, "instrument_id", identity.id, as_of_cutoff, as_of_recorded_at_utc)
        if revision is None: raise CanonicalPriceNotFound("listed_instrument_not_visible", "listed instrument is not visible at the requested boundaries")
        return {"instrument_id": str(identity.id), "instrument_key": identity.instrument_key, "revision": _instrument_payload(revision)}

    def get_price(self, identity_id: UUID, *, as_of_cutoff: date, as_of_recorded_at_utc: datetime) -> dict[str, Any]:
        as_of_recorded_at_utc = _read_boundary(as_of_cutoff, as_of_recorded_at_utc)
        identity = self._session.get(CanonicalPrice, identity_id)
        if identity is None: raise CanonicalPriceNotFound("canonical_price_not_found", "canonical price was not found")
        revision = _as_of_revision(self._session, CanonicalPriceRevision, "canonical_price_id", identity.id, as_of_cutoff, as_of_recorded_at_utc)
        if revision is None: raise CanonicalPriceNotFound("canonical_price_not_visible", "canonical price is not visible at the requested boundaries")
        contract = self._session.get(CanonicalPriceSeriesRevision, revision.series_revision_id)
        instrument = self._session.get(ListedInstrumentRevision, revision.instrument_revision_id)
        run = self._session.get(IngestionRun, revision.source_ingestion_run_id)
        source = self._session.get(DailyPriceRecord, revision.source_daily_price_id)
        if None in (contract, instrument, run, source) or source.ingestion_run_id != run.id:
            raise CanonicalPriceError("canonical_graph_inconsistent", "canonical price provenance is incomplete")
        if (
            contract.series_id != identity.series_id
            or contract.instrument_revision_id != instrument.id
            or identity.trade_date != revision.trade_date
            or identity.price_kind != contract.price_kind
            or identity.adjustment_basis != contract.adjustment_basis
            or revision.currency_code != contract.currency_code
            or revision.unit_code != contract.unit_code
            or run.status != "succeeded"
            or run.provider != contract.provider
            or run.dataset != contract.dataset
            or run.series_key != contract.series_key
            or source.source != contract.provider
            or source.stock_code != contract.source_stock_code
            or source.adjust_type != contract.source_adjust_type
            or source.trade_date != identity.trade_date
        ):
            raise CanonicalPriceError("canonical_graph_inconsistent", "canonical price provenance does not match the frozen contract")
        source_text, standardized_text, decimal_value = canonicalize_float(source.close, contract.decimal_scale)
        if (
            source_text != revision.source_value_text
            or standardized_text != revision.standardized_value_text
            or decimal_value != revision.value_decimal
        ):
            raise CanonicalPriceError("canonical_graph_inconsistent", "canonical source value no longer matches the frozen revision")
        if not _visible(contract, as_of_cutoff, as_of_recorded_at_utc) or not _visible(instrument, as_of_cutoff, as_of_recorded_at_utc):
            raise CanonicalPriceNotFound("canonical_price_not_visible", "canonical price provenance is not visible at the requested boundaries")
        if not _visible(contract, revision.information_cutoff_date, _stored_utc(revision.recorded_at_utc)) or not _visible(
            instrument,
            revision.information_cutoff_date,
            _stored_utc(revision.recorded_at_utc),
        ):
            raise CanonicalPriceError("canonical_graph_inconsistent", "canonical upstream revisions exceed the frozen price boundary")
        if (
            run.information_cutoff_date > as_of_cutoff
            or run.completed_at is None
            or _stored_utc(run.completed_at) < _stored_utc(run.imported_at)
            or _stored_utc(run.completed_at) > as_of_recorded_at_utc
            or run.information_cutoff_date > revision.information_cutoff_date
            or _stored_utc(run.completed_at) > _stored_utc(revision.recorded_at_utc)
        ):
            raise CanonicalPriceNotFound("canonical_price_not_visible", "canonical source run is not visible at the requested boundaries")
        return {"canonical_price_id": str(identity.id), "series_id": str(identity.series_id), "trade_date": identity.trade_date.isoformat(), "price_kind": identity.price_kind, "adjustment_basis": identity.adjustment_basis, "revision": _price_payload(revision), "series_revision": _series_payload(contract), "instrument_revision": _instrument_payload(instrument), "source": {"daily_price_id": source.id, "ingestion_run_id": run.id, "provider": run.provider, "dataset": run.dataset, "series_key": run.series_key, "information_cutoff_date": run.information_cutoff_date.isoformat(), "completed_at_utc": _iso(run.completed_at)}}

    def get_eligibility(self, identity_id: UUID, *, as_of_cutoff: date, as_of_recorded_at_utc: datetime) -> dict[str, Any]:
        as_of_recorded_at_utc = _read_boundary(as_of_cutoff, as_of_recorded_at_utc)
        identity = self._session.get(ComparisonEligibilityAssessment, identity_id)
        if identity is None: raise CanonicalPriceNotFound("eligibility_not_found", "comparison eligibility assessment was not found")
        revision = _as_of_revision(self._session, ComparisonEligibilityRevision, "assessment_id", identity.id, as_of_cutoff, as_of_recorded_at_utc)
        if revision is None: raise CanonicalPriceNotFound("eligibility_not_visible", "comparison eligibility is not visible at the requested boundaries")
        members = tuple(self._session.scalars(select(ComparisonEligibilityMember).where(ComparisonEligibilityMember.eligibility_revision_id == revision.id).order_by(ComparisonEligibilityMember.position, ComparisonEligibilityMember.id)))
        payloads = []
        for member in members:
            if _stored_utc(member.recorded_at_utc) > as_of_recorded_at_utc: raise CanonicalPriceError("canonical_graph_inconsistent", "eligibility member is outside the frozen boundary")
            price = self._session.get(CanonicalPriceRevision, member.canonical_price_revision_id)
            if price is None or not _visible(price, as_of_cutoff, as_of_recorded_at_utc): raise CanonicalPriceError("canonical_graph_inconsistent", "eligibility member price is not visible")
            if not _visible(price, revision.information_cutoff_date, _stored_utc(revision.recorded_at_utc)):
                raise CanonicalPriceError("canonical_graph_inconsistent", "eligibility member exceeds the frozen assessment boundary")
            payloads.append({"position": member.position, "canonical_price_revision": _price_payload(price)})
        reasons = revision.reason_codes
        if (
            not isinstance(reasons, list)
            or any(not isinstance(item, str) or item not in REASON_CODES for item in reasons)
            or reasons != sorted(set(reasons))
        ):
            raise CanonicalPriceError("canonical_graph_inconsistent", "eligibility reasons are not canonical")
        _validate_eligibility(
            {
                "purpose_code": identity.purpose_code,
                "rule_version": revision.rule_version,
                "state": revision.state,
                "reason_codes": tuple(reasons),
                "requested_trade_date": revision.requested_trade_date,
            },
            [self._session.get(CanonicalPriceRevision, member.canonical_price_revision_id) for member in members],
        )
        return {"assessment_id": str(identity.id), "assessment_key": identity.assessment_key, "purpose_code": identity.purpose_code, "revision": {"id": str(revision.id), "revision_no": revision.revision_no, "rule_version": revision.rule_version, "state": revision.state, "reason_codes": list(revision.reason_codes), "requested_trade_date": revision.requested_trade_date.isoformat(), "information_cutoff_date": revision.information_cutoff_date.isoformat(), "recorded_at_utc": _iso(revision.recorded_at_utc)}, "members": payloads}


def _listed_input(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {"instrument_key", "expected_latest_revision_id", "canonical_symbol", "security_type", "market_code", "exchange_code_namespace", "exchange_code", "currency_code", "listing_date", "delisting_date", "listing_status", "recorded_by", "information_cutoff_date", "recorded_at_utc"}
    _strict(raw, allowed)
    for field in ("market_code", "exchange_code_namespace", "exchange_code", "currency_code"):
        if not isinstance(raw.get(field), str) or not raw[field].strip():
            raise CanonicalPriceError(
                "canonical_identity_incomplete",
                "explicit market, exchange namespace, exchange, and currency are required",
            )
    result = _common(raw)
    result.update(instrument_key=_text(raw.get("instrument_key"), "instrument_key", 160), expected_latest_revision_id=_optional_uuid(raw.get("expected_latest_revision_id")), canonical_symbol=_text(raw.get("canonical_symbol"), "canonical_symbol", 64), security_type=_choice(raw.get("security_type"), {"common_equity"}, "security_type"), market_code=_text(raw.get("market_code"), "market_code", 32).upper(), exchange_code_namespace=_text(raw.get("exchange_code_namespace"), "exchange_code_namespace", 32).upper(), exchange_code=_text(raw.get("exchange_code"), "exchange_code", 32).upper(), currency_code=_currency(raw.get("currency_code")), listing_date=_date(raw.get("listing_date"), "listing_date"), delisting_date=None if raw.get("delisting_date") is None else _date(raw.get("delisting_date"), "delisting_date"), listing_status=_choice(raw.get("listing_status"), {"active", "suspended", "delisted"}, "listing_status"))
    if result["delisting_date"] is not None and result["delisting_date"] < result["listing_date"]: raise CanonicalPriceError("canonical_identity_invalid", "delisting_date cannot precede listing_date")
    if result["listing_date"] > result["information_cutoff_date"]:
        raise CanonicalPriceError("canonical_identity_invalid", "listing_date cannot be later than the information cutoff")
    if (result["listing_status"] == "delisted") != (result["delisting_date"] is not None):
        raise CanonicalPriceError("canonical_identity_invalid", "delisted status and delisting_date must be provided together")
    return result


def _series_input(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {"series_contract_key", "instrument_id", "instrument_revision_id", "expected_latest_revision_id", "provider", "dataset", "series_key", "source_stock_code", "source_adjust_type", "price_kind", "adjustment_basis", "unit_code", "currency_code", "decimal_scale", "decimal_rule_code", "rounding_mode", "status", "recorded_by", "information_cutoff_date", "recorded_at_utc"}
    _strict(raw, allowed); result = _common(raw)
    scale = raw.get("decimal_scale")
    if not isinstance(scale, int) or isinstance(scale, bool) or not 0 <= scale <= 10: raise CanonicalPriceError("canonical_contract_invalid", "decimal_scale must be between 0 and 10")
    result.update(series_contract_key=_text(raw.get("series_contract_key"), "series_contract_key", 160), instrument_id=_uuid(raw.get("instrument_id"), "instrument_id"), instrument_revision_id=_uuid(raw.get("instrument_revision_id"), "instrument_revision_id"), expected_latest_revision_id=_optional_uuid(raw.get("expected_latest_revision_id")), provider=_text(raw.get("provider"), "provider", 64), dataset=_text(raw.get("dataset"), "dataset", 64), series_key=_text(raw.get("series_key"), "series_key", 64), source_stock_code=_text(raw.get("source_stock_code"), "source_stock_code", 64), source_adjust_type=_text_allow_empty(raw.get("source_adjust_type"), "source_adjust_type", 32), price_kind=_choice(raw.get("price_kind"), {"official_close"}, "price_kind"), adjustment_basis=_choice(raw.get("adjustment_basis"), {"unadjusted", "forward_adjusted", "backward_adjusted"}, "adjustment_basis"), unit_code=_choice(raw.get("unit_code"), {"currency_per_share"}, "unit_code"), currency_code=_currency(raw.get("currency_code")), decimal_scale=scale, decimal_rule_code=_choice(raw.get("decimal_rule_code"), {"float_repr_decimal_v1"}, "decimal_rule_code"), rounding_mode=_choice(raw.get("rounding_mode"), {"ROUND_HALF_EVEN"}, "rounding_mode"), status=_choice(raw.get("status"), {"draft", "accepted", "retired"}, "status"))
    if len(result["series_key"]) != 64:
        raise CanonicalPriceError("canonical_contract_invalid", "series_key must contain exactly 64 characters")
    return result


def _price_input(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {"series_id", "series_revision_id", "instrument_revision_id", "source_daily_price_id", "source_ingestion_run_id", "trade_date", "expected_latest_revision_id", "canonical_status", "conflict_summary", "recorded_by", "information_cutoff_date", "recorded_at_utc"}
    _strict(raw, allowed); result = _common(raw)
    status = _choice(raw.get("canonical_status"), {"accepted", "conflicting", "rejected"}, "canonical_status")
    conflict = _optional_text(raw.get("conflict_summary"), "conflict_summary", 2000)
    if (status == "conflicting") != (conflict is not None): raise CanonicalPriceError("canonical_status_invalid", "only conflicting status requires conflict_summary")
    result.update(series_id=_uuid(raw.get("series_id"), "series_id"), series_revision_id=_uuid(raw.get("series_revision_id"), "series_revision_id"), instrument_revision_id=_uuid(raw.get("instrument_revision_id"), "instrument_revision_id"), source_daily_price_id=_positive_int(raw.get("source_daily_price_id"), "source_daily_price_id"), source_ingestion_run_id=_positive_int(raw.get("source_ingestion_run_id"), "source_ingestion_run_id"), trade_date=_date(raw.get("trade_date"), "trade_date"), expected_latest_revision_id=_optional_uuid(raw.get("expected_latest_revision_id")), canonical_status=status, conflict_summary=conflict)
    if result["trade_date"] > result["information_cutoff_date"]:
        raise CanonicalPriceError("canonical_chronology_invalid", "trade_date cannot be later than the information cutoff")
    return result


def _eligibility_input(raw: dict[str, Any]) -> dict[str, Any]:
    allowed = {"assessment_key", "purpose_code", "expected_latest_revision_id", "rule_version", "state", "reason_codes", "requested_trade_date", "canonical_price_revision_ids", "recorded_by", "information_cutoff_date", "recorded_at_utc"}
    _strict(raw, allowed); result = _common(raw)
    reasons = raw.get("reason_codes")
    if not isinstance(reasons, list) or any(not isinstance(x, str) or x not in REASON_CODES for x in reasons) or reasons != sorted(set(reasons)): raise CanonicalPriceError("eligibility_invalid", "reason_codes must be a sorted unique list from the v1 vocabulary")
    ids = raw.get("canonical_price_revision_ids")
    if not isinstance(ids, list) or len(ids) > 100: raise CanonicalPriceError("eligibility_invalid", "canonical_price_revision_ids must be a bounded array")
    parsed_ids = tuple(_uuid(x, "canonical_price_revision_ids") for x in ids)
    if len(set(parsed_ids)) != len(parsed_ids): raise CanonicalPriceError("eligibility_invalid", "canonical price members must be unique")
    result.update(assessment_key=_text(raw.get("assessment_key"), "assessment_key", 160), purpose_code=_text(raw.get("purpose_code"), "purpose_code", 64), expected_latest_revision_id=_optional_uuid(raw.get("expected_latest_revision_id")), rule_version=_text(raw.get("rule_version"), "rule_version", 96), state=_choice(raw.get("state"), ELIGIBILITY_STATES, "state"), reason_codes=tuple(reasons), requested_trade_date=_date(raw.get("requested_trade_date"), "requested_trade_date"), canonical_price_revision_ids=parsed_ids)
    if result["requested_trade_date"] > result["information_cutoff_date"]:
        raise CanonicalPriceError("canonical_chronology_invalid", "requested_trade_date cannot be later than the information cutoff")
    return result


def _validate_eligibility(data: dict[str, Any], prices: list[CanonicalPriceRevision]) -> None:
    if data["purpose_code"] != PURPOSE:
        if data["state"] != "not_applicable" or data["reason_codes"] != ("purpose_not_supported",) or prices: raise CanonicalPriceError("eligibility_invalid", "unsupported purpose must be not_applicable with no members")
        return
    if data["rule_version"] != RULE_VERSION: raise CanonicalPriceError("eligibility_invalid", "rule_version is not accepted for the v1 purpose")
    if data["state"] == "not_applicable":
        raise CanonicalPriceError("eligibility_invalid", "the supported v1 purpose cannot use not_applicable")
    if data["state"] == "eligible":
        if not prices or any(p.canonical_status != "accepted" or p.trade_date != data["requested_trade_date"] for p in prices): raise CanonicalPriceError("eligibility_invalid", "eligible members must be accepted prices for the requested trade date")
        required = ("canonical_price_accepted", "source_numeric_fidelity_disclosed")
        if data["reason_codes"] != required: raise CanonicalPriceError("eligibility_invalid", "eligible state requires exactly the accepted and fidelity reason codes")
    elif prices and data["state"] in {"missing", "not_applicable"}: raise CanonicalPriceError("eligibility_invalid", "missing and not_applicable states cannot have members")
    if data["state"] == "conflicting" and not any(price.canonical_status == "conflicting" for price in prices):
        raise CanonicalPriceError("eligibility_invalid", "conflicting state requires a conflicting canonical price member")
    if "canonical_price_rejected" in data["reason_codes"] and not any(price.canonical_status == "rejected" for price in prices):
        raise CanonicalPriceError("eligibility_invalid", "rejected reason requires a rejected canonical price member")
    if data["state"] == "stale" and not any(price.trade_date != data["requested_trade_date"] for price in prices):
        raise CanonicalPriceError("eligibility_invalid", "stale state requires a member outside the requested trade date")
    required_reason = {
        "missing": {"canonical_price_missing", "canonical_price_not_visible"},
        "stale": {"stale_for_requested_context"},
        "conflicting": {"canonical_price_conflicting"},
        "ineligible": {
            "canonical_price_rejected", "instrument_revision_mismatch", "market_missing",
            "exchange_missing", "currency_missing", "unit_mismatch", "price_kind_mismatch",
            "adjustment_basis_mismatch", "trade_date_mismatch", "source_contract_mismatch",
            "source_run_not_succeeded",
        },
    }.get(data["state"])
    if required_reason is not None and not required_reason.intersection(data["reason_codes"]):
        raise CanonicalPriceError("eligibility_invalid", "eligibility state lacks a compatible reason code")


def _common(raw: dict[str, Any]) -> dict[str, Any]:
    cutoff = _date(raw.get("information_cutoff_date"), "information_cutoff_date")
    recorded = _datetime(raw.get("recorded_at_utc"), "recorded_at_utc")
    if cutoff > recorded.date(): raise CanonicalPriceError("canonical_chronology_invalid", "information_cutoff_date cannot be later than recorded_at_utc")
    return {"recorded_by": _text(raw.get("recorded_by"), "recorded_by", 100), "information_cutoff_date": cutoff, "recorded_at_utc": recorded}


def _strict(raw: Any, allowed: set[str]) -> None:
    if not isinstance(raw, dict): raise CanonicalPriceError("canonical_input_invalid", "input must be a JSON object")
    unknown = sorted(set(raw) - allowed)
    if unknown: raise CanonicalPriceError("canonical_input_invalid", f"unknown fields: {', '.join(unknown)}")


def _latest(session: Session, model: Any, foreign_key: str, identity_id: UUID | None) -> Any:
    if identity_id is None: return None
    return session.scalar(select(model).where(getattr(model, foreign_key) == identity_id).order_by(model.revision_no.desc()).limit(1).with_for_update())


def _expected(expected: UUID | None, latest: Any) -> None:
    if (latest is None and expected is not None) or (latest is not None and expected != latest.id): raise CanonicalPriceError("canonical_revision_conflict", "expected_latest_revision_id does not match accepted history")


def _chronology(data: dict[str, Any], latest: Any) -> None:
    if latest is not None and (data["information_cutoff_date"] < latest.information_cutoff_date or data["recorded_at_utc"] < _stored_utc(latest.recorded_at_utc)): raise CanonicalPriceError("canonical_chronology_invalid", "revision chronology cannot move backward")


def _visible_upstream(row: Any, data: dict[str, Any]) -> None:
    if row.information_cutoff_date > data["information_cutoff_date"] or _stored_utc(row.recorded_at_utc) > data["recorded_at_utc"]: raise CanonicalPriceError("canonical_chronology_invalid", "frozen upstream revision is outside the requested boundary")


def _visible(row: Any, cutoff: date, recorded: datetime) -> bool:
    return row.information_cutoff_date <= cutoff and _stored_utc(row.recorded_at_utc) <= recorded


def _as_of_revision(session: Session, model: Any, foreign_key: str, identity_id: UUID, cutoff: date, recorded: datetime) -> Any:
    return session.scalar(select(model).where(getattr(model, foreign_key) == identity_id, model.information_cutoff_date <= cutoff, model.recorded_at_utc <= recorded).order_by(model.revision_no.desc()).limit(1))


def _instrument_payload(row: ListedInstrumentRevision) -> dict[str, Any]:
    return {"id": str(row.id), "revision_no": row.revision_no, "canonical_symbol": row.canonical_symbol, "security_type": row.security_type, "market_code": row.market_code, "exchange_code_namespace": row.exchange_code_namespace, "exchange_code": row.exchange_code, "currency_code": row.currency_code, "listing_date": row.listing_date.isoformat(), "delisting_date": None if row.delisting_date is None else row.delisting_date.isoformat(), "listing_status": row.listing_status, "information_cutoff_date": row.information_cutoff_date.isoformat(), "recorded_at_utc": _iso(row.recorded_at_utc)}


def _series_payload(row: CanonicalPriceSeriesRevision) -> dict[str, Any]:
    return {"id": str(row.id), "revision_no": row.revision_no, "provider": row.provider, "dataset": row.dataset, "series_key": row.series_key, "source_stock_code": row.source_stock_code, "source_adjust_type": row.source_adjust_type, "price_kind": row.price_kind, "adjustment_basis": row.adjustment_basis, "unit_code": row.unit_code, "currency_code": row.currency_code, "decimal_scale": row.decimal_scale, "decimal_rule_code": row.decimal_rule_code, "rounding_mode": row.rounding_mode, "status": row.status, "information_cutoff_date": row.information_cutoff_date.isoformat(), "recorded_at_utc": _iso(row.recorded_at_utc)}


def _price_payload(row: CanonicalPriceRevision) -> dict[str, Any]:
    return {"id": str(row.id), "revision_no": row.revision_no, "series_revision_id": str(row.series_revision_id), "instrument_revision_id": str(row.instrument_revision_id), "source_daily_price_id": row.source_daily_price_id, "source_ingestion_run_id": row.source_ingestion_run_id, "source_value_text": row.source_value_text, "standardized_value_text": row.standardized_value_text, "value_decimal": row.standardized_value_text, "numeric_fidelity": row.numeric_fidelity, "currency_code": row.currency_code, "unit_code": row.unit_code, "trade_date": row.trade_date.isoformat(), "canonical_status": row.canonical_status, "conflict_summary": row.conflict_summary, "information_cutoff_date": row.information_cutoff_date.isoformat(), "recorded_at_utc": _iso(row.recorded_at_utc)}


def _text(value: Any, label: str, maximum: int) -> str:
    if not isinstance(value, str): raise CanonicalPriceError("canonical_input_invalid", f"{label} must be text")
    result = value.strip()
    if not result or len(result) > maximum: raise CanonicalPriceError("canonical_input_invalid", f"{label} is outside accepted bounds")
    return result


def _text_allow_empty(value: Any, label: str, maximum: int) -> str:
    if not isinstance(value, str) or len(value) > maximum: raise CanonicalPriceError("canonical_input_invalid", f"{label} must be bounded text")
    return value.strip()


def _optional_text(value: Any, label: str, maximum: int) -> str | None:
    return None if value is None else _text(value, label, maximum)


def _choice(value: Any, choices: set[str] | frozenset[str], label: str) -> str:
    if not isinstance(value, str) or value not in choices: raise CanonicalPriceError("canonical_input_invalid", f"{label} is not in the accepted vocabulary")
    return value


def _currency(value: Any) -> str:
    result = _text(value, "currency_code", 3).upper()
    if len(result) != 3 or not result.isalpha(): raise CanonicalPriceError("canonical_identity_incomplete", "currency_code must be an explicit ISO-4217 code")
    return result


def _uuid(value: Any, label: str) -> UUID:
    try: return UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc: raise CanonicalPriceError("canonical_input_invalid", f"{label} must be a UUID") from exc


def _optional_uuid(value: Any) -> UUID | None: return None if value is None else _uuid(value, "expected_latest_revision_id")


def _date(value: Any, label: str) -> date:
    if not isinstance(value, str): raise CanonicalPriceError("canonical_input_invalid", f"{label} must use YYYY-MM-DD")
    try: return date.fromisoformat(value)
    except ValueError as exc: raise CanonicalPriceError("canonical_input_invalid", f"{label} must use YYYY-MM-DD") from exc


def _datetime(value: Any, label: str) -> datetime:
    if not isinstance(value, str): raise CanonicalPriceError("canonical_input_invalid", f"{label} must be an explicit UTC timestamp")
    try: result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc: raise CanonicalPriceError("canonical_input_invalid", f"{label} must be ISO-8601 UTC") from exc
    if result.tzinfo is None or result.utcoffset() != timezone.utc.utcoffset(result): raise CanonicalPriceError("canonical_input_invalid", f"{label} must use UTC")
    return result.astimezone(timezone.utc)


def _positive_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0: raise CanonicalPriceError("canonical_input_invalid", f"{label} must be a positive integer")
    return value


def _stored_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _read_boundary(cutoff: date, recorded: datetime) -> datetime:
    if recorded.tzinfo is None or recorded.utcoffset() != timezone.utc.utcoffset(recorded):
        raise CanonicalPriceError("canonical_boundary_invalid", "as_of_recorded_at_utc must use UTC")
    result = recorded.astimezone(timezone.utc)
    if cutoff > result.date():
        raise CanonicalPriceError("canonical_boundary_invalid", "as_of_cutoff cannot be later than as_of_recorded_at_utc")
    return result


def _iso(value: datetime) -> str: return _stored_utc(value).isoformat().replace("+00:00", "Z")

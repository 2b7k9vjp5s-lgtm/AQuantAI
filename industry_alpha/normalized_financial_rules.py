"""Deterministic structured-financial-observation rules for Slice 5."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
import re

STRUCTURED_FINANCIAL_RULE_VERSION = "aquantai.structured-financial-observation.v1"
AMOUNT_SCALE = Decimal("0.000001")
DECIMAL_TEXT_PATTERN = re.compile(r"^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")

METRIC_CODES = frozenset(
    {
        "diluted_shares_outstanding",
        "revenue",
        "net_profit_attributable",
        "ebitda",
        "free_cash_flow",
        "net_debt",
    }
)
SOURCE_KINDS = frozenset({"actual", "guidance", "consensus", "research_assumption"})
OBSERVATION_STATES = frozenset(
    {"supported", "missing", "disputed", "rejected", "not_applicable"}
)
PERIOD_BASES = frozenset({"instant", "ttm", "fy_actual", "forward_fy1", "forward_fy2"})
ACCOUNTING_SCOPES = frozenset({"consolidated", "consolidated_attributable"})

FLOW_METRICS = frozenset(
    {"revenue", "net_profit_attributable", "ebitda", "free_cash_flow"}
)
CURRENCY_METRICS = FLOW_METRICS | {"net_debt"}


class NormalizedMetricError(RuntimeError):
    """Stable credential-safe public error for normalized metrics."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class StructuredObservationInput:
    """Validated, explicit structured financial observation input."""

    instrument_id: str
    company_research_id: str
    metric_code: str
    source_kind: str
    observation_state: str
    value_text: str | None
    value: Decimal | None
    currency_code: str | None
    unit_code: str
    period_basis: str
    target_period_key: str
    accounting_scope: str
    observation_as_of_date: date
    period_start_date: date | None
    period_end_date: date
    fiscal_year: int | None
    effective_start_date: date | None
    effective_end_date: date | None


def parse_decimal_text(value: str | None, *, required: bool) -> tuple[str | None, Decimal | None]:
    """Parse ordinary bounded decimal text and quantize to storage scale."""

    if value is None:
        if required:
            raise NormalizedMetricError(
                "normalized_financial_value_required", "supported observation requires value_text"
            )
        return None, None
    if not isinstance(value, str):
        raise NormalizedMetricError(
            "normalized_financial_decimal_invalid", "value must be decimal text"
        )
    text = value.strip()
    if not text or len(text) > 128 or DECIMAL_TEXT_PATTERN.fullmatch(text) is None:
        raise NormalizedMetricError(
            "normalized_financial_decimal_invalid",
            "value must be bounded ordinary decimal text without exponent notation",
        )
    try:
        with localcontext() as context:
            context.prec = 50
            number = Decimal(text)
            standardized = number.quantize(AMOUNT_SCALE, rounding=ROUND_HALF_EVEN)
    except (InvalidOperation, ValueError) as exc:
        raise NormalizedMetricError(
            "normalized_financial_decimal_invalid", "value must be valid decimal text"
        ) from exc
    if not number.is_finite():
        raise NormalizedMetricError(
            "normalized_financial_decimal_invalid", "value must be finite"
        )
    digit_count = sum(char.isdigit() for char in format(standardized, "f"))
    if digit_count > 38:
        raise NormalizedMetricError(
            "normalized_financial_decimal_overflow", "value exceeds Numeric(38, 6)"
        )
    return text, standardized


def build_structured_observation(
    *,
    instrument_id: str,
    company_research_id: str,
    metric_code: str,
    source_kind: str,
    observation_state: str,
    value_text: str | None,
    currency_code: str | None,
    unit_code: str,
    period_basis: str,
    target_period_key: str,
    accounting_scope: str,
    observation_as_of_date: date,
    period_end_date: date,
    period_start_date: date | None = None,
    fiscal_year: int | None = None,
    effective_start_date: date | None = None,
    effective_end_date: date | None = None,
) -> StructuredObservationInput:
    """Validate closed vocabularies and metric-specific observation semantics."""

    _bounded_identity(instrument_id, "instrument_id")
    _bounded_identity(company_research_id, "company_research_id")
    _bounded_identity(target_period_key, "target_period_key")
    _require_member(metric_code, METRIC_CODES, "metric_code")
    _require_member(source_kind, SOURCE_KINDS, "source_kind")
    _require_member(observation_state, OBSERVATION_STATES, "observation_state")
    _require_member(period_basis, PERIOD_BASES, "period_basis")
    _require_member(accounting_scope, ACCOUNTING_SCOPES, "accounting_scope")

    value_source, value = parse_decimal_text(
        value_text, required=observation_state == "supported"
    )
    if observation_state != "supported" and value_text is not None:
        raise NormalizedMetricError(
            "normalized_financial_value_forbidden",
            "only supported observations may contain a numeric value",
        )

    if period_start_date is not None and period_start_date > period_end_date:
        raise NormalizedMetricError(
            "normalized_financial_period_invalid", "period start must not exceed period end"
        )
    if observation_as_of_date < period_end_date and source_kind == "actual":
        raise NormalizedMetricError(
            "normalized_financial_chronology_invalid",
            "actual observation cannot be known before its period end",
        )

    _validate_metric_shape(
        metric_code=metric_code,
        source_kind=source_kind,
        currency_code=currency_code,
        unit_code=unit_code,
        period_basis=period_basis,
        accounting_scope=accounting_scope,
        period_start_date=period_start_date,
        fiscal_year=fiscal_year,
        effective_start_date=effective_start_date,
        effective_end_date=effective_end_date,
        observation_state=observation_state,
    )

    return StructuredObservationInput(
        instrument_id=instrument_id.strip(),
        company_research_id=company_research_id.strip(),
        metric_code=metric_code,
        source_kind=source_kind,
        observation_state=observation_state,
        value_text=value_source,
        value=value,
        currency_code=currency_code,
        unit_code=unit_code,
        period_basis=period_basis,
        target_period_key=target_period_key.strip(),
        accounting_scope=accounting_scope,
        observation_as_of_date=observation_as_of_date,
        period_start_date=period_start_date,
        period_end_date=period_end_date,
        fiscal_year=fiscal_year,
        effective_start_date=effective_start_date,
        effective_end_date=effective_end_date,
    )


def _validate_metric_shape(
    *,
    metric_code: str,
    source_kind: str,
    currency_code: str | None,
    unit_code: str,
    period_basis: str,
    accounting_scope: str,
    period_start_date: date | None,
    fiscal_year: int | None,
    effective_start_date: date | None,
    effective_end_date: date | None,
    observation_state: str,
) -> None:
    expected_scope = (
        "consolidated_attributable"
        if metric_code in {"diluted_shares_outstanding", "net_profit_attributable"}
        else "consolidated"
    )
    if accounting_scope != expected_scope:
        raise NormalizedMetricError(
            "normalized_financial_accounting_scope_invalid",
            f"{metric_code} requires {expected_scope}",
        )

    if metric_code == "diluted_shares_outstanding":
        if unit_code != "shares" or currency_code is not None:
            raise NormalizedMetricError(
                "normalized_financial_unit_invalid",
                "diluted shares require shares unit and null currency",
            )
        if period_basis != "instant":
            raise NormalizedMetricError(
                "normalized_financial_period_basis_invalid",
                "diluted shares require instant period basis",
            )
        if observation_state == "supported" and effective_start_date is None:
            raise NormalizedMetricError(
                "normalized_financial_effective_range_required",
                "supported diluted shares require effective_start_date",
            )
    else:
        if unit_code != "currency_amount" or not _valid_currency(currency_code):
            raise NormalizedMetricError(
                "normalized_financial_unit_invalid",
                f"{metric_code} requires currency_amount and explicit currency",
            )

    if metric_code == "net_debt" and period_basis != "instant":
        raise NormalizedMetricError(
            "normalized_financial_period_basis_invalid", "net debt requires instant period basis"
        )

    if metric_code in FLOW_METRICS:
        if period_start_date is None:
            raise NormalizedMetricError(
                "normalized_financial_period_start_required",
                "flow metrics require period_start_date",
            )
        if source_kind == "actual" and period_basis not in {"ttm", "fy_actual"}:
            raise NormalizedMetricError(
                "normalized_financial_period_basis_invalid",
                "actual flow metrics require ttm or fy_actual",
            )
        if source_kind in {"guidance", "consensus", "research_assumption"} and period_basis not in {
            "forward_fy1",
            "forward_fy2",
        }:
            raise NormalizedMetricError(
                "normalized_financial_period_basis_invalid",
                "expected flow metrics require forward_fy1 or forward_fy2",
            )

    if period_basis in {"fy_actual", "forward_fy1", "forward_fy2"} and fiscal_year is None:
        raise NormalizedMetricError(
            "normalized_financial_fiscal_year_required",
            "fiscal-year period basis requires fiscal_year",
        )

    if effective_end_date is not None:
        if effective_start_date is None or effective_end_date < effective_start_date:
            raise NormalizedMetricError(
                "normalized_financial_effective_range_invalid",
                "effective end requires a start and must not precede it",
            )
    if metric_code != "diluted_shares_outstanding" and (
        effective_start_date is not None or effective_end_date is not None
    ):
        raise NormalizedMetricError(
            "normalized_financial_effective_range_forbidden",
            "only diluted shares may own an effective range in v1",
        )


def _bounded_identity(value: str, field: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 128:
        raise NormalizedMetricError(
            "normalized_financial_identity_invalid", f"{field} must be bounded explicit text"
        )


def _require_member(value: str, allowed: frozenset[str], field: str) -> None:
    if value not in allowed:
        raise NormalizedMetricError(
            "normalized_financial_vocabulary_invalid", f"unsupported {field}: {value}"
        )


def _valid_currency(value: str | None) -> bool:
    return isinstance(value, str) and len(value) == 3 and value.isalpha() and value.isupper()

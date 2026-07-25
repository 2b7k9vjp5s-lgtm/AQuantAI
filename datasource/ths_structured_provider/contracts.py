"""Immutable public-contract registry for THS Stage C0.

This module intentionally contains no transport, credential, persistence, or
runtime-configuration path.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .fingerprint import canonical_sha256

SOURCE_KEY = "ths-account-structured-provider-v1"
ADAPTER_FAMILY = "ths_structured_provider"
INDEX_HISTORY_CAPABILITY = "a_share_index_daily_history"


@dataclass(frozen=True, slots=True)
class PublicEndpointContract:
    contract_key: str
    source_key: str
    capability_key: str
    host_key: str
    https_host: str
    http_method: str
    path_template: str
    ordered_query_fields: tuple[str, ...]
    required_query_fields: tuple[str, ...]
    optional_query_fields: tuple[str, ...]
    selector_schema_version: str
    response_schema_version: str
    pagination_contract: str
    ordering_contract: str
    timezone_contract: str
    unit_contract: tuple[tuple[str, str], ...]
    public_limit_contract: tuple[tuple[str, str], ...]
    reviewed_at_date: str
    source_document_key: str

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "contract_key": self.contract_key,
            "source_key": self.source_key,
            "capability_key": self.capability_key,
            "host_key": self.host_key,
            "https_host": self.https_host,
            "http_method": self.http_method,
            "path_template": self.path_template,
            "ordered_query_fields": self.ordered_query_fields,
            "required_query_fields": self.required_query_fields,
            "optional_query_fields": self.optional_query_fields,
            "selector_schema_version": self.selector_schema_version,
            "response_schema_version": self.response_schema_version,
            "pagination_contract": self.pagination_contract,
            "ordering_contract": self.ordering_contract,
            "timezone_contract": self.timezone_contract,
            "unit_contract": self.unit_contract,
            "public_limit_contract": self.public_limit_contract,
            "reviewed_at_date": self.reviewed_at_date,
            "source_document_key": self.source_document_key,
        }

    @property
    def contract_fingerprint(self) -> str:
        return canonical_sha256(self.fingerprint_payload())


INDEX_DAILY_HISTORY_CONTRACT = PublicEndpointContract(
    contract_key="ths.a-share-index.prices.historical.v1",
    source_key=SOURCE_KEY,
    capability_key=INDEX_HISTORY_CAPABILITY,
    host_key="ths-fuyao-official-v1",
    https_host="fuyao.aicubes.cn",
    http_method="GET",
    path_template="/api/a-share-index/prices/historical",
    ordered_query_fields=("thscode", "interval", "start", "end"),
    required_query_fields=("thscode", "interval", "start", "end"),
    optional_query_fields=(),
    selector_schema_version="aquantai.ths-index-history-selector.v1",
    response_schema_version="aquantai.ths-index-history-response.v1",
    pagination_contract="none; offset is unsupported",
    ordering_contract="item.date_ms strictly ascending",
    timezone_contract="millisecond Unix timestamps; source-market interpretation Asia/Shanghai",
    unit_contract=(
        ("price", "numeric; currency/unit not established for live use in the reviewed index contract"),
        ("volume", "numeric; unit not established for live use in the reviewed index contract"),
        ("turnover", "numeric; unit not established for live use in the reviewed index contract"),
    ),
    public_limit_contract=(
        ("thscode_count", "exactly_one"),
        ("interval", "1d"),
        ("maximum_window_years", "10"),
        ("adjust_parameter", "unsupported"),
        ("offset_parameter", "unsupported"),
    ),
    reviewed_at_date="2026-07-24",
    source_document_key="docs/ths_today_market_official_contract_appendix.md#index-historical-prices",
)

_CONTRACTS = {INDEX_DAILY_HISTORY_CONTRACT.capability_key: INDEX_DAILY_HISTORY_CONTRACT}
CONTRACT_REGISTRY: Mapping[str, PublicEndpointContract] = MappingProxyType(_CONTRACTS)


def get_contract(capability_key: str) -> PublicEndpointContract:
    try:
        return CONTRACT_REGISTRY[capability_key]
    except KeyError as exc:
        raise KeyError(f"Unsupported THS Stage C0 capability: {capability_key}") from exc

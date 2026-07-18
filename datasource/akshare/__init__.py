"""AKShare data provider integration."""

from datasource.akshare.provider import (
    ADAPTER_COMPATIBILITY_VERSION,
    ADAPTER_VERSION,
    BENCHMARK_INDEX_ENDPOINT,
    MAX_BENCHMARK_CODES_PER_REQUEST,
    MAX_SECTOR_CODES_PER_REQUEST,
    SECTOR_CLASSIFICATION_SYSTEM,
    SECTOR_HISTORY_ENDPOINT,
    SECTOR_TAXONOMY_ENDPOINT,
    AkshareDataProvider,
    AkshareProviderError,
    AkshareProviderTimeout,
    installed_akshare_version,
    validate_akshare_runtime_version,
)

__all__ = [
    "ADAPTER_COMPATIBILITY_VERSION",
    "ADAPTER_VERSION",
    "BENCHMARK_INDEX_ENDPOINT",
    "MAX_BENCHMARK_CODES_PER_REQUEST",
    "MAX_SECTOR_CODES_PER_REQUEST",
    "SECTOR_CLASSIFICATION_SYSTEM",
    "SECTOR_HISTORY_ENDPOINT",
    "SECTOR_TAXONOMY_ENDPOINT",
    "AkshareDataProvider",
    "AkshareProviderError",
    "AkshareProviderTimeout",
    "installed_akshare_version",
    "validate_akshare_runtime_version",
]

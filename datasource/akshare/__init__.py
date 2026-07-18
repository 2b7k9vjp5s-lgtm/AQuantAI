"""AKShare data provider integration."""

from datasource.akshare.provider import (
    ADAPTER_COMPATIBILITY_VERSION,
    ADAPTER_VERSION,
    AkshareDataProvider,
    AkshareProviderError,
    AkshareProviderTimeout,
    installed_akshare_version,
    validate_akshare_runtime_version,
)

__all__ = [
    "ADAPTER_COMPATIBILITY_VERSION",
    "ADAPTER_VERSION",
    "AkshareDataProvider",
    "AkshareProviderError",
    "AkshareProviderTimeout",
    "installed_akshare_version",
    "validate_akshare_runtime_version",
]

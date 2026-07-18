"""AKShare data provider integration."""

from datasource.akshare.provider import (
    ADAPTER_VERSION,
    AkshareDataProvider,
    AkshareProviderError,
    AkshareProviderTimeout,
)

__all__ = [
    "ADAPTER_VERSION",
    "AkshareDataProvider",
    "AkshareProviderError",
    "AkshareProviderTimeout",
]

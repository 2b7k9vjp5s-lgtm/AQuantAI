"""Runtime-only credential references for THS daily-market transport.

This module never reads environment variables, files, keyrings, databases, or network
resources. Application code must inject one resolver explicitly. Credential values exist
only inside ``ResolvedCredential`` and are excluded from repr, equality, metadata, and
fingerprints.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol, runtime_checkable

from .contracts import SOURCE_KEY
from .fingerprint import canonical_sha256
from .live_contracts import AUTHENTICATION_REFERENCE_TYPE

CREDENTIAL_CONTRACT_VERSION = "aquantai.ths-runtime-credential-reference.v1"


class CredentialFailureCode(str, Enum):
    INVALID_REFERENCE = "THS_CREDENTIAL_INVALID_REFERENCE"
    RESOLVER_UNAVAILABLE = "THS_CREDENTIAL_RESOLVER_UNAVAILABLE"
    CREDENTIAL_MISSING = "THS_CREDENTIAL_MISSING"
    CREDENTIAL_EXPIRED = "THS_CREDENTIAL_EXPIRED"
    CREDENTIAL_INVALID = "THS_CREDENTIAL_INVALID"


class CredentialResolutionError(RuntimeError):
    def __init__(self, message: str, reason_code: CredentialFailureCode) -> None:
        self.reason_code = reason_code
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class CredentialReference:
    """Non-secret locator owned by runtime configuration."""

    reference_id: str
    source_key: str = SOURCE_KEY
    reference_type: str = AUTHENTICATION_REFERENCE_TYPE
    contract_version: str = CREDENTIAL_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.reference_id, str) or not self.reference_id.strip():
            raise CredentialResolutionError(
                "credential reference_id must be a non-empty string",
                CredentialFailureCode.INVALID_REFERENCE,
            )
        normalized = self.reference_id.strip()
        if len(normalized) > 128:
            raise CredentialResolutionError(
                "credential reference_id exceeds 128 characters",
                CredentialFailureCode.INVALID_REFERENCE,
            )
        if any(character.isspace() for character in normalized):
            raise CredentialResolutionError(
                "credential reference_id must not contain whitespace",
                CredentialFailureCode.INVALID_REFERENCE,
            )
        if self.source_key != SOURCE_KEY:
            raise CredentialResolutionError(
                "credential reference source does not match the selected THS source",
                CredentialFailureCode.INVALID_REFERENCE,
            )
        if self.reference_type != AUTHENTICATION_REFERENCE_TYPE:
            raise CredentialResolutionError(
                "credential reference type is outside the reviewed contract",
                CredentialFailureCode.INVALID_REFERENCE,
            )
        if self.contract_version != CREDENTIAL_CONTRACT_VERSION:
            raise CredentialResolutionError(
                "credential reference contract version is not reviewed",
                CredentialFailureCode.INVALID_REFERENCE,
            )
        object.__setattr__(self, "reference_id", normalized)

    def fingerprint_payload(self) -> dict[str, str]:
        return {
            "reference_id": self.reference_id,
            "source_key": self.source_key,
            "reference_type": self.reference_type,
            "contract_version": self.contract_version,
        }

    @property
    def reference_fingerprint(self) -> str:
        return canonical_sha256(self.fingerprint_payload())


class ResolvedCredential:
    """In-memory credential value with deliberately redacted object behavior."""

    __slots__ = ("_credential_value", "_expires_at")

    def __init__(
        self,
        credential_value: str,
        *,
        expires_at: datetime | None = None,
    ) -> None:
        if not isinstance(credential_value, str) or not credential_value:
            raise CredentialResolutionError(
                "credential resolver returned an empty credential",
                CredentialFailureCode.CREDENTIAL_INVALID,
            )
        if expires_at is not None:
            if not isinstance(expires_at, datetime) or expires_at.tzinfo is None:
                raise CredentialResolutionError(
                    "credential expiry must be timezone-aware",
                    CredentialFailureCode.CREDENTIAL_INVALID,
                )
            expires_at = expires_at.astimezone(timezone.utc)
        self._credential_value = credential_value
        self._expires_at = expires_at

    def __repr__(self) -> str:
        return "ResolvedCredential(<redacted>)"

    def __str__(self) -> str:
        return "<redacted>"

    @property
    def expires_at(self) -> datetime | None:
        return self._expires_at

    def safe_metadata(self) -> dict[str, str | None]:
        return {
            "credential_state": "resolved_in_memory",
            "expires_at": self._expires_at.isoformat() if self._expires_at else None,
        }

    def reveal_for_transport(self) -> str:
        """Return the value only to the reviewed transport call boundary."""

        return self._credential_value


@runtime_checkable
class CredentialResolver(Protocol):
    def resolve(self, reference: CredentialReference) -> ResolvedCredential | None:
        """Resolve one runtime reference without logging or persisting its value."""


def resolve_runtime_credential(
    reference: CredentialReference,
    resolver: CredentialResolver,
    *,
    now: datetime,
) -> ResolvedCredential:
    """Resolve and validate one credential using an explicit UTC-aware clock."""

    if not isinstance(reference, CredentialReference):
        raise CredentialResolutionError(
            "credential reference must use CredentialReference",
            CredentialFailureCode.INVALID_REFERENCE,
        )
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise CredentialResolutionError(
            "credential validation clock must be timezone-aware",
            CredentialFailureCode.CREDENTIAL_INVALID,
        )
    if not isinstance(resolver, CredentialResolver):
        raise CredentialResolutionError(
            "credential resolver does not implement the reviewed resolver protocol",
            CredentialFailureCode.RESOLVER_UNAVAILABLE,
        )
    try:
        resolved = resolver.resolve(reference)
    except CredentialResolutionError:
        raise
    except Exception as exc:
        raise CredentialResolutionError(
            "credential resolver failed without exposing provider details",
            CredentialFailureCode.RESOLVER_UNAVAILABLE,
        ) from exc
    if resolved is None:
        raise CredentialResolutionError(
            "credential reference is unavailable",
            CredentialFailureCode.CREDENTIAL_MISSING,
        )
    if not isinstance(resolved, ResolvedCredential):
        raise CredentialResolutionError(
            "credential resolver returned an unsupported value",
            CredentialFailureCode.CREDENTIAL_INVALID,
        )
    current = now.astimezone(timezone.utc)
    if resolved.expires_at is not None and resolved.expires_at <= current:
        raise CredentialResolutionError(
            "credential reference is expired",
            CredentialFailureCode.CREDENTIAL_EXPIRED,
        )
    return resolved

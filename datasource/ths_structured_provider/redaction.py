"""Deterministic redaction for invented Stage C0 diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
import re
from typing import Any
from urllib.parse import parse_qsl, urlsplit

REDACTED = "[REDACTED]"

_SENSITIVE_FRAGMENTS = (
    "xapikey",
    "authorization",
    "apikey",
    "token",
    "cookie",
    "setcookie",
    "accountid",
    "userid",
    "requestid",
    "credentialprofile",
)


def _normalized_label(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def is_sensitive_label(label: str) -> bool:
    normalized = _normalized_label(label)
    return any(fragment in normalized for fragment in _SENSITIVE_FRAGMENTS)


def redact_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, item in value.items():
        key_text = str(key)
        if is_sensitive_label(key_text):
            redacted[key_text] = REDACTED
        elif isinstance(item, Mapping):
            redacted[key_text] = redact_mapping(item)
        elif isinstance(item, list):
            redacted[key_text] = [redact_mapping(v) if isinstance(v, Mapping) else v for v in item]
        elif isinstance(item, tuple):
            redacted[key_text] = tuple(redact_mapping(v) if isinstance(v, Mapping) else v for v in item)
        else:
            redacted[key_text] = item
    return redacted


_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(x-api-key|authorization|api[_-]?key|token|cookie|set-cookie|account[_-]?id|user[_-]?id|request[_-]?id|credential[_-]?profile)\b\s*[:=]\s*([^\s,;]+)"
)


def redact_text(value: str) -> str:
    return _ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}={REDACTED}", value)


def assert_safe_display_url(value: str) -> None:
    parsed = urlsplit(value)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("display URL must not contain user information")
    for key, _ in parse_qsl(parsed.query, keep_blank_values=True):
        if is_sensitive_label(key):
            raise ValueError("display URL contains a sensitive query label")

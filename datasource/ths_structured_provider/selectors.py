"""Closed synthetic selectors for the THS Stage C0 planner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from zoneinfo import ZoneInfo

from .fingerprint import canonical_sha256
from .readiness import BLOCKED_REASON_MESSAGES_ZH, BlockedReasonCode

_SYNTHETIC_THSCODE_RE = re.compile(r"^SYNTH\.IDX\.[A-Z0-9_]{1,32}$")
_SHANGHAI = ZoneInfo("Asia/Shanghai")


class SelectorValidationError(ValueError):
    """Raised with a stable blocked reason when a selector is invalid."""

    def __init__(
        self,
        message: str,
        reason_code: BlockedReasonCode = BlockedReasonCode.SELECTOR_INVALID,
    ) -> None:
        self.reason_code = reason_code
        self.message_zh = BLOCKED_REASON_MESSAGES_ZH[reason_code]
        super().__init__(message)


def _as_datetime(timestamp_ms: int) -> datetime:
    try:
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=_SHANGHAI)
    except (OverflowError, OSError, ValueError) as exc:
        raise SelectorValidationError(
            "timestamp is outside the supported datetime range",
            BlockedReasonCode.SELECTOR_OUT_OF_BOUNDS,
        ) from exc


def _ten_year_anniversary(start: datetime) -> datetime:
    try:
        return start.replace(year=start.year + 10)
    except ValueError:
        # February 29 maps to February 28 in the tenth anniversary year.
        return start.replace(month=2, day=28, year=start.year + 10)


@dataclass(frozen=True, slots=True)
class IndexHistorySelector:
    thscode: str
    start_ms: int
    end_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.thscode, str) or not _SYNTHETIC_THSCODE_RE.fullmatch(self.thscode):
            raise SelectorValidationError("thscode must use the reserved SYNTH.IDX.* namespace")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (self.start_ms, self.end_ms)):
            raise SelectorValidationError("start_ms and end_ms must be integer millisecond timestamps")
        if self.start_ms < 0 or self.end_ms < 0:
            raise SelectorValidationError(
                "timestamps must be non-negative",
                BlockedReasonCode.SELECTOR_OUT_OF_BOUNDS,
            )
        if self.start_ms > self.end_ms:
            raise SelectorValidationError(
                "start_ms must be less than or equal to end_ms",
                BlockedReasonCode.SELECTOR_OUT_OF_BOUNDS,
            )

        start = _as_datetime(self.start_ms)
        end = _as_datetime(self.end_ms)
        if end > _ten_year_anniversary(start):
            raise SelectorValidationError(
                "index-history window exceeds ten calendar years",
                BlockedReasonCode.SELECTOR_OUT_OF_BOUNDS,
            )

    @property
    def synthetic_only(self) -> bool:
        return True

    def ordered_query_items(self) -> tuple[tuple[str, str], ...]:
        return (
            ("thscode", self.thscode),
            ("interval", "1d"),
            ("start", str(self.start_ms)),
            ("end", str(self.end_ms)),
        )

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "schema_version": "aquantai.ths-index-history-selector.v1",
            "thscode": self.thscode,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "synthetic_only": True,
        }

    @property
    def selector_fingerprint(self) -> str:
        return canonical_sha256(self.fingerprint_payload())

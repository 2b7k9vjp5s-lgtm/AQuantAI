"""Provider-neutral application port for deterministic Today Market refresh."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from .contracts import TodayMarketAcquisitionBatch, TodayMarketRefreshPlan


@runtime_checkable
class TodayMarketAcquisitionPort(Protocol):
    def acquire(self, plan: TodayMarketRefreshPlan) -> TodayMarketAcquisitionBatch:
        """Return one complete batch or raise a typed application error."""

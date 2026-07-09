"""Lazy LLM adapter boundary for future research-agent extensions."""

from __future__ import annotations

from typing import Any


class LLMAdapter:
    """Optional adapter that keeps network-backed LLM use out of core reports."""

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            raise RuntimeError("No LLM client is configured; deterministic reports do not require one.")
        return self._client

    def is_available(self) -> bool:
        return self._client is not None

    def summarize_sections(self, sections: list[str]) -> list[str]:
        """Delegate to a mockable client without owning calculations."""
        client = self.client
        return client.summarize_sections(sections)

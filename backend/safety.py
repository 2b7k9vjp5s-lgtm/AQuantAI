"""Shared research-only safety rules."""

from __future__ import annotations

from typing import Any

RESEARCH_DISCLAIMER = (
    "This report is for quantitative research and learning only. It is not investment advice, "
    "not a trading recommendation, and not an instruction to buy, sell, or hold any security."
)

DISALLOWED_ACTIONS = {"trade", "order", "buy", "sell", "hold"}
DISALLOWED_PHRASES = {
    "recommendation to buy",
    "recommendation to sell",
    "guaranteed return",
    "place order",
}


def validate_allowed_actions(actions: list[str]) -> None:
    normalized = {str(action).lower() for action in actions}
    disallowed = normalized.intersection(DISALLOWED_ACTIONS)
    if disallowed:
        raise ValueError(f"Payload exposes disallowed actions: {sorted(disallowed)}")


def validate_research_text(*values: Any) -> None:
    text = " ".join(_flatten_text(values)).lower()
    if any(phrase in text for phrase in DISALLOWED_PHRASES):
        raise ValueError("Payload contains disallowed investment-advice wording")


def _flatten_text(values: Any) -> list[str]:
    flattened: list[str] = []
    for value in values:
        if isinstance(value, dict):
            flattened.extend(_flatten_text(value.values()))
        elif isinstance(value, (list, tuple, set)):
            flattened.extend(_flatten_text(value))
        else:
            flattened.append(str(value))
    return flattened

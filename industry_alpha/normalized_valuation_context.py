"""Typed optional v0.6B context links for the reviewed thirteen-table schema."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from collections.abc import Iterator
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Uuid, event
from sqlalchemy.orm import mapped_column

from industry_alpha.normalized_valuation_models import (
    NormalizedExpectationGapRevision,
    StructuredFinancialObservationRevision,
)

_OBSERVATION_CONTEXT: ContextVar[tuple[UUID | None, UUID | None]] = ContextVar(
    "normalized_observation_context", default=(None, None)
)
_EXPECTATION_CONTEXT: ContextVar[UUID | None] = ContextVar(
    "normalized_expectation_context", default=None
)


def _install_columns() -> None:
    if not hasattr(
        StructuredFinancialObservationRevision, "market_expectation_revision_id"
    ):
        setattr(
            StructuredFinancialObservationRevision,
            "market_expectation_revision_id",
            mapped_column(
                Uuid,
                ForeignKey("stage2_market_expectation_revisions.id", ondelete="RESTRICT"),
                nullable=True,
            ),
        )
        setattr(
            StructuredFinancialObservationRevision,
            "valuation_snapshot_revision_id",
            mapped_column(
                Uuid,
                ForeignKey("stage2_valuation_snapshot_revisions.id", ondelete="RESTRICT"),
                nullable=True,
            ),
        )
        StructuredFinancialObservationRevision.__table__.append_constraint(
            CheckConstraint(
                "(CASE WHEN market_expectation_revision_id IS NOT NULL THEN 1 ELSE 0 END + "
                "CASE WHEN valuation_snapshot_revision_id IS NOT NULL THEN 1 ELSE 0 END) <= 1",
                name="ck_structured_financial_optional_context",
            )
        )
    if not hasattr(NormalizedExpectationGapRevision, "market_expectation_revision_id"):
        setattr(
            NormalizedExpectationGapRevision,
            "market_expectation_revision_id",
            mapped_column(
                Uuid,
                ForeignKey("stage2_market_expectation_revisions.id", ondelete="RESTRICT"),
                nullable=True,
            ),
        )


_install_columns()


@event.listens_for(StructuredFinancialObservationRevision, "init", propagate=True)
def _initialize_observation_context(target, _args, _kwargs) -> None:
    market_expectation_id, valuation_snapshot_id = _OBSERVATION_CONTEXT.get()
    target.market_expectation_revision_id = market_expectation_id
    target.valuation_snapshot_revision_id = valuation_snapshot_id


@event.listens_for(NormalizedExpectationGapRevision, "init", propagate=True)
def _initialize_expectation_context(target, _args, _kwargs) -> None:
    target.market_expectation_revision_id = _EXPECTATION_CONTEXT.get()


@contextmanager
def observation_context(
    market_expectation_revision_id: UUID | None,
    valuation_snapshot_revision_id: UUID | None,
) -> Iterator[None]:
    token = _OBSERVATION_CONTEXT.set(
        (market_expectation_revision_id, valuation_snapshot_revision_id)
    )
    try:
        yield
    finally:
        _OBSERVATION_CONTEXT.reset(token)


@contextmanager
def expectation_context(
    market_expectation_revision_id: UUID | None,
) -> Iterator[None]:
    token = _EXPECTATION_CONTEXT.set(market_expectation_revision_id)
    try:
        yield
    finally:
        _EXPECTATION_CONTEXT.reset(token)


__all__ = ("observation_context", "expectation_context")

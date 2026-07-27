"""Synthetic Today Market demo projection."""

from __future__ import annotations

from .contracts import (
    OVERALL_LIVE_GATE,
    PROJECTION_VERSION,
    CoverageStatus,
    TodayMarketAcquisitionBatch,
    TodayMarketDemoProjection,
    ValidationStatus,
)
from .fingerprint import canonical_sha256


class CandidateValidationError(ValueError):
    pass


def validate_publishable_batch(batch: TodayMarketAcquisitionBatch) -> None:
    if not batch.verify_fingerprint():
        raise CandidateValidationError("batch fingerprint is invalid")
    available_family_orders = (
        batch.coverage.required_families,
        tuple(
            family
            for family in batch.coverage.required_families
            if family not in batch.coverage.missing_families
        ),
    )
    if tuple(result.family_key for result in batch.family_results) not in available_family_orders:
        raise CandidateValidationError(
            "family result ordering or identity is incompatible"
        )
    for result in batch.family_results:
        if result.validation_status is not ValidationStatus.VALID:
            raise CandidateValidationError(
                f"family {result.family_key.value} is invalid"
            )
        if not result.synthetic:
            raise CandidateValidationError("Mock result lost its synthetic marker")
    if batch.coverage.status is not CoverageStatus.COMPLETE:
        raise CandidateValidationError("batch coverage is not complete")
    if batch.coverage.covered_sessions != batch.requested_sessions:
        raise CandidateValidationError("batch sessions are incomplete")
    if batch.coverage.missing_families:
        raise CandidateValidationError("required family coverage is missing")
    for result in batch.family_results:
        if result.covered_sessions != batch.requested_sessions:
            raise CandidateValidationError(
                f"family {result.family_key.value} coverage is incomplete"
            )
    if batch.source_provenance.provider_confirmed:
        raise CandidateValidationError("Mock provenance cannot be Provider-confirmed")


def build_demo_projection(
    batch: TodayMarketAcquisitionBatch,
) -> TodayMarketDemoProjection:
    validate_publishable_batch(batch)
    counts = tuple(
        (result.family_key.value, result.item_count)
        for result in batch.family_results
    )
    payload = {
        "projection_version": PROJECTION_VERSION,
        "is_synthetic": True,
        "source_label": "模拟数据",
        "production_live_source_ready": False,
        "overall_live_gate": OVERALL_LIVE_GATE,
        "message_zh": "模拟更新成功，真实数据源仍未启用",
        "data_through_session": batch.data_through_session,
        "family_item_counts": counts,
        "batch_fingerprint": batch.batch_fingerprint,
    }
    return TodayMarketDemoProjection(
        projection_version=PROJECTION_VERSION,
        is_synthetic=True,
        source_label="模拟数据",
        production_live_source_ready=False,
        overall_live_gate=OVERALL_LIVE_GATE,
        message_zh="模拟更新成功，真实数据源仍未启用",
        data_through_session=batch.data_through_session,
        family_item_counts=counts,
        projection_fingerprint=canonical_sha256(payload),
    )

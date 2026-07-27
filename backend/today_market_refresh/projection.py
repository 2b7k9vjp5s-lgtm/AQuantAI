"""Synthetic Today Market demo projection."""

from __future__ import annotations

from .contracts import (
    OVERALL_LIVE_GATE,
    PROJECTION_VERSION,
    CoverageStatus,
    FailureCategory,
    TodayMarketAcquisitionBatch,
    TodayMarketDemoProjection,
    ValidationStatus,
)
from .fingerprint import canonical_sha256


class CandidateValidationError(ValueError):
    """Closed validation failure with an explicit category and stable code."""

    def __init__(
        self,
        message: str,
        *,
        failure_code: str,
        category: FailureCategory,
    ) -> None:
        self.failure_code = failure_code
        self.category = category
        super().__init__(message)


def _validation_error(
    message: str,
    *,
    failure_code: str,
    category: FailureCategory,
) -> CandidateValidationError:
    return CandidateValidationError(
        message,
        failure_code=failure_code,
        category=category,
    )


def validate_publishable_batch(batch: TodayMarketAcquisitionBatch) -> None:
    if not batch.verify_fingerprint():
        raise _validation_error(
            "batch fingerprint is invalid",
            failure_code="mock_batch_fingerprint_invalid",
            category=FailureCategory.INTERNAL_VALIDATION_FAILED,
        )
    available_family_orders = (
        batch.coverage.required_families,
        tuple(
            family
            for family in batch.coverage.required_families
            if family not in batch.coverage.missing_families
        ),
    )
    if tuple(result.family_key for result in batch.family_results) not in available_family_orders:
        raise _validation_error(
            "family result ordering or identity is incompatible",
            failure_code="mock_family_identity_incompatible",
            category=FailureCategory.INTERNAL_VALIDATION_FAILED,
        )
    for result in batch.family_results:
        if result.validation_status is not ValidationStatus.VALID:
            raise _validation_error(
                f"family {result.family_key.value} is invalid",
                failure_code="mock_family_schema_invalid",
                category=FailureCategory.SCHEMA_MISMATCH,
            )
        if not result.synthetic:
            raise _validation_error(
                "Mock result lost its synthetic marker",
                failure_code="mock_synthetic_marker_missing",
                category=FailureCategory.INTERNAL_VALIDATION_FAILED,
            )
    if batch.coverage.status is not CoverageStatus.COMPLETE:
        raise _validation_error(
            "batch coverage is not complete",
            failure_code="mock_batch_coverage_incomplete",
            category=FailureCategory.COVERAGE_INCOMPLETE,
        )
    if batch.coverage.covered_sessions != batch.requested_sessions:
        raise _validation_error(
            "batch sessions are incomplete",
            failure_code="mock_batch_sessions_incomplete",
            category=FailureCategory.COVERAGE_INCOMPLETE,
        )
    if batch.coverage.missing_families:
        raise _validation_error(
            "required family coverage is missing",
            failure_code="mock_required_family_missing",
            category=FailureCategory.COVERAGE_INCOMPLETE,
        )
    for result in batch.family_results:
        if result.covered_sessions != batch.requested_sessions:
            raise _validation_error(
                f"family {result.family_key.value} coverage is incomplete",
                failure_code="mock_family_coverage_incomplete",
                category=FailureCategory.COVERAGE_INCOMPLETE,
            )
    if batch.source_provenance.provider_confirmed:
        raise _validation_error(
            "Mock provenance cannot be Provider-confirmed",
            failure_code="mock_provider_confirmation_prohibited",
            category=FailureCategory.INTERNAL_VALIDATION_FAILED,
        )


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

"""Fixed-count scalar reads for the Company Research Comparison Matrix."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, NamedTuple
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from backend.database.models import StockBasicRecord
from industry_alpha.beneficiary_semantics_models import (
    Stage1BeneficiarySemanticAssertion,
    Stage1BeneficiarySemanticProfile,
    Stage1BeneficiarySemanticProfileRevision,
)
from industry_alpha.chain_map_models import IndustryMapRevision
from industry_alpha.stage1_models import (
    Stage1Beneficiary,
    Stage1BeneficiaryRevision,
    Stage1CandidatePool,
    Stage1CandidatePoolMembership,
    Stage1CandidatePoolRevision,
)
from industry_alpha.stage2_assessments_models import (
    Stage2CatalystAssessment,
    Stage2CatalystAssessmentRevision,
    Stage2RiskAssessment,
    Stage2RiskAssessmentRevision,
)
from industry_alpha.stage2_expectations_models import (
    Stage2MarketExpectation,
    Stage2MarketExpectationRevision,
    Stage2ValuationSnapshot,
    Stage2ValuationSnapshotRevision,
)
from industry_alpha.stage2_judgments_models import (
    Stage2CompanyJudgment,
    Stage2CompanyJudgmentRevision,
    Stage2IndustryJudgment,
    Stage2IndustryJudgmentRevision,
)
from industry_alpha.stage2_models import (
    Stage2CompanyResearch,
    Stage2CompanyResearchRevision,
    Stage2FinancialHypothesis,
    Stage2FinancialHypothesisRevision,
    Stage2ResearchHypothesisLink,
)

COMPARISON_QUERY_COUNT = 13
TAXONOMY_VERSION = "aquantai.typed-beneficiary-evidence-semantics.v1"


class CompanyComparisonDataError(RuntimeError):
    """The accepted comparison graph cannot be projected without guessing."""


class ModuleSpec(NamedTuple):
    name: str
    identity: Any
    revision: Any
    revision_fk: str
    key_field: str
    research_revision_fk: str | None
    fields: tuple[str, ...]


MODULE_SPECS = (
    ModuleSpec(
        "hypothesis",
        Stage2FinancialHypothesis,
        Stage2FinancialHypothesisRevision,
        "hypothesis_id",
        "hypothesis_key",
        None,
        ("hypothesis_status", "direction", "confidence"),
    ),
    ModuleSpec(
        "expectation",
        Stage2MarketExpectation,
        Stage2MarketExpectationRevision,
        "expectation_id",
        "expectation_key",
        "company_research_revision_id",
        ("subject", "direction", "status", "confidence"),
    ),
    ModuleSpec(
        "valuation",
        Stage2ValuationSnapshot,
        Stage2ValuationSnapshotRevision,
        "valuation_id",
        "valuation_key",
        "company_research_revision_id",
        ("valuation_method", "metric_context", "status", "confidence"),
    ),
    ModuleSpec(
        "catalyst",
        Stage2CatalystAssessment,
        Stage2CatalystAssessmentRevision,
        "catalyst_id",
        "catalyst_key",
        "company_research_revision_id",
        (
            "catalyst_category",
            "subject",
            "expected_observation_window",
            "status",
            "confidence",
        ),
    ),
    ModuleSpec(
        "risk",
        Stage2RiskAssessment,
        Stage2RiskAssessmentRevision,
        "risk_id",
        "risk_key",
        "company_research_revision_id",
        (
            "risk_category",
            "subject",
            "thesis_invalidation_condition",
            "status",
            "confidence",
        ),
    ),
    ModuleSpec(
        "industry_judgment",
        Stage2IndustryJudgment,
        Stage2IndustryJudgmentRevision,
        "judgment_id",
        "judgment_key",
        "company_research_revision_id",
        ("outcome", "evidence_state", "confidence"),
    ),
    ModuleSpec(
        "company_judgment",
        Stage2CompanyJudgment,
        Stage2CompanyJudgmentRevision,
        "judgment_id",
        "judgment_key",
        "company_research_revision_id",
        ("outcome", "evidence_state", "confidence"),
    ),
)


@dataclass(frozen=True)
class ComparisonReadSet:
    memberships: tuple[dict[str, Any], ...]
    research_roots: tuple[dict[str, Any], ...]
    research_revisions: tuple[dict[str, Any], ...]
    semantic_revisions: tuple[dict[str, Any], ...]
    semantic_assertions: tuple[dict[str, Any], ...]
    modules: dict[str, tuple[dict[str, Any], ...]]
    query_count: int


class CompanyComparisonRepository:
    """Read one exact frozen pool using a count independent of member growth."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def load_header(self, candidate_pool_revision_id: UUID) -> dict[str, Any] | None:
        rows = self._rows(
            select(
                Stage1CandidatePoolRevision.id.label("candidate_pool_revision_id"),
                Stage1CandidatePoolRevision.candidate_pool_id.label("candidate_pool_id"),
                Stage1CandidatePoolRevision.revision_no.label("candidate_pool_revision_no"),
                Stage1CandidatePoolRevision.selected_map_revision_id.label(
                    "selected_map_revision_id"
                ),
                Stage1CandidatePoolRevision.title.label("candidate_pool_title"),
                Stage1CandidatePoolRevision.scope.label("candidate_pool_scope"),
                Stage1CandidatePoolRevision.information_cutoff_date.label(
                    "candidate_pool_information_cutoff_date"
                ),
                Stage1CandidatePoolRevision.recorded_at_utc.label(
                    "candidate_pool_recorded_at_utc"
                ),
                Stage1CandidatePoolRevision.supersedes_revision_id.label(
                    "candidate_pool_supersedes_revision_id"
                ),
                Stage1CandidatePool.case_id.label("case_id"),
                Stage1CandidatePool.map_id.label("map_id"),
                Stage1CandidatePool.pool_key.label("candidate_pool_key"),
                Stage1CandidatePool.created_at_utc.label(
                    "candidate_pool_created_at_utc"
                ),
                IndustryMapRevision.map_id.label("map_revision_map_id"),
                IndustryMapRevision.revision_no.label("map_revision_no"),
                IndustryMapRevision.title.label("map_revision_title"),
                IndustryMapRevision.scope.label("map_revision_scope"),
                IndustryMapRevision.information_cutoff_date.label(
                    "map_information_cutoff_date"
                ),
                IndustryMapRevision.recorded_at_utc.label("map_recorded_at_utc"),
            )
            .select_from(Stage1CandidatePoolRevision)
            .outerjoin(
                Stage1CandidatePool,
                Stage1CandidatePool.id
                == Stage1CandidatePoolRevision.candidate_pool_id,
            )
            .outerjoin(
                IndustryMapRevision,
                IndustryMapRevision.id
                == Stage1CandidatePoolRevision.selected_map_revision_id,
            )
            .where(Stage1CandidatePoolRevision.id == candidate_pool_revision_id)
        )
        if len(rows) > 1:
            raise CompanyComparisonDataError(
                f"duplicate candidate-pool revision {candidate_pool_revision_id}"
            )
        return None if not rows else rows[0]

    def load_components(
        self,
        candidate_pool_revision_id: UUID,
        *,
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ) -> ComparisonReadSet:
        memberships = self._rows(self._membership_statement(candidate_pool_revision_id))
        research_roots = self._rows(
            self._research_root_statement(
                candidate_pool_revision_id, as_of_recorded_at_utc
            )
        )
        research_ids = tuple(
            row["company_research_id"] for row in research_roots
        )
        research_revisions = self._rows(
            self._research_revision_statement(
                research_ids, as_of_cutoff, as_of_recorded_at_utc
            )
        )
        beneficiary_ids = tuple(row["beneficiary_id"] for row in memberships)
        semantic_revisions = self._rows(
            self._semantic_revision_statement(
                beneficiary_ids, as_of_cutoff, as_of_recorded_at_utc
            )
        )
        semantic_revision_ids = tuple(
            row["profile_revision_id"] for row in semantic_revisions
        )
        semantic_assertions = self._rows(
            self._semantic_assertion_statement(semantic_revision_ids)
        )
        modules = {
            spec.name: self._rows(
                self._module_statement(
                    spec,
                    research_ids,
                    as_of_cutoff,
                    as_of_recorded_at_utc,
                )
            )
            for spec in MODULE_SPECS
        }
        return ComparisonReadSet(
            memberships=memberships,
            research_roots=research_roots,
            research_revisions=research_revisions,
            semantic_revisions=semantic_revisions,
            semantic_assertions=semantic_assertions,
            modules=modules,
            query_count=COMPARISON_QUERY_COUNT,
        )

    @staticmethod
    def _membership_statement(candidate_pool_revision_id: UUID):
        return (
            select(
                Stage1CandidatePoolMembership.id.label(
                    "candidate_pool_membership_id"
                ),
                Stage1CandidatePoolMembership.candidate_pool_revision_id.label(
                    "candidate_pool_revision_id"
                ),
                Stage1CandidatePoolMembership.beneficiary_id.label("beneficiary_id"),
                Stage1CandidatePoolMembership.beneficiary_revision_id.label(
                    "beneficiary_revision_id"
                ),
                Stage1CandidatePoolMembership.recorded_at_utc.label(
                    "membership_recorded_at_utc"
                ),
                Stage1Beneficiary.case_id.label("beneficiary_case_id"),
                Stage1Beneficiary.map_id.label("beneficiary_map_id"),
                Stage1Beneficiary.source.label("source"),
                Stage1Beneficiary.stock_code.label("stock_code"),
                Stage1Beneficiary.created_at_utc.label("beneficiary_created_at_utc"),
                Stage1BeneficiaryRevision.revision_no.label(
                    "beneficiary_revision_no"
                ),
                Stage1BeneficiaryRevision.selected_map_revision_id.label(
                    "beneficiary_selected_map_revision_id"
                ),
                Stage1BeneficiaryRevision.stock_basic_record_id.label(
                    "stock_basic_record_id"
                ),
                Stage1BeneficiaryRevision.beneficiary_kind.label(
                    "beneficiary_kind"
                ),
                Stage1BeneficiaryRevision.assessment_status.label(
                    "beneficiary_assessment_status"
                ),
                Stage1BeneficiaryRevision.rationale_summary.label(
                    "beneficiary_rationale_summary"
                ),
                Stage1BeneficiaryRevision.information_cutoff_date.label(
                    "beneficiary_information_cutoff_date"
                ),
                Stage1BeneficiaryRevision.recorded_at_utc.label(
                    "beneficiary_recorded_at_utc"
                ),
                StockBasicRecord.stock_name.label("stock_name"),
                StockBasicRecord.exchange.label("exchange"),
                StockBasicRecord.source.label("stock_record_source"),
                StockBasicRecord.stock_code.label("stock_record_code"),
            )
            .select_from(Stage1CandidatePoolMembership)
            .outerjoin(
                Stage1Beneficiary,
                Stage1Beneficiary.id
                == Stage1CandidatePoolMembership.beneficiary_id,
            )
            .outerjoin(
                Stage1BeneficiaryRevision,
                and_(
                    Stage1BeneficiaryRevision.id
                    == Stage1CandidatePoolMembership.beneficiary_revision_id,
                    Stage1BeneficiaryRevision.beneficiary_id
                    == Stage1CandidatePoolMembership.beneficiary_id,
                ),
            )
            .outerjoin(
                StockBasicRecord,
                StockBasicRecord.id
                == Stage1BeneficiaryRevision.stock_basic_record_id,
            )
            .where(
                Stage1CandidatePoolMembership.candidate_pool_revision_id
                == candidate_pool_revision_id
            )
            .order_by(
                Stage1Beneficiary.source,
                Stage1Beneficiary.stock_code,
                Stage1CandidatePoolMembership.beneficiary_id,
            )
        )

    @staticmethod
    def _research_root_statement(
        candidate_pool_revision_id: UUID, as_of_recorded_at_utc: datetime
    ):
        return (
            select(
                Stage2CompanyResearch.id.label("company_research_id"),
                Stage2CompanyResearch.case_id.label("case_id"),
                Stage2CompanyResearch.map_id.label("map_id"),
                Stage2CompanyResearch.candidate_pool_id.label("candidate_pool_id"),
                Stage2CompanyResearch.candidate_pool_revision_id.label(
                    "candidate_pool_revision_id"
                ),
                Stage2CompanyResearch.candidate_pool_membership_id.label(
                    "candidate_pool_membership_id"
                ),
                Stage2CompanyResearch.beneficiary_id.label("beneficiary_id"),
                Stage2CompanyResearch.beneficiary_revision_id.label(
                    "beneficiary_revision_id"
                ),
                Stage2CompanyResearch.selected_map_revision_id.label(
                    "selected_map_revision_id"
                ),
                Stage2CompanyResearch.stock_basic_record_id.label(
                    "stock_basic_record_id"
                ),
                Stage2CompanyResearch.source.label("source"),
                Stage2CompanyResearch.stock_code.label("stock_code"),
                Stage2CompanyResearch.created_at_utc.label("created_at_utc"),
            )
            .where(
                Stage2CompanyResearch.candidate_pool_revision_id
                == candidate_pool_revision_id,
                Stage2CompanyResearch.created_at_utc <= as_of_recorded_at_utc,
            )
            .order_by(
                Stage2CompanyResearch.candidate_pool_membership_id,
                Stage2CompanyResearch.id,
            )
        )

    @staticmethod
    def _research_revision_statement(
        research_ids: tuple[UUID, ...],
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ):
        return (
            select(
                Stage2CompanyResearchRevision.company_research_id.label(
                    "company_research_id"
                ),
                Stage2CompanyResearchRevision.id.label("revision_id"),
                Stage2CompanyResearchRevision.revision_no.label("revision_no"),
                Stage2CompanyResearchRevision.workflow_state.label("workflow_state"),
                Stage2CompanyResearchRevision.conclusion_status.label(
                    "conclusion_status"
                ),
                Stage2CompanyResearchRevision.information_cutoff_date.label(
                    "information_cutoff_date"
                ),
                Stage2CompanyResearchRevision.recorded_at_utc.label(
                    "recorded_at_utc"
                ),
                Stage2CompanyResearchRevision.supersedes_revision_id.label(
                    "supersedes_revision_id"
                ),
            )
            .where(
                Stage2CompanyResearchRevision.company_research_id.in_(research_ids),
                Stage2CompanyResearchRevision.information_cutoff_date <= as_of_cutoff,
                Stage2CompanyResearchRevision.recorded_at_utc
                <= as_of_recorded_at_utc,
            )
            .order_by(
                Stage2CompanyResearchRevision.company_research_id,
                Stage2CompanyResearchRevision.revision_no,
                Stage2CompanyResearchRevision.id,
            )
        )

    @staticmethod
    def _semantic_revision_statement(
        beneficiary_ids: tuple[UUID, ...],
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ):
        return (
            select(
                Stage1BeneficiarySemanticProfile.id.label("profile_id"),
                Stage1BeneficiarySemanticProfile.beneficiary_id.label(
                    "beneficiary_id"
                ),
                Stage1BeneficiarySemanticProfile.created_at_utc.label(
                    "profile_created_at_utc"
                ),
                Stage1BeneficiarySemanticProfileRevision.id.label(
                    "profile_revision_id"
                ),
                Stage1BeneficiarySemanticProfileRevision.revision_no.label(
                    "revision_no"
                ),
                Stage1BeneficiarySemanticProfileRevision.beneficiary_revision_id.label(
                    "beneficiary_revision_id"
                ),
                Stage1BeneficiarySemanticProfileRevision.selected_map_revision_id.label(
                    "selected_map_revision_id"
                ),
                Stage1BeneficiarySemanticProfileRevision.taxonomy_version.label(
                    "taxonomy_version"
                ),
                Stage1BeneficiarySemanticProfileRevision.overall_status.label(
                    "overall_status"
                ),
                Stage1BeneficiarySemanticProfileRevision.information_cutoff_date.label(
                    "information_cutoff_date"
                ),
                Stage1BeneficiarySemanticProfileRevision.recorded_at_utc.label(
                    "recorded_at_utc"
                ),
                Stage1BeneficiarySemanticProfileRevision.supersedes_revision_id.label(
                    "supersedes_revision_id"
                ),
            )
            .select_from(Stage1BeneficiarySemanticProfile)
            .join(
                Stage1BeneficiarySemanticProfileRevision,
                Stage1BeneficiarySemanticProfileRevision.profile_id
                == Stage1BeneficiarySemanticProfile.id,
            )
            .where(
                Stage1BeneficiarySemanticProfile.beneficiary_id.in_(beneficiary_ids),
                Stage1BeneficiarySemanticProfile.created_at_utc
                <= as_of_recorded_at_utc,
                Stage1BeneficiarySemanticProfileRevision.information_cutoff_date
                <= as_of_cutoff,
                Stage1BeneficiarySemanticProfileRevision.recorded_at_utc
                <= as_of_recorded_at_utc,
            )
            .order_by(
                Stage1BeneficiarySemanticProfile.beneficiary_id,
                Stage1BeneficiarySemanticProfileRevision.revision_no,
                Stage1BeneficiarySemanticProfileRevision.id,
            )
        )

    @staticmethod
    def _semantic_assertion_statement(
        profile_revision_ids: tuple[UUID, ...],
    ):
        return (
            select(
                Stage1BeneficiarySemanticAssertion.id.label("assertion_id"),
                Stage1BeneficiarySemanticAssertion.profile_revision_id.label(
                    "profile_revision_id"
                ),
                Stage1BeneficiarySemanticAssertion.assertion_key.label(
                    "assertion_key"
                ),
                Stage1BeneficiarySemanticAssertion.field_kind.label("field_kind"),
                Stage1BeneficiarySemanticAssertion.state_code.label("state_code"),
                Stage1BeneficiarySemanticAssertion.evidence_state.label(
                    "evidence_state"
                ),
                Stage1BeneficiarySemanticAssertion.subject_text.label("subject_text"),
                Stage1BeneficiarySemanticAssertion.map_observation_revision_id.label(
                    "map_observation_revision_id"
                ),
                Stage1BeneficiarySemanticAssertion.position.label("position"),
            )
            .where(
                Stage1BeneficiarySemanticAssertion.profile_revision_id.in_(
                    profile_revision_ids
                )
            )
            .order_by(
                Stage1BeneficiarySemanticAssertion.profile_revision_id,
                Stage1BeneficiarySemanticAssertion.field_kind,
                Stage1BeneficiarySemanticAssertion.position,
                Stage1BeneficiarySemanticAssertion.assertion_key,
            )
        )

    @staticmethod
    def _module_statement(
        spec: ModuleSpec,
        research_ids: tuple[UUID, ...],
        as_of_cutoff: date,
        as_of_recorded_at_utc: datetime,
    ):
        identity = spec.identity
        revision = spec.revision
        research_revision = Stage2CompanyResearchRevision
        columns = [
            identity.company_research_id.label("company_research_id"),
            identity.id.label("item_id"),
            getattr(identity, spec.key_field).label("item_key"),
            identity.created_at_utc.label("created_at_utc"),
            revision.id.label("revision_id"),
            revision.revision_no.label("revision_no"),
            revision.information_cutoff_date.label("information_cutoff_date"),
            revision.recorded_at_utc.label("recorded_at_utc"),
            revision.supersedes_revision_id.label("supersedes_revision_id"),
        ]
        columns.extend(getattr(revision, field).label(field) for field in spec.fields)
        statement = (
            select(*columns)
            .select_from(identity)
            .join(revision, getattr(revision, spec.revision_fk) == identity.id)
        )
        if spec.name == "hypothesis":
            statement = statement.join(
                Stage2ResearchHypothesisLink,
                Stage2ResearchHypothesisLink.hypothesis_revision_id == revision.id,
            ).join(
                research_revision,
                research_revision.id
                == Stage2ResearchHypothesisLink.company_research_revision_id,
            )
            statement = statement.add_columns(
                Stage2ResearchHypothesisLink.company_research_revision_id.label(
                    "company_research_revision_id"
                )
            )
        else:
            frozen_field = getattr(revision, spec.research_revision_fk)
            statement = statement.join(
                research_revision,
                research_revision.id == frozen_field,
            ).add_columns(
                frozen_field.label("company_research_revision_id")
            )
        return (
            statement.where(
                identity.company_research_id.in_(research_ids),
                identity.created_at_utc <= as_of_recorded_at_utc,
                revision.information_cutoff_date <= as_of_cutoff,
                revision.recorded_at_utc <= as_of_recorded_at_utc,
                research_revision.company_research_id
                == identity.company_research_id,
                research_revision.information_cutoff_date <= as_of_cutoff,
                research_revision.recorded_at_utc <= as_of_recorded_at_utc,
            )
            .order_by(
                identity.company_research_id,
                getattr(identity, spec.key_field),
                identity.id,
                revision.revision_no,
                revision.id,
            )
        )

    def _rows(self, statement: Any) -> tuple[dict[str, Any], ...]:
        return tuple(dict(row) for row in self._session.execute(statement).mappings())

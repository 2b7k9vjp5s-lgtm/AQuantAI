"""Fixed-count scalar reads for the Company Research Workspace."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Iterable, NamedTuple
from uuid import UUID
from sqlalchemy import Date, DateTime, Uuid, and_, cast, func, literal, select, union_all
from sqlalchemy.orm import Session
from backend.database.models import DailyPriceRecord, IngestionRun, StockBasicRecord
from industry_alpha.chain_map_models import IndustryMapNodeRevision, IndustryMapObservationRevision, IndustryMapRelationshipRevision, IndustryMapRevision
from industry_alpha.models import Claim, ClaimEvidenceLink, ClaimRevision, EvidenceItem
from industry_alpha.stage1_models import Stage1Beneficiary, Stage1BeneficiaryAssertionLink, Stage1BeneficiaryClaimLink, Stage1BeneficiaryRevision, Stage1CandidatePool, Stage1CandidatePoolMembership, Stage1CandidatePoolRevision
from industry_alpha.stage2_assessments_models import Stage2CatalystAssessment, Stage2CatalystAssessmentRevision, Stage2CatalystClaimLink, Stage2CatalystEvidenceLink, Stage2CatalystExpectationLink, Stage2CatalystHypothesisLink, Stage2CatalystValuationLink, Stage2RiskAssessment, Stage2RiskAssessmentRevision, Stage2RiskClaimLink, Stage2RiskEvidenceLink, Stage2RiskExpectationLink, Stage2RiskHypothesisLink, Stage2RiskValuationLink
from industry_alpha.stage2_expectations_models import Stage2ExpectationClaimLink, Stage2ExpectationEvidenceLink, Stage2ExpectationHypothesisLink, Stage2MarketExpectation, Stage2MarketExpectationRevision, Stage2ValuationClaimLink, Stage2ValuationEvidenceLink, Stage2ValuationHypothesisLink, Stage2ValuationSnapshot, Stage2ValuationSnapshotRevision
from industry_alpha.stage2_judgments_models import Stage2CompanyJudgment, Stage2CompanyJudgmentCatalystLink, Stage2CompanyJudgmentClaimLink, Stage2CompanyJudgmentEvidenceLink, Stage2CompanyJudgmentExpectationLink, Stage2CompanyJudgmentHypothesisLink, Stage2CompanyJudgmentRevision, Stage2CompanyJudgmentRiskLink, Stage2CompanyJudgmentValuationLink, Stage2IndustryJudgment, Stage2IndustryJudgmentCatalystLink, Stage2IndustryJudgmentClaimLink, Stage2IndustryJudgmentEvidenceLink, Stage2IndustryJudgmentExpectationLink, Stage2IndustryJudgmentHypothesisLink, Stage2IndustryJudgmentRevision, Stage2IndustryJudgmentRiskLink, Stage2IndustryJudgmentValuationLink
from industry_alpha.stage2_models import Stage2CompanyResearch, Stage2CompanyResearchRevision, Stage2FinancialHypothesis, Stage2FinancialHypothesisRevision, Stage2HandoffAssertionLink, Stage2HandoffClaimLink, Stage2HandoffEvidenceLink, Stage2HypothesisClaimLink, Stage2HypothesisEvidenceLink, Stage2ResearchHypothesisLink, Stage2VerificationItem
SELECTOR_QUERY_COUNT = 3
WORKSPACE_QUERY_COUNT = 14

class CompanyResearchWorkspaceDataError(RuntimeError):
    """The accepted workspace graph cannot be projected without guessing."""

@dataclass(frozen=True)
class WorkspaceReadSet:
    root: dict[str, Any] | None
    research_revisions: tuple[dict[str, Any], ...]
    verification_items: tuple[dict[str, Any], ...]
    hypotheses: tuple[dict[str, Any], ...]
    expectations: tuple[dict[str, Any], ...]
    valuations: tuple[dict[str, Any], ...]
    catalysts: tuple[dict[str, Any], ...]
    risks: tuple[dict[str, Any], ...]
    industry_judgments: tuple[dict[str, Any], ...]
    company_judgments: tuple[dict[str, Any], ...]
    frozen_links: tuple[dict[str, Any], ...]
    claim_links: tuple[dict[str, Any], ...]
    evidence_links: tuple[dict[str, Any], ...]
    handoff_links: tuple[dict[str, Any], ...]
    query_count: int

class ModuleSpec(NamedTuple):
    name: str
    identity: Any
    revision: Any
    revision_fk: str
    key_field: str
    research_revision_fk: str | None
    fields: tuple[str, ...]
MODULE_SPECS = (ModuleSpec('hypothesis', Stage2FinancialHypothesis, Stage2FinancialHypothesisRevision, 'hypothesis_id', 'hypothesis_key', None, ('hypothesis_status', 'mechanism', 'direction', 'operating_metric', 'financial_statement_line', 'expected_lag_horizon', 'confidence', 'basis')), ModuleSpec('expectation', Stage2MarketExpectation, Stage2MarketExpectationRevision, 'expectation_id', 'expectation_key', 'company_research_revision_id', ('subject', 'period_horizon', 'expectation_kind', 'direction', 'status', 'confidence', 'basis')), ModuleSpec('valuation', Stage2ValuationSnapshot, Stage2ValuationSnapshotRevision, 'valuation_id', 'valuation_key', 'company_research_revision_id', ('valuation_method', 'metric_context', 'observed_value', 'missing_data_reason', 'unit', 'currency', 'comparison_basis', 'assumptions', 'status', 'confidence', 'daily_price_id')), ModuleSpec('catalyst', Stage2CatalystAssessment, Stage2CatalystAssessmentRevision, 'catalyst_id', 'catalyst_key', 'company_research_revision_id', ('catalyst_category', 'subject', 'expected_observation_window', 'status', 'confidence', 'trigger_observation_criteria', 'basis', 'uncertainty')), ModuleSpec('risk', Stage2RiskAssessment, Stage2RiskAssessmentRevision, 'risk_id', 'risk_key', 'company_research_revision_id', ('risk_category', 'subject', 'downside_path', 'thesis_invalidation_condition', 'mitigants', 'status', 'confidence', 'basis', 'uncertainty')), ModuleSpec('industry_judgment', Stage2IndustryJudgment, Stage2IndustryJudgmentRevision, 'judgment_id', 'judgment_key', 'company_research_revision_id', ('outcome', 'evidence_state', 'confidence', 'decision_criteria', 'rationale', 'uncertainty', 'follow_up_verification', 'driver_durability', 'value_pool_direction', 'chain_bottleneck_support')), ModuleSpec('company_judgment', Stage2CompanyJudgment, Stage2CompanyJudgmentRevision, 'judgment_id', 'judgment_key', 'company_research_revision_id', ('outcome', 'evidence_state', 'confidence', 'decision_criteria', 'rationale', 'uncertainty', 'follow_up_verification', 'beneficiary_credibility', 'financial_transmission_credibility', 'execution_risks')))

class CompanyResearchWorkspaceRepository:

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_selector_roots(self, *, as_of_cutoff: date | None=None) -> tuple[dict[str, Any], ...]:
        statement = self._root_statement().where(*_recorded_visibility(Stage2CompanyResearch.created_at_utc, as_of_cutoff))
        return self._rows(statement)

    def list_research_revisions(self, research_ids: Iterable[UUID], *, as_of_cutoff: date | None=None) -> tuple[dict[str, Any], ...]:
        return self._rows(self._research_statement(tuple(research_ids), as_of_cutoff))

    def list_availability(self, research_ids: Iterable[UUID], *, as_of_cutoff: date | None=None) -> tuple[dict[str, Any], ...]:
        ids = tuple(research_ids)
        branches = []
        for spec in MODULE_SPECS:
            identity, revision = (spec.identity, spec.revision)
            statement = select(identity.company_research_id.label('company_research_id'), literal(spec.name).label('module'), func.count(func.distinct(identity.id)).label('visible_count')).join(revision, getattr(revision, spec.revision_fk) == identity.id)
            if spec.name == 'hypothesis':
                statement = statement.join(Stage2ResearchHypothesisLink, Stage2ResearchHypothesisLink.hypothesis_revision_id == revision.id).join(Stage2CompanyResearchRevision, Stage2CompanyResearchRevision.id == Stage2ResearchHypothesisLink.company_research_revision_id)
            else:
                statement = statement.join(Stage2CompanyResearchRevision, Stage2CompanyResearchRevision.id == getattr(revision, spec.research_revision_fk))
            branches.append(statement.where(identity.company_research_id.in_(ids), Stage2CompanyResearchRevision.company_research_id == identity.company_research_id, *_recorded_visibility(identity.created_at_utc, as_of_cutoff), *_dated_visibility(revision.information_cutoff_date, revision.recorded_at_utc, as_of_cutoff), *_dated_visibility(Stage2CompanyResearchRevision.information_cutoff_date, Stage2CompanyResearchRevision.recorded_at_utc, as_of_cutoff)).group_by(identity.company_research_id))
        return self._rows(union_all(*branches).order_by('company_research_id', 'module'))

    def load_workspace(self, research_id: UUID) -> WorkspaceReadSet:
        roots = self._rows(self._root_statement().where(Stage2CompanyResearch.id == research_id))
        if len(roots) > 1:
            raise CompanyResearchWorkspaceDataError(f'duplicate exact company research root {research_id}')
        if not roots:
            return WorkspaceReadSet(None, (), (), (), (), (), (), (), (), (), (), (), (), (), 1)
        research = self._rows(self._research_statement((research_id,), None))
        verification = self._rows(self._verification_statement({row['revision_id'] for row in research}))
        modules = {spec.name: self._rows(self._module_statement(spec, research_id)) for spec in MODULE_SPECS}
        revision_sets = {'research': {row['revision_id'] for row in research}}
        revision_sets.update({name: {row['revision_id'] for row in rows} for name, rows in modules.items()})
        frozen = self._rows(_frozen_statement(revision_sets))
        claims = self._rows(_claim_statement(revision_sets))
        evidence = self._rows(_evidence_statement(revision_sets))
        handoff = self._rows(_handoff_statement(research_id))
        return WorkspaceReadSet(roots[0], research, verification, modules['hypothesis'], modules['expectation'], modules['valuation'], modules['catalyst'], modules['risk'], modules['industry_judgment'], modules['company_judgment'], frozen, claims, evidence, handoff, WORKSPACE_QUERY_COUNT)

    @staticmethod
    def _root_statement():
        return select(Stage2CompanyResearch.id.label('company_research_id'), Stage2CompanyResearch.case_id.label('case_id'), Stage2CompanyResearch.map_id.label('map_id'), Stage2CompanyResearch.source.label('source'), Stage2CompanyResearch.stock_code.label('stock_code'), Stage2CompanyResearch.created_at_utc.label('created_at_utc'), Stage1CandidatePool.id.label('candidate_pool_id'), Stage1CandidatePool.pool_key.label('candidate_pool_key'), Stage1CandidatePool.created_at_utc.label('candidate_pool_created_at_utc'), Stage1CandidatePoolRevision.id.label('candidate_pool_revision_id'), Stage1CandidatePoolRevision.revision_no.label('candidate_pool_revision_no'), Stage1CandidatePoolRevision.selected_map_revision_id.label('pool_selected_map_revision_id'), Stage1CandidatePoolRevision.title.label('candidate_pool_title'), Stage1CandidatePoolRevision.scope.label('candidate_pool_scope'), Stage1CandidatePoolRevision.information_cutoff_date.label('candidate_pool_information_cutoff_date'), Stage1CandidatePoolRevision.recorded_at_utc.label('candidate_pool_recorded_at_utc'), Stage1CandidatePoolRevision.supersedes_revision_id.label('candidate_pool_supersedes_revision_id'), Stage1CandidatePoolMembership.id.label('candidate_pool_membership_id'), Stage1CandidatePoolMembership.recorded_at_utc.label('membership_recorded_at_utc'), Stage1Beneficiary.id.label('beneficiary_id'), Stage1Beneficiary.case_id.label('beneficiary_case_id'), Stage1Beneficiary.map_id.label('beneficiary_map_id'), Stage1Beneficiary.source.label('beneficiary_source'), Stage1Beneficiary.stock_code.label('beneficiary_stock_code'), Stage1Beneficiary.created_at_utc.label('beneficiary_created_at_utc'), Stage1BeneficiaryRevision.id.label('beneficiary_revision_id'), Stage1BeneficiaryRevision.revision_no.label('beneficiary_revision_no'), Stage1BeneficiaryRevision.selected_map_revision_id.label('beneficiary_selected_map_revision_id'), Stage1BeneficiaryRevision.stock_basic_record_id.label('beneficiary_stock_basic_record_id'), Stage1BeneficiaryRevision.beneficiary_kind.label('beneficiary_kind'), Stage1BeneficiaryRevision.assessment_status.label('beneficiary_assessment_status'), Stage1BeneficiaryRevision.rationale_summary.label('beneficiary_rationale_summary'), Stage1BeneficiaryRevision.information_cutoff_date.label('beneficiary_information_cutoff_date'), Stage1BeneficiaryRevision.recorded_at_utc.label('beneficiary_recorded_at_utc'), Stage1BeneficiaryRevision.supersedes_revision_id.label('beneficiary_supersedes_revision_id'), IndustryMapRevision.id.label('selected_map_revision_id'), IndustryMapRevision.map_id.label('map_revision_map_id'), IndustryMapRevision.revision_no.label('map_revision_no'), IndustryMapRevision.title.label('map_revision_title'), IndustryMapRevision.scope.label('map_revision_scope'), IndustryMapRevision.information_cutoff_date.label('map_information_cutoff_date'), IndustryMapRevision.recorded_at_utc.label('map_recorded_at_utc'), IndustryMapRevision.supersedes_revision_id.label('map_supersedes_revision_id'), StockBasicRecord.id.label('stock_basic_record_id'), StockBasicRecord.stock_code.label('stock_record_code'), StockBasicRecord.stock_name.label('stock_name'), StockBasicRecord.exchange.label('exchange'), StockBasicRecord.industry.label('provider_industry'), StockBasicRecord.listing_date.label('listing_date'), StockBasicRecord.status.label('stock_status'), StockBasicRecord.source.label('stock_record_source'), IngestionRun.id.label('ingestion_run_id'), IngestionRun.series_key.label('ingestion_series_key'), IngestionRun.provider.label('ingestion_provider'), IngestionRun.dataset.label('ingestion_dataset'), IngestionRun.information_cutoff_date.label('ingestion_information_cutoff_date'), IngestionRun.completed_at.label('ingestion_completed_at_utc'), IngestionRun.status.label('ingestion_status')).outerjoin(Stage1CandidatePool, and_(Stage1CandidatePool.id == Stage2CompanyResearch.candidate_pool_id, Stage1CandidatePool.case_id == Stage2CompanyResearch.case_id, Stage1CandidatePool.map_id == Stage2CompanyResearch.map_id)).outerjoin(Stage1CandidatePoolRevision, and_(Stage1CandidatePoolRevision.id == Stage2CompanyResearch.candidate_pool_revision_id, Stage1CandidatePoolRevision.candidate_pool_id == Stage2CompanyResearch.candidate_pool_id, Stage1CandidatePoolRevision.selected_map_revision_id == Stage2CompanyResearch.selected_map_revision_id)).outerjoin(Stage1CandidatePoolMembership, and_(Stage1CandidatePoolMembership.id == Stage2CompanyResearch.candidate_pool_membership_id, Stage1CandidatePoolMembership.candidate_pool_revision_id == Stage2CompanyResearch.candidate_pool_revision_id, Stage1CandidatePoolMembership.beneficiary_id == Stage2CompanyResearch.beneficiary_id, Stage1CandidatePoolMembership.beneficiary_revision_id == Stage2CompanyResearch.beneficiary_revision_id)).outerjoin(Stage1Beneficiary, and_(Stage1Beneficiary.id == Stage2CompanyResearch.beneficiary_id, Stage1Beneficiary.case_id == Stage2CompanyResearch.case_id, Stage1Beneficiary.map_id == Stage2CompanyResearch.map_id, Stage1Beneficiary.source == Stage2CompanyResearch.source, Stage1Beneficiary.stock_code == Stage2CompanyResearch.stock_code)).outerjoin(Stage1BeneficiaryRevision, and_(Stage1BeneficiaryRevision.id == Stage2CompanyResearch.beneficiary_revision_id, Stage1BeneficiaryRevision.beneficiary_id == Stage2CompanyResearch.beneficiary_id, Stage1BeneficiaryRevision.selected_map_revision_id == Stage2CompanyResearch.selected_map_revision_id, Stage1BeneficiaryRevision.stock_basic_record_id == Stage2CompanyResearch.stock_basic_record_id)).outerjoin(IndustryMapRevision, and_(IndustryMapRevision.id == Stage2CompanyResearch.selected_map_revision_id, IndustryMapRevision.map_id == Stage2CompanyResearch.map_id)).outerjoin(StockBasicRecord, and_(StockBasicRecord.id == Stage2CompanyResearch.stock_basic_record_id, StockBasicRecord.source == Stage2CompanyResearch.source, StockBasicRecord.stock_code == Stage2CompanyResearch.stock_code)).outerjoin(IngestionRun, IngestionRun.id == StockBasicRecord.ingestion_run_id).order_by(Stage2CompanyResearch.source, Stage2CompanyResearch.stock_code, Stage2CompanyResearch.id)

    @staticmethod
    def _research_statement(ids: tuple[UUID, ...], cutoff: date | None):
        revision = Stage2CompanyResearchRevision
        return select(revision.company_research_id.label('company_research_id'), revision.id.label('revision_id'), revision.revision_no.label('revision_no'), revision.workflow_state.label('workflow_state'), revision.conclusion_status.label('conclusion_status'), revision.research_question.label('research_question'), revision.summary.label('summary'), revision.information_cutoff_date.label('information_cutoff_date'), revision.recorded_at_utc.label('recorded_at_utc'), revision.supersedes_revision_id.label('supersedes_revision_id')).where(revision.company_research_id.in_(ids), *_dated_visibility(revision.information_cutoff_date, revision.recorded_at_utc, cutoff)).order_by(revision.company_research_id, revision.revision_no, revision.recorded_at_utc, revision.id)

    @staticmethod
    def _verification_statement(revision_ids: set[UUID]):
        item = Stage2VerificationItem
        return select(item.id.label('verification_item_id'), item.company_research_revision_id.label('company_research_revision_id'), item.item_no.label('item_no'), item.description.label('description'), item.status.label('status'), item.due_date.label('due_date'), item.recorded_at_utc.label('recorded_at_utc')).where(item.company_research_revision_id.in_(revision_ids)).order_by(item.company_research_revision_id, item.item_no, item.id)

    @staticmethod
    def _module_statement(spec: ModuleSpec, research_id: UUID):
        identity, revision = (spec.identity, spec.revision)
        columns = [identity.id.label('item_id'), identity.company_research_id.label('company_research_id'), getattr(identity, spec.key_field).label('item_key'), identity.created_at_utc.label('created_at_utc'), revision.id.label('revision_id'), revision.revision_no.label('revision_no'), revision.information_cutoff_date.label('information_cutoff_date'), revision.recorded_at_utc.label('recorded_at_utc'), revision.supersedes_revision_id.label('supersedes_revision_id')]
        if spec.research_revision_fk:
            columns.append(getattr(revision, spec.research_revision_fk).label('company_research_revision_id'))
        columns.extend((getattr(revision, field).label(field) for field in spec.fields))
        statement = select(*columns).join(revision, getattr(revision, spec.revision_fk) == identity.id)
        if spec.name == 'valuation':
            statement = statement.outerjoin(DailyPriceRecord, DailyPriceRecord.id == revision.daily_price_id).outerjoin(IngestionRun, IngestionRun.id == DailyPriceRecord.ingestion_run_id).add_columns(DailyPriceRecord.ingestion_run_id.label('price_ingestion_run_id'), DailyPriceRecord.trade_date.label('price_trade_date'), DailyPriceRecord.stock_code.label('price_stock_code'), DailyPriceRecord.close.label('price_close'), DailyPriceRecord.adjust_type.label('price_adjust_type'), DailyPriceRecord.source.label('price_source'), IngestionRun.provider.label('price_ingestion_provider'), IngestionRun.dataset.label('price_ingestion_dataset'), IngestionRun.information_cutoff_date.label('price_ingestion_information_cutoff_date'), IngestionRun.completed_at.label('price_ingestion_completed_at_utc'), IngestionRun.status.label('price_ingestion_status'))
        return statement.where(identity.company_research_id == research_id).order_by(getattr(identity, spec.key_field), identity.id, revision.revision_no, revision.id)

    def _rows(self, statement: Any) -> tuple[dict[str, Any], ...]:
        return tuple((dict(row) for row in self._session.execute(statement).mappings()))
FROZEN_SPECS = (('research', Stage2ResearchHypothesisLink, 'company_research_revision_id', 'hypothesis', 'hypothesis_revision_id'), ('expectation', Stage2ExpectationHypothesisLink, 'expectation_revision_id', 'hypothesis', 'hypothesis_revision_id'), ('valuation', Stage2ValuationHypothesisLink, 'valuation_revision_id', 'hypothesis', 'hypothesis_revision_id'), ('catalyst', Stage2CatalystHypothesisLink, 'catalyst_revision_id', 'hypothesis', 'hypothesis_revision_id'), ('catalyst', Stage2CatalystExpectationLink, 'catalyst_revision_id', 'expectation', 'expectation_revision_id'), ('catalyst', Stage2CatalystValuationLink, 'catalyst_revision_id', 'valuation', 'valuation_revision_id'), ('risk', Stage2RiskHypothesisLink, 'risk_revision_id', 'hypothesis', 'hypothesis_revision_id'), ('risk', Stage2RiskExpectationLink, 'risk_revision_id', 'expectation', 'expectation_revision_id'), ('risk', Stage2RiskValuationLink, 'risk_revision_id', 'valuation', 'valuation_revision_id'))
for module, prefix, models in (('industry_judgment', 'judgment_revision_id', ((Stage2IndustryJudgmentHypothesisLink, 'hypothesis', 'hypothesis_revision_id'), (Stage2IndustryJudgmentExpectationLink, 'expectation', 'expectation_revision_id'), (Stage2IndustryJudgmentValuationLink, 'valuation', 'valuation_revision_id'), (Stage2IndustryJudgmentCatalystLink, 'catalyst', 'catalyst_revision_id'), (Stage2IndustryJudgmentRiskLink, 'risk', 'risk_revision_id'))), ('company_judgment', 'judgment_revision_id', ((Stage2CompanyJudgmentHypothesisLink, 'hypothesis', 'hypothesis_revision_id'), (Stage2CompanyJudgmentExpectationLink, 'expectation', 'expectation_revision_id'), (Stage2CompanyJudgmentValuationLink, 'valuation', 'valuation_revision_id'), (Stage2CompanyJudgmentCatalystLink, 'catalyst', 'catalyst_revision_id'), (Stage2CompanyJudgmentRiskLink, 'risk', 'risk_revision_id')))):
    FROZEN_SPECS += tuple(((module, model, prefix, kind, target) for model, kind, target in models))
CLAIM_SPECS = (('hypothesis', Stage2HypothesisClaimLink, 'hypothesis_revision_id'), ('expectation', Stage2ExpectationClaimLink, 'expectation_revision_id'), ('valuation', Stage2ValuationClaimLink, 'valuation_revision_id'), ('catalyst', Stage2CatalystClaimLink, 'catalyst_revision_id'), ('risk', Stage2RiskClaimLink, 'risk_revision_id'), ('industry_judgment', Stage2IndustryJudgmentClaimLink, 'judgment_revision_id'), ('company_judgment', Stage2CompanyJudgmentClaimLink, 'judgment_revision_id'))
EVIDENCE_SPECS = (('hypothesis', Stage2HypothesisEvidenceLink, 'hypothesis_revision_id'), ('expectation', Stage2ExpectationEvidenceLink, 'expectation_revision_id'), ('valuation', Stage2ValuationEvidenceLink, 'valuation_revision_id'), ('catalyst', Stage2CatalystEvidenceLink, 'catalyst_revision_id'), ('risk', Stage2RiskEvidenceLink, 'risk_revision_id'), ('industry_judgment', Stage2IndustryJudgmentEvidenceLink, 'judgment_revision_id'), ('company_judgment', Stage2CompanyJudgmentEvidenceLink, 'judgment_revision_id'))

def _frozen_statement(revision_sets: dict[str, set[UUID]]):
    branches = []
    for module, model, owner_name, link_kind, target_name in FROZEN_SPECS:
        owner = getattr(model, owner_name)
        branches.append(select(literal(module).label('module'), owner.label('owner_revision_id'), literal(link_kind).label('link_kind'), getattr(model, target_name).label('linked_revision_id'), model.recorded_at_utc.label('recorded_at_utc')).where(owner.in_(revision_sets[module])))
    return union_all(*branches).order_by('module', 'owner_revision_id', 'link_kind', 'linked_revision_id')

def _claim_statement(revision_sets: dict[str, set[UUID]]):
    branches = []
    for module, model, owner_name in CLAIM_SPECS:
        owner = getattr(model, owner_name)
        branches.append(select(literal(module).label('module'), owner.label('owner_revision_id'), model.id.label('claim_link_id'), model.claim_revision_id.label('claim_revision_id'), Claim.id.label('claim_id'), Claim.claim_key.label('claim_key'), ClaimRevision.revision_no.label('claim_revision_no'), ClaimRevision.statement.label('statement'), ClaimRevision.claim_kind.label('claim_kind'), ClaimRevision.claim_status.label('claim_status'), ClaimRevision.inference_confidence.label('inference_confidence'), ClaimRevision.information_cutoff_date.label('information_cutoff_date'), ClaimRevision.recorded_at_utc.label('claim_recorded_at_utc'), model.recorded_at_utc.label('recorded_at_utc')).join(ClaimRevision, ClaimRevision.id == model.claim_revision_id).join(Claim, Claim.id == ClaimRevision.claim_id).where(owner.in_(revision_sets[module])))
    return union_all(*branches).order_by('module', 'owner_revision_id', 'claim_key', 'claim_revision_id')

def _evidence_statement(revision_sets: dict[str, set[UUID]]):
    branches = []
    for module, model, owner_name in EVIDENCE_SPECS:
        owner = getattr(model, owner_name)
        branches.append(select(literal(module).label('module'), owner.label('owner_revision_id'), model.id.label('evidence_boundary_link_id'), model.claim_revision_id.label('claim_revision_id'), model.claim_evidence_link_id.label('claim_evidence_link_id'), model.evidence_id.label('evidence_id'), ClaimEvidenceLink.claim_revision_id.label('source_claim_revision_id'), ClaimEvidenceLink.evidence_id.label('source_evidence_id'), ClaimEvidenceLink.relation.label('relation'), ClaimEvidenceLink.recorded_at_utc.label('source_link_recorded_at_utc'), EvidenceItem.evidence_grade.label('evidence_grade'), EvidenceItem.source_kind.label('source_kind'), EvidenceItem.source_title.label('source_title'), EvidenceItem.information_date.label('information_date'), EvidenceItem.recorded_at_utc.label('evidence_recorded_at_utc'), model.recorded_at_utc.label('recorded_at_utc')).join(ClaimEvidenceLink, ClaimEvidenceLink.id == model.claim_evidence_link_id).join(EvidenceItem, EvidenceItem.id == model.evidence_id).where(owner.in_(revision_sets[module])))
    return union_all(*branches).order_by('module', 'owner_revision_id', 'relation', 'evidence_grade', 'evidence_id')

def _assertion_branch(research_id: UUID, kind: str, target_column: Any, target_model: Any):
    null_uuid = cast(literal(None), Uuid)
    return select(literal('assertion').label('handoff_kind'), Stage2HandoffAssertionLink.id.label('handoff_link_id'), Stage2HandoffAssertionLink.stage1_beneficiary_assertion_link_id.label('source_link_id'), Stage1BeneficiaryAssertionLink.beneficiary_revision_id.label('beneficiary_revision_id'), literal(kind).label('target_kind'), target_column.label('target_id'), null_uuid.label('claim_revision_id'), null_uuid.label('evidence_id'), target_model.information_cutoff_date.label('target_information_cutoff_date'), target_model.recorded_at_utc.label('target_recorded_at_utc'), null_uuid.label('source_claim_revision_id'), null_uuid.label('source_evidence_id'), Stage1BeneficiaryAssertionLink.recorded_at_utc.label('source_link_recorded_at_utc'), Stage2HandoffAssertionLink.recorded_at_utc.label('recorded_at_utc')).join(Stage1BeneficiaryAssertionLink, Stage1BeneficiaryAssertionLink.id == Stage2HandoffAssertionLink.stage1_beneficiary_assertion_link_id).join(target_model, target_model.id == target_column).where(Stage2HandoffAssertionLink.company_research_id == research_id, target_column.is_not(None))

def _handoff_statement(research_id: UUID):
    null_uuid = cast(literal(None), Uuid)
    assertions = (_assertion_branch(research_id, 'node_revision', Stage1BeneficiaryAssertionLink.node_revision_id, IndustryMapNodeRevision), _assertion_branch(research_id, 'relationship_revision', Stage1BeneficiaryAssertionLink.relationship_revision_id, IndustryMapRelationshipRevision), _assertion_branch(research_id, 'observation_revision', Stage1BeneficiaryAssertionLink.observation_revision_id, IndustryMapObservationRevision))
    claim = select(literal('claim').label('handoff_kind'), Stage2HandoffClaimLink.id.label('handoff_link_id'), Stage2HandoffClaimLink.stage1_beneficiary_claim_link_id.label('source_link_id'), Stage1BeneficiaryClaimLink.beneficiary_revision_id.label('beneficiary_revision_id'), literal('claim_revision').label('target_kind'), Stage2HandoffClaimLink.claim_revision_id.label('target_id'), Stage2HandoffClaimLink.claim_revision_id.label('claim_revision_id'), null_uuid.label('evidence_id'), ClaimRevision.information_cutoff_date.label('target_information_cutoff_date'), ClaimRevision.recorded_at_utc.label('target_recorded_at_utc'), Stage1BeneficiaryClaimLink.claim_revision_id.label('source_claim_revision_id'), null_uuid.label('source_evidence_id'), Stage1BeneficiaryClaimLink.recorded_at_utc.label('source_link_recorded_at_utc'), Stage2HandoffClaimLink.recorded_at_utc.label('recorded_at_utc')).join(Stage1BeneficiaryClaimLink, Stage1BeneficiaryClaimLink.id == Stage2HandoffClaimLink.stage1_beneficiary_claim_link_id).join(ClaimRevision, ClaimRevision.id == Stage2HandoffClaimLink.claim_revision_id).where(Stage2HandoffClaimLink.company_research_id == research_id)
    evidence = select(literal('evidence').label('handoff_kind'), Stage2HandoffEvidenceLink.id.label('handoff_link_id'), Stage2HandoffEvidenceLink.claim_evidence_link_id.label('source_link_id'), null_uuid.label('beneficiary_revision_id'), literal('evidence').label('target_kind'), Stage2HandoffEvidenceLink.evidence_id.label('target_id'), Stage2HandoffEvidenceLink.claim_revision_id.label('claim_revision_id'), Stage2HandoffEvidenceLink.evidence_id.label('evidence_id'), EvidenceItem.information_date.label('target_information_cutoff_date'), EvidenceItem.recorded_at_utc.label('target_recorded_at_utc'), ClaimEvidenceLink.claim_revision_id.label('source_claim_revision_id'), ClaimEvidenceLink.evidence_id.label('source_evidence_id'), ClaimEvidenceLink.recorded_at_utc.label('source_link_recorded_at_utc'), Stage2HandoffEvidenceLink.recorded_at_utc.label('recorded_at_utc')).join(ClaimEvidenceLink, ClaimEvidenceLink.id == Stage2HandoffEvidenceLink.claim_evidence_link_id).join(EvidenceItem, EvidenceItem.id == Stage2HandoffEvidenceLink.evidence_id).where(Stage2HandoffEvidenceLink.company_research_id == research_id)
    return union_all(*assertions, claim, evidence).order_by('handoff_kind', 'source_link_id', 'target_id')

def _recorded_visibility(column: Any, cutoff: date | None) -> tuple[Any, ...]:
    return () if cutoff is None else (column < _next_day(cutoff),)

def _dated_visibility(info: Any, recorded: Any, cutoff: date | None) -> tuple[Any, ...]:
    return () if cutoff is None else (info <= cutoff, recorded < _next_day(cutoff))

def _next_day(cutoff: date) -> datetime:
    return datetime.combine(cutoff + timedelta(days=1), time.min, tzinfo=timezone.utc)

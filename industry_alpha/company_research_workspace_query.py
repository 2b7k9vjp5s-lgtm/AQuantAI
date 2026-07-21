"""Deterministic projection logic for the Company Research Workspace."""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Any, Iterable
from uuid import UUID
from industry_alpha.company_research_workspace_contracts import CompanyResearchSelectorContract, CompanyResearchWorkspaceContract
from industry_alpha.company_research_workspace_repository import CompanyResearchWorkspaceDataError, CompanyResearchWorkspaceRepository, WorkspaceReadSet
from industry_alpha.errors import EvidenceLedgerNotFound, EvidenceLedgerNotVisible
from industry_alpha.stage2_query_values import date_text, dated_visible, recorded_visible, timestamp_text, uuid_text
WORKSPACE_NOTICES: dict[str, Any] = {'read_only': True, 'research_only': True, 'not_investment_advice': True, 'explicit_identity_only': True, 'no_identity_inference_or_fallback': True, 'no_scores_rankings_or_recommendations': True, 'no_canonical_price_or_comparison_eligibility': True, 'no_target_price_fair_value_expected_return_or_upside': True, 'valuation_section_meaning': '估值观察保留原始研究字段和可选本地价格来源，不代表估值结论、可比性、目标价或预期收益。', 'historical_revision_meaning': '下游记录冻结的公司研究修订与当前最新可见修订不一致时，作为历史事实显示，不自动重绑。', 'semantic_qualification': {'D0': '持久化身份、日期、UTC、修订号与来源记录。', 'D1': '确定性数量、冲突数量、缺失证据数量与证据等级数量。', 'D2': 'Stage 1 受益类型、证据等级和证据关系。', 'D3': '公司研究、假设、预期、估值观察、催化剂、风险和质量判断。', 'L1_price_context': '可选本地日线记录仅为来源上下文，不是 Canonical Price。'}, 'no_hidden_network_requests': True}
MODULES = ('hypothesis', 'expectation', 'valuation', 'catalyst', 'risk', 'industry_judgment', 'company_judgment')
MODULE_ID_FIELDS = {'hypothesis': 'hypothesis_id', 'expectation': 'expectation_id', 'valuation': 'valuation_id', 'catalyst': 'catalyst_id', 'risk': 'risk_id', 'industry_judgment': 'judgment_id', 'company_judgment': 'judgment_id'}
DETAIL_ROUTES = {'company_research': '/industry-alpha/company-research/{company_research_id}', 'hypothesis': '/industry-alpha/company-research/{company_research_id}', 'expectation': '/industry-alpha/market-expectations/{expectation_id}', 'valuation': '/industry-alpha/valuation-snapshots/{valuation_id}', 'catalyst': '/industry-alpha/catalyst-assessments/{catalyst_id}', 'risk': '/industry-alpha/risk-assessments/{risk_id}', 'industry_judgment': '/industry-alpha/industry-judgments/{judgment_id}', 'company_judgment': '/industry-alpha/company-judgments/{judgment_id}'}

class CompanyResearchWorkspaceQueryService:

    def __init__(self, repository: CompanyResearchWorkspaceRepository) -> None:
        self._repository = repository

    def list_research(self, *, as_of_cutoff: date | None=None) -> CompanyResearchSelectorContract:
        roots = self._repository.list_selector_roots(as_of_cutoff=as_of_cutoff)
        research_ids = tuple((_required_uuid(row, 'company_research_id') for row in roots))
        if len(research_ids) != len(set(research_ids)):
            raise CompanyResearchWorkspaceDataError('selector returned duplicate exact company research roots')
        revisions = self._repository.list_research_revisions(research_ids, as_of_cutoff=as_of_cutoff)
        availability_rows = self._repository.list_availability(research_ids, as_of_cutoff=as_of_cutoff)
        availability: dict[UUID, dict[str, int]] = {research_id: {module: 0 for module in MODULES} for research_id in research_ids}
        for row in availability_rows:
            research_id = _required_uuid(row, 'company_research_id')
            module = _required_text(row, 'module')
            if research_id not in availability or module not in MODULES:
                raise CompanyResearchWorkspaceDataError('selector availability references an incompatible identity or module')
            if availability[research_id][module] != 0:
                raise CompanyResearchWorkspaceDataError('selector availability returned a duplicate identity/module relation')
            availability[research_id][module] = _required_nonnegative_int(row, 'visible_count')
        revisions_by_research: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
        for row in revisions:
            revisions_by_research[_required_uuid(row, 'company_research_id')].append(row)
        payload: list[dict[str, Any]] = []
        for root in roots:
            _validate_root(root, as_of_cutoff)
            research_id = _required_uuid(root, 'company_research_id')
            history = sorted(revisions_by_research.get(research_id, []), key=_revision_sort_key)
            _validate_revision_history(history, 'company research')
            if not history:
                continue
            payload.append(_selector_payload(root, history[-1], availability[research_id]))
        payload.sort(key=lambda item: (item['source'], item['stock_code'], item['company_research_id']))
        return CompanyResearchSelectorContract(as_of_cutoff=date_text(as_of_cutoff), research=tuple(payload), notices=dict(WORKSPACE_NOTICES))

    def get_workspace(self, research_id: UUID, *, as_of_cutoff: date | None=None) -> CompanyResearchWorkspaceContract:
        rows = self._repository.load_workspace(research_id)
        if rows.root is None:
            raise EvidenceLedgerNotFound(f'Stage 2 company research {research_id} was not found.')
        root = rows.root
        if _required_uuid(root, 'company_research_id') != research_id:
            raise CompanyResearchWorkspaceDataError('workspace root identity does not match the requested identity')
        _validate_root(root, as_of_cutoff)
        research_history = [row for row in rows.research_revisions if dated_visible(_required_date(row, 'information_cutoff_date'), _required_datetime(row, 'recorded_at_utc'), as_of_cutoff)]
        research_history.sort(key=_revision_sort_key)
        _validate_revision_history(research_history, 'company research')
        if not research_history:
            raise EvidenceLedgerNotVisible(f'Stage 2 company research {research_id} has no visible revision.')
        latest_research_revision_id = _required_uuid(research_history[-1], 'revision_id')
        visible_rows = {'hypothesis': _visible_module_rows(rows.hypotheses, as_of_cutoff), 'expectation': _visible_module_rows(rows.expectations, as_of_cutoff), 'valuation': _visible_module_rows(rows.valuations, as_of_cutoff), 'catalyst': _visible_module_rows(rows.catalysts, as_of_cutoff), 'risk': _visible_module_rows(rows.risks, as_of_cutoff), 'industry_judgment': _visible_module_rows(rows.industry_judgments, as_of_cutoff), 'company_judgment': _visible_module_rows(rows.company_judgments, as_of_cutoff)}
        visible_revision_ids = {'research': {_required_uuid(row, 'revision_id') for row in research_history}}
        visible_revision_ids.update({module: {_required_uuid(row, 'revision_id') for row in module_rows} for module, module_rows in visible_rows.items()})
        for module, module_rows in visible_rows.items():
            if module == 'hypothesis':
                continue
            for row in module_rows:
                frozen_research_id = _required_uuid(row, 'company_research_revision_id')
                if frozen_research_id not in visible_revision_ids['research']:
                    raise CompanyResearchWorkspaceDataError(f'visible {module} revision freezes a cutoff-invisible company research revision')
        frozen_links = _project_frozen_links(rows.frozen_links, visible_revision_ids, as_of_cutoff)
        claim_links = _project_claim_links(rows.claim_links, visible_revision_ids, as_of_cutoff)
        evidence_links = _project_evidence_links(rows.evidence_links, visible_revision_ids, claim_links, as_of_cutoff)
        evidence_by_owner = _evidence_summary_by_owner(claim_links, evidence_links)
        research_freezes = _reverse_research_hypothesis_links(frozen_links)
        module_payloads = {module: _module_payloads(module, module_rows, latest_research_revision_id, frozen_links, evidence_by_owner, research_freezes, root, as_of_cutoff) for module, module_rows in visible_rows.items()}
        visible_handoff = _project_handoff_links(rows.handoff_links, root, as_of_cutoff)
        verification = tuple((_verification_payload(row) for row in rows.verification_items if _required_uuid(row, 'company_research_revision_id') in visible_revision_ids['research'] and recorded_visible(_required_datetime(row, 'recorded_at_utc'), as_of_cutoff)))
        aggregate = _aggregate_evidence_summary(module_payloads)
        company_research = {'latest_revision': _research_revision_payload(research_history[-1]), 'revision_history': tuple((_research_revision_payload(row) for row in research_history)), 'verification_items': verification, 'verification_count': len(verification), 'detail_path': f'/industry-alpha/company-research/{research_id}'}
        return CompanyResearchWorkspaceContract(as_of_cutoff=date_text(as_of_cutoff), identity={'company_research_id': str(research_id), 'case_id': str(_required_uuid(root, 'case_id')), 'map_id': str(_required_uuid(root, 'map_id')), 'source': _required_text(root, 'source'), 'stock_code': _required_text(root, 'stock_code'), 'created_at_utc': timestamp_text(_required_datetime(root, 'created_at_utc')), 'stock_name': _required_text(root, 'stock_name'), 'exchange': _required_text(root, 'exchange', allow_empty=True), 'provider_industry': _required_text(root, 'provider_industry', allow_empty=True)}, frozen_stage1=_frozen_stage1_payload(root, visible_handoff), company_research=company_research, hypotheses=module_payloads['hypothesis'], expectations=module_payloads['expectation'], valuation_observations=module_payloads['valuation'], catalysts=module_payloads['catalyst'], risks=module_payloads['risk'], industry_judgments=module_payloads['industry_judgment'], company_judgments=module_payloads['company_judgment'], evidence_summary=aggregate, detail_routes=dict(DETAIL_ROUTES), notices=dict(WORKSPACE_NOTICES))

def _selector_payload(root: dict[str, Any], latest: dict[str, Any], availability: dict[str, int]) -> dict[str, Any]:
    return {'company_research_id': str(_required_uuid(root, 'company_research_id')), 'case_id': str(_required_uuid(root, 'case_id')), 'map_id': str(_required_uuid(root, 'map_id')), 'source': _required_text(root, 'source'), 'stock_code': _required_text(root, 'stock_code'), 'stock_name': _required_text(root, 'stock_name'), 'exchange': _required_text(root, 'exchange', allow_empty=True), 'provider_industry': _required_text(root, 'provider_industry', allow_empty=True), 'created_at_utc': timestamp_text(_required_datetime(root, 'created_at_utc')), 'frozen_stage1': {'candidate_pool_id': str(_required_uuid(root, 'candidate_pool_id')), 'candidate_pool_revision_id': str(_required_uuid(root, 'candidate_pool_revision_id')), 'candidate_pool_membership_id': str(_required_uuid(root, 'candidate_pool_membership_id')), 'beneficiary_id': str(_required_uuid(root, 'beneficiary_id')), 'beneficiary_revision_id': str(_required_uuid(root, 'beneficiary_revision_id')), 'selected_map_revision_id': str(_required_uuid(root, 'selected_map_revision_id')), 'stock_basic_record_id': _required_int(root, 'stock_basic_record_id')}, 'latest_revision': _research_revision_payload(latest), 'availability': {f'{module}_count': availability[module] for module in MODULES}}

def _validate_root(root: dict[str, Any], cutoff: date | None) -> None:
    if not recorded_visible(_required_datetime(root, 'created_at_utc'), cutoff):
        raise EvidenceLedgerNotVisible('company research identity is not visible at the requested cutoff')
    research_id = _required_uuid(root, 'company_research_id')
    selected_map_revision_id = _required_uuid(root, 'selected_map_revision_id')
    stock_id = _required_int(root, 'stock_basic_record_id')
    for field in ('candidate_pool_id', 'candidate_pool_revision_id', 'candidate_pool_membership_id', 'beneficiary_id', 'beneficiary_revision_id', 'selected_map_revision_id'):
        _required_uuid(root, field)
    if _required_uuid(root, 'beneficiary_selected_map_revision_id') != selected_map_revision_id:
        raise CompanyResearchWorkspaceDataError(f'company research {research_id} frozen map revision mismatch')
    if _required_int(root, 'beneficiary_stock_basic_record_id') != stock_id:
        raise CompanyResearchWorkspaceDataError(f'company research {research_id} frozen stock row mismatch')
    if _required_uuid(root, 'pool_selected_map_revision_id') != selected_map_revision_id:
        raise CompanyResearchWorkspaceDataError(f'company research {research_id} pool map revision mismatch')
    if _required_uuid(root, 'map_revision_map_id') != _required_uuid(root, 'map_id'):
        raise CompanyResearchWorkspaceDataError(f'company research {research_id} map revision identity mismatch')
    if _required_uuid(root, 'beneficiary_case_id') != _required_uuid(root, 'case_id') or _required_uuid(root, 'beneficiary_map_id') != _required_uuid(root, 'map_id'):
        raise CompanyResearchWorkspaceDataError(f'company research {research_id} Stage 1 identity mismatch')
    source = _required_text(root, 'source')
    stock_code = _required_text(root, 'stock_code')
    if _required_text(root, 'beneficiary_source') != source or _required_text(root, 'beneficiary_stock_code') != stock_code or _required_text(root, 'stock_record_source') != source or (_required_text(root, 'stock_record_code') != stock_code):
        raise CompanyResearchWorkspaceDataError(f'company research {research_id} exact stock provenance mismatch')
    if _required_text(root, 'ingestion_status') != 'succeeded':
        raise CompanyResearchWorkspaceDataError(f'company research {research_id} stock provenance is not succeeded')
    completed_at = _required_datetime(root, 'ingestion_completed_at_utc')
    for prefix in ('candidate_pool', 'beneficiary', 'map'):
        if not dated_visible(_required_date(root, f'{prefix}_information_cutoff_date'), _required_datetime(root, f'{prefix}_recorded_at_utc'), cutoff):
            raise EvidenceLedgerNotVisible(f'required frozen {prefix} revision is not visible at the requested cutoff')
    for field in ('candidate_pool_created_at_utc', 'membership_recorded_at_utc', 'beneficiary_created_at_utc'):
        if not recorded_visible(_required_datetime(root, field), cutoff):
            raise EvidenceLedgerNotVisible('required frozen Stage 1 provenance is not visible at the requested cutoff')
    ingestion_cutoff = _required_date(root, 'ingestion_information_cutoff_date')
    if cutoff is not None and (ingestion_cutoff > cutoff or completed_at.date() > cutoff):
        raise EvidenceLedgerNotVisible('required stock ingestion provenance is not visible at the requested cutoff')

def _visible_module_rows(rows: Iterable[dict[str, Any]], cutoff: date | None) -> tuple[dict[str, Any], ...]:
    visible = []
    for row in rows:
        if not recorded_visible(_required_datetime(row, 'created_at_utc'), cutoff):
            continue
        if not dated_visible(_required_date(row, 'information_cutoff_date'), _required_datetime(row, 'recorded_at_utc'), cutoff):
            continue
        visible.append(row)
    visible.sort(key=lambda row: (_required_text(row, 'item_key'), str(_required_uuid(row, 'item_id')), *_revision_sort_key(row)))
    return tuple(visible)

def _project_frozen_links(rows: Iterable[dict[str, Any]], visible_revision_ids: dict[str, set[UUID]], cutoff: date | None) -> dict[tuple[str, UUID], dict[str, tuple[str, ...]]]:
    grouped: dict[tuple[str, UUID], dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        if not recorded_visible(_required_datetime(row, 'recorded_at_utc'), cutoff):
            continue
        module = _required_text(row, 'module')
        owner = _required_uuid(row, 'owner_revision_id')
        kind = _required_text(row, 'link_kind')
        linked = _required_uuid(row, 'linked_revision_id')
        if owner not in visible_revision_ids.get(module, set()):
            continue
        if linked not in visible_revision_ids.get(kind, set()):
            raise CompanyResearchWorkspaceDataError(f'visible {module} revision {owner} has dangling frozen {kind} revision {linked}')
        grouped[module, owner][kind].append(str(linked))
    return {key: {kind: tuple(sorted(set(values))) for kind, values in sorted(kinds.items())} for key, kinds in grouped.items()}

def _project_claim_links(rows: Iterable[dict[str, Any]], visible_revision_ids: dict[str, set[UUID]], cutoff: date | None) -> dict[tuple[str, UUID], tuple[dict[str, Any], ...]]:
    grouped: dict[tuple[str, UUID], list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, UUID, UUID]] = set()
    for row in rows:
        module = _required_text(row, 'module')
        owner = _required_uuid(row, 'owner_revision_id')
        claim_revision_id = _required_uuid(row, 'claim_revision_id')
        if owner not in visible_revision_ids.get(module, set()):
            continue
        if not recorded_visible(_required_datetime(row, 'recorded_at_utc'), cutoff):
            continue
        if not dated_visible(_required_date(row, 'information_cutoff_date'), _required_datetime(row, 'claim_recorded_at_utc'), cutoff):
            raise CompanyResearchWorkspaceDataError(f'visible {module} revision {owner} references a cutoff-invisible claim revision')
        key = (module, owner, claim_revision_id)
        if key in seen:
            raise CompanyResearchWorkspaceDataError(f'duplicate exact claim boundary for {module} revision {owner}')
        seen.add(key)
        grouped[module, owner].append({'claim_id': str(_required_uuid(row, 'claim_id')), 'claim_key': _required_text(row, 'claim_key'), 'claim_revision_id': str(claim_revision_id), 'claim_revision_no': _required_int(row, 'claim_revision_no'), 'claim_kind': _required_text(row, 'claim_kind'), 'claim_status': _required_text(row, 'claim_status')})
    return {key: tuple(sorted(values, key=lambda item: (item['claim_key'], item['claim_revision_id']))) for key, values in grouped.items()}

def _project_evidence_links(rows: Iterable[dict[str, Any]], visible_revision_ids: dict[str, set[UUID]], claim_links: dict[tuple[str, UUID], tuple[dict[str, Any], ...]], cutoff: date | None) -> dict[tuple[str, UUID], tuple[dict[str, Any], ...]]:
    grouped: dict[tuple[str, UUID], list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, UUID, UUID]] = set()
    for row in rows:
        module = _required_text(row, 'module')
        owner = _required_uuid(row, 'owner_revision_id')
        if owner not in visible_revision_ids.get(module, set()):
            continue
        if not recorded_visible(_required_datetime(row, 'recorded_at_utc'), cutoff):
            continue
        if not recorded_visible(_required_datetime(row, 'source_link_recorded_at_utc'), cutoff):
            raise CompanyResearchWorkspaceDataError(f'visible {module} evidence boundary references a cutoff-invisible source link')
        claim_revision_id = _required_uuid(row, 'claim_revision_id')
        evidence_id = _required_uuid(row, 'evidence_id')
        if _required_uuid(row, 'source_claim_revision_id') != claim_revision_id or _required_uuid(row, 'source_evidence_id') != evidence_id:
            raise CompanyResearchWorkspaceDataError(f'{module} evidence boundary does not match its source claim-evidence link')
        known_claim_ids = {item['claim_revision_id'] for item in claim_links.get((module, owner), ())}
        if str(claim_revision_id) not in known_claim_ids:
            raise CompanyResearchWorkspaceDataError(f'{module} evidence boundary references an unfrozen claim revision')
        information_date = _required_date(row, 'information_date')
        evidence_recorded = _required_datetime(row, 'evidence_recorded_at_utc')
        if cutoff is not None and (information_date > cutoff or evidence_recorded.date() > cutoff):
            raise CompanyResearchWorkspaceDataError(f'visible {module} revision references cutoff-invisible evidence')
        key = (module, owner, _required_uuid(row, 'claim_evidence_link_id'))
        if key in seen:
            raise CompanyResearchWorkspaceDataError(f'duplicate exact evidence boundary for {module} revision {owner}')
        seen.add(key)
        grouped[module, owner].append({'claim_revision_id': str(claim_revision_id), 'claim_evidence_link_id': str(_required_uuid(row, 'claim_evidence_link_id')), 'evidence_id': str(evidence_id), 'relation': _required_text(row, 'relation'), 'evidence_grade': _required_text(row, 'evidence_grade'), 'source_kind': _required_text(row, 'source_kind'), 'source_title': _required_text(row, 'source_title'), 'information_date': date_text(information_date)})
    return {key: tuple(sorted(values, key=lambda item: (item['relation'], item['evidence_grade'], item['information_date'], item['evidence_id']))) for key, values in grouped.items()}

def _evidence_summary_by_owner(claims: dict[tuple[str, UUID], tuple[dict[str, Any], ...]], evidence: dict[tuple[str, UUID], tuple[dict[str, Any], ...]]) -> dict[tuple[str, UUID], dict[str, Any]]:
    result: dict[tuple[str, UUID], dict[str, Any]] = {}
    for key in set(claims) | set(evidence):
        claim_rows = claims.get(key, ())
        evidence_rows = evidence.get(key, ())
        grades = Counter((item['evidence_grade'] for item in evidence_rows))
        conflicts = tuple(({'claim_revision_id': item['claim_revision_id'], 'evidence_id': item['evidence_id'], 'evidence_grade': item['evidence_grade'], 'source_title': item['source_title']} for item in evidence_rows if item['relation'] == 'contradicts'))
        evidence_claims = {item['claim_revision_id'] for item in evidence_rows}
        missing = tuple(({'claim_key': item['claim_key'], 'claim_revision_id': item['claim_revision_id'], 'reason': '尚未获得可靠公开证据'} for item in claim_rows if item['claim_revision_id'] not in evidence_claims))
        result[key] = {'claim_count': len(claim_rows), 'evidence_count': len(evidence_rows), 'evidence_grade_counts': {grade: grades[grade] for grade in ('A', 'B', 'C', 'D')}, 'conflict_count': len(conflicts), 'missing_evidence_count': len(missing), 'conflicts': conflicts, 'missing_evidence': missing}
    return result

def _reverse_research_hypothesis_links(frozen_links: dict[tuple[str, UUID], dict[str, tuple[str, ...]]]) -> dict[UUID, tuple[str, ...]]:
    reverse: dict[UUID, list[str]] = defaultdict(list)
    for (module, owner), links in frozen_links.items():
        if module != 'research':
            continue
        for hypothesis_revision_id in links.get('hypothesis', ()):
            reverse[UUID(hypothesis_revision_id)].append(str(owner))
    return {key: tuple(sorted(set(values))) for key, values in reverse.items()}

def _module_payloads(module: str, rows: tuple[dict[str, Any], ...], latest_research_revision_id: UUID, frozen_links: dict[tuple[str, UUID], dict[str, tuple[str, ...]]], evidence_by_owner: dict[tuple[str, UUID], dict[str, Any]], research_freezes: dict[UUID, tuple[str, ...]], root: dict[str, Any], cutoff: date | None) -> tuple[dict[str, Any], ...]:
    grouped: dict[UUID, list[dict[str, Any]]] = defaultdict(list)
    keys: dict[UUID, str] = {}
    created: dict[UUID, datetime] = {}
    for row in rows:
        item_id = _required_uuid(row, 'item_id')
        item_key = _required_text(row, 'item_key')
        created_at = _required_datetime(row, 'created_at_utc')
        if item_id in keys and (keys[item_id] != item_key or created[item_id] != created_at):
            raise CompanyResearchWorkspaceDataError(f'{module} identity has incompatible duplicate scalar values')
        grouped[item_id].append(row)
        keys[item_id] = item_key
        created[item_id] = created_at
    payload = []
    for item_id, history_rows in grouped.items():
        history_rows.sort(key=_revision_sort_key)
        _validate_revision_history(history_rows, module)
        history = tuple((_decorated_module_revision(module, row, latest_research_revision_id, frozen_links, evidence_by_owner, research_freezes, root, cutoff) for row in history_rows))
        identity_field = MODULE_ID_FIELDS[module]
        route = DETAIL_ROUTES[module].format(company_research_id=_required_uuid(root, 'company_research_id'), expectation_id=item_id, valuation_id=item_id, catalyst_id=item_id, risk_id=item_id, judgment_id=item_id)
        payload.append({identity_field: str(item_id), 'key': keys[item_id], 'created_at_utc': timestamp_text(created[item_id]), 'latest_revision': history[-1], 'revision_history': history, 'detail_path': route})
    payload.sort(key=lambda item: (item['key'], item[MODULE_ID_FIELDS[module]]))
    return tuple(payload)

def _decorated_module_revision(module: str, row: dict[str, Any], latest_research_revision_id: UUID, frozen_links: dict[tuple[str, UUID], dict[str, tuple[str, ...]]], evidence_by_owner: dict[tuple[str, UUID], dict[str, Any]], research_freezes: dict[UUID, tuple[str, ...]], root: dict[str, Any], cutoff: date | None) -> dict[str, Any]:
    revision_id = _required_uuid(row, 'revision_id')
    payload = _generic_revision_payload(row)
    payload['frozen_links'] = dict(frozen_links.get((module, revision_id), {}))
    payload['evidence_summary'] = dict(evidence_by_owner.get((module, revision_id), _empty_evidence_summary()))
    if module == 'hypothesis':
        frozen_research = research_freezes.get(revision_id, ())
        if not frozen_research:
            raise CompanyResearchWorkspaceDataError(f'visible hypothesis revision {revision_id} is not frozen by any cutoff-visible company research revision')
        payload['frozen_company_research_revision_ids'] = frozen_research
        payload['historical_revision_mismatch'] = str(latest_research_revision_id) not in frozen_research
    else:
        frozen_research_id = _required_uuid(row, 'company_research_revision_id')
        payload['historical_revision_mismatch'] = frozen_research_id != latest_research_revision_id
    if module == 'valuation':
        payload['price_reference'] = _price_reference_payload(row, root, cutoff)
    return payload

def _generic_revision_payload(row: dict[str, Any]) -> dict[str, Any]:
    excluded = {'item_id', 'item_key', 'company_research_id', 'created_at_utc', 'daily_price_id', 'price_ingestion_run_id', 'price_trade_date', 'price_stock_code', 'price_close', 'price_adjust_type', 'price_source', 'price_ingestion_provider', 'price_ingestion_dataset', 'price_ingestion_information_cutoff_date', 'price_ingestion_completed_at_utc', 'price_ingestion_status'}
    return {key: _json_value(value) for key, value in row.items() if key not in excluded}

def _price_reference_payload(row: dict[str, Any], root: dict[str, Any], cutoff: date | None) -> dict[str, Any] | None:
    price_id = row.get('daily_price_id')
    if price_id is None:
        return None
    if _required_text(row, 'price_source') != _required_text(root, 'source') or _required_text(row, 'price_stock_code') != _required_text(root, 'stock_code') or _required_text(row, 'price_ingestion_status') != 'succeeded':
        raise CompanyResearchWorkspaceDataError('valuation local price provenance does not match the selected company identity')
    completed_at = _required_datetime(row, 'price_ingestion_completed_at_utc')
    trade_date = _required_date(row, 'price_trade_date')
    ingestion_cutoff = _required_date(row, 'price_ingestion_information_cutoff_date')
    if cutoff is not None and (trade_date > cutoff or ingestion_cutoff > cutoff or completed_at.date() > cutoff):
        raise CompanyResearchWorkspaceDataError('valuation local price provenance is not visible at the requested cutoff')
    return {'semantic_level': 'L1 source context', 'daily_price_id': _required_int(row, 'daily_price_id'), 'trade_date': date_text(trade_date), 'close': row.get('price_close'), 'adjust_type': _required_text(row, 'price_adjust_type', allow_empty=True), 'source': _required_text(row, 'price_source'), 'ingestion_run_id': _required_int(row, 'price_ingestion_run_id'), 'ingestion_provider': _required_text(row, 'price_ingestion_provider'), 'ingestion_dataset': _required_text(row, 'price_ingestion_dataset'), 'ingestion_information_cutoff_date': date_text(ingestion_cutoff), 'ingestion_completed_at_utc': timestamp_text(completed_at)}

def _project_handoff_links(rows: Iterable[dict[str, Any]], root: dict[str, Any], cutoff: date | None) -> tuple[dict[str, Any], ...]:
    beneficiary_revision_id = _required_uuid(root, 'beneficiary_revision_id')
    claim_revision_ids: set[UUID] = set()
    projected: list[dict[str, Any]] = []
    seen: set[tuple[str, UUID, UUID]] = set()
    for row in rows:
        recorded_at = _required_datetime(row, 'recorded_at_utc')
        if not recorded_visible(recorded_at, cutoff):
            continue
        if not recorded_visible(_required_datetime(row, 'source_link_recorded_at_utc'), cutoff):
            raise CompanyResearchWorkspaceDataError('Stage 2 handoff references a cutoff-invisible Stage 1 source link')
        kind = _required_text(row, 'handoff_kind')
        source_link_id = _required_uuid(row, 'source_link_id')
        target_id = _required_uuid(row, 'target_id')
        exact_key = (kind, source_link_id, target_id)
        if exact_key in seen:
            raise CompanyResearchWorkspaceDataError('duplicate exact Stage 2 handoff boundary')
        seen.add(exact_key)
        if kind in {'assertion', 'claim'} and _required_uuid(row, 'beneficiary_revision_id') != beneficiary_revision_id:
            raise CompanyResearchWorkspaceDataError('Stage 2 handoff link does not belong to the frozen Stage 1 beneficiary revision')
        target_information_date = _required_date(row, 'target_information_cutoff_date')
        target_recorded_at = _required_datetime(row, 'target_recorded_at_utc')
        if cutoff is not None and (target_information_date > cutoff or target_recorded_at.date() > cutoff):
            raise CompanyResearchWorkspaceDataError('Stage 2 handoff references a cutoff-invisible frozen target')
        claim_revision_id = row.get('claim_revision_id')
        evidence_id = row.get('evidence_id')
        if kind == 'claim':
            claim_id = _required_uuid(row, 'claim_revision_id')
            if _required_uuid(row, 'source_claim_revision_id') != claim_id:
                raise CompanyResearchWorkspaceDataError('Stage 2 handoff claim does not match its Stage 1 source link')
            claim_revision_ids.add(claim_id)
        if kind == 'evidence':
            claim_id = _required_uuid(row, 'claim_revision_id')
            exact_evidence_id = _required_uuid(row, 'evidence_id')
            if _required_uuid(row, 'source_claim_revision_id') != claim_id or _required_uuid(row, 'source_evidence_id') != exact_evidence_id:
                raise CompanyResearchWorkspaceDataError('Stage 2 handoff evidence does not match its source claim-evidence link')
            if claim_id not in claim_revision_ids:
                raise CompanyResearchWorkspaceDataError('Stage 2 handoff evidence references a claim outside the frozen handoff')
        projected.append({'handoff_kind': kind, 'handoff_link_id': str(_required_uuid(row, 'handoff_link_id')), 'source_link_id': str(source_link_id), 'target_kind': _required_text(row, 'target_kind'), 'target_id': str(target_id), 'claim_revision_id': uuid_text(claim_revision_id), 'evidence_id': uuid_text(evidence_id), 'target_information_date': date_text(target_information_date), 'target_recorded_at_utc': timestamp_text(target_recorded_at), 'recorded_at_utc': timestamp_text(recorded_at)})
    projected.sort(key=lambda item: (item['handoff_kind'], item['source_link_id'], item['target_id']))
    return tuple(projected)

def _frozen_stage1_payload(root: dict[str, Any], handoff_links: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    counts = Counter((item['handoff_kind'] for item in handoff_links))
    return {'candidate_pool': {'candidate_pool_id': str(_required_uuid(root, 'candidate_pool_id')), 'pool_key': _required_text(root, 'candidate_pool_key'), 'created_at_utc': timestamp_text(_required_datetime(root, 'candidate_pool_created_at_utc'))}, 'candidate_pool_revision': {'revision_id': str(_required_uuid(root, 'candidate_pool_revision_id')), 'revision_no': _required_int(root, 'candidate_pool_revision_no'), 'title': _required_text(root, 'candidate_pool_title'), 'scope': _required_text(root, 'candidate_pool_scope'), 'selected_map_revision_id': str(_required_uuid(root, 'pool_selected_map_revision_id')), 'information_cutoff_date': date_text(_required_date(root, 'candidate_pool_information_cutoff_date')), 'recorded_at_utc': timestamp_text(_required_datetime(root, 'candidate_pool_recorded_at_utc')), 'supersedes_revision_id': uuid_text(root.get('candidate_pool_supersedes_revision_id'))}, 'membership': {'candidate_pool_membership_id': str(_required_uuid(root, 'candidate_pool_membership_id')), 'recorded_at_utc': timestamp_text(_required_datetime(root, 'membership_recorded_at_utc'))}, 'beneficiary': {'beneficiary_id': str(_required_uuid(root, 'beneficiary_id')), 'source': _required_text(root, 'beneficiary_source'), 'stock_code': _required_text(root, 'beneficiary_stock_code'), 'created_at_utc': timestamp_text(_required_datetime(root, 'beneficiary_created_at_utc'))}, 'beneficiary_revision': {'revision_id': str(_required_uuid(root, 'beneficiary_revision_id')), 'revision_no': _required_int(root, 'beneficiary_revision_no'), 'beneficiary_kind': _required_text(root, 'beneficiary_kind'), 'assessment_status': _required_text(root, 'beneficiary_assessment_status'), 'rationale_summary': _required_text(root, 'beneficiary_rationale_summary'), 'selected_map_revision_id': str(_required_uuid(root, 'beneficiary_selected_map_revision_id')), 'stock_basic_record_id': _required_int(root, 'beneficiary_stock_basic_record_id'), 'information_cutoff_date': date_text(_required_date(root, 'beneficiary_information_cutoff_date')), 'recorded_at_utc': timestamp_text(_required_datetime(root, 'beneficiary_recorded_at_utc')), 'supersedes_revision_id': uuid_text(root.get('beneficiary_supersedes_revision_id'))}, 'selected_map_revision': {'revision_id': str(_required_uuid(root, 'selected_map_revision_id')), 'revision_no': _required_int(root, 'map_revision_no'), 'title': _required_text(root, 'map_revision_title'), 'scope': _required_text(root, 'map_revision_scope'), 'information_cutoff_date': date_text(_required_date(root, 'map_information_cutoff_date')), 'recorded_at_utc': timestamp_text(_required_datetime(root, 'map_recorded_at_utc')), 'supersedes_revision_id': uuid_text(root.get('map_supersedes_revision_id'))}, 'stock': {'stock_basic_record_id': _required_int(root, 'stock_basic_record_id'), 'stock_name': _required_text(root, 'stock_name'), 'exchange': _required_text(root, 'exchange', allow_empty=True), 'provider_industry': _required_text(root, 'provider_industry', allow_empty=True), 'listing_date': date_text(root.get('listing_date')), 'status': _required_text(root, 'stock_status'), 'source': _required_text(root, 'source')}, 'ingestion_run': {'ingestion_run_id': _required_int(root, 'ingestion_run_id'), 'series_key': _required_text(root, 'ingestion_series_key'), 'provider': _required_text(root, 'ingestion_provider'), 'dataset': _required_text(root, 'ingestion_dataset'), 'information_cutoff_date': date_text(_required_date(root, 'ingestion_information_cutoff_date')), 'completed_at_utc': timestamp_text(_required_datetime(root, 'ingestion_completed_at_utc'))}, 'handoff': {'assertion_count': counts['assertion'], 'claim_count': counts['claim'], 'evidence_count': counts['evidence'], 'links': handoff_links}}

def _aggregate_evidence_summary(module_payloads: dict[str, tuple[dict[str, Any], ...]]) -> dict[str, Any]:
    grades: Counter[str] = Counter()
    conflicts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    by_module: dict[str, dict[str, Any]] = {}
    for module, items in module_payloads.items():
        module_grades: Counter[str] = Counter()
        module_conflicts = 0
        module_missing = 0
        for item in items:
            summary = item['latest_revision']['evidence_summary']
            module_grades.update(summary['evidence_grade_counts'])
            module_conflicts += summary['conflict_count']
            module_missing += summary['missing_evidence_count']
            conflicts.extend(({'module': module, 'item_id': item[MODULE_ID_FIELDS[module]], **entry} for entry in summary['conflicts']))
            missing.extend(({'module': module, 'item_id': item[MODULE_ID_FIELDS[module]], **entry} for entry in summary['missing_evidence']))
        grades.update(module_grades)
        by_module[module] = {'evidence_grade_counts': {grade: module_grades[grade] for grade in ('A', 'B', 'C', 'D')}, 'conflict_count': module_conflicts, 'missing_evidence_count': module_missing}
    conflicts.sort(key=lambda item: (item['module'], item.get('claim_revision_id', ''), item.get('evidence_id', '')))
    missing.sort(key=lambda item: (item['module'], item.get('claim_key', ''), item.get('claim_revision_id', '')))
    return {'evidence_grade_counts': {grade: grades[grade] for grade in ('A', 'B', 'C', 'D')}, 'conflict_count': len(conflicts), 'missing_evidence_count': len(missing), 'conflicts': tuple(conflicts), 'missing_evidence': tuple(missing), 'by_module': by_module}

def _empty_evidence_summary() -> dict[str, Any]:
    return {'claim_count': 0, 'evidence_count': 0, 'evidence_grade_counts': {grade: 0 for grade in ('A', 'B', 'C', 'D')}, 'conflict_count': 0, 'missing_evidence_count': 0, 'conflicts': (), 'missing_evidence': ()}

def _research_revision_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {'revision_id': str(_required_uuid(row, 'revision_id')), 'revision_no': _required_int(row, 'revision_no'), 'workflow_state': _required_text(row, 'workflow_state'), 'conclusion_status': _required_text(row, 'conclusion_status'), 'research_question': _required_text(row, 'research_question'), 'summary': row.get('summary'), 'information_cutoff_date': date_text(_required_date(row, 'information_cutoff_date')), 'recorded_at_utc': timestamp_text(_required_datetime(row, 'recorded_at_utc')), 'supersedes_revision_id': uuid_text(row.get('supersedes_revision_id'))}

def _verification_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {'verification_item_id': str(_required_uuid(row, 'verification_item_id')), 'company_research_revision_id': str(_required_uuid(row, 'company_research_revision_id')), 'item_no': _required_int(row, 'item_no'), 'description': _required_text(row, 'description'), 'status': _required_text(row, 'status'), 'due_date': date_text(row.get('due_date')), 'recorded_at_utc': timestamp_text(_required_datetime(row, 'recorded_at_utc'))}

def _validate_revision_history(rows: Iterable[dict[str, Any]], label: str) -> None:
    revision_ids: set[UUID] = set()
    revision_numbers: set[int] = set()
    for row in rows:
        revision_id = _required_uuid(row, 'revision_id')
        revision_no = _required_int(row, 'revision_no')
        if revision_id in revision_ids or revision_no in revision_numbers:
            raise CompanyResearchWorkspaceDataError(f'{label} contains an incompatible duplicate revision')
        revision_ids.add(revision_id)
        revision_numbers.add(revision_no)

def _revision_sort_key(row: dict[str, Any]) -> tuple[int, datetime, str]:
    return (_required_int(row, 'revision_no'), _required_datetime(row, 'recorded_at_utc'), str(_required_uuid(row, 'revision_id')))

def _json_value(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return timestamp_text(value)
    if isinstance(value, date):
        return date_text(value)
    return value

def _required_uuid(row: dict[str, Any], field: str) -> UUID:
    value = row.get(field)
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise CompanyResearchWorkspaceDataError(f'required UUID field {field} is unavailable') from exc

def _required_date(row: dict[str, Any], field: str) -> date:
    value = row.get(field)
    if not isinstance(value, date) or isinstance(value, datetime):
        raise CompanyResearchWorkspaceDataError(f'required date field {field} is unavailable')
    return value

def _required_datetime(row: dict[str, Any], field: str) -> datetime:
    value = row.get(field)
    if not isinstance(value, datetime):
        raise CompanyResearchWorkspaceDataError(f'required UTC field {field} is unavailable')
    return value

def _required_text(row: dict[str, Any], field: str, *, allow_empty: bool=False) -> str:
    value = row.get(field)
    if not isinstance(value, str) or (not allow_empty and (not value.strip())):
        raise CompanyResearchWorkspaceDataError(f'required text field {field} is unavailable')
    return value

def _required_int(row: dict[str, Any], field: str) -> int:
    value = row.get(field)
    if not isinstance(value, int) or isinstance(value, bool):
        raise CompanyResearchWorkspaceDataError(f'required integer field {field} is unavailable')
    return value

def _required_nonnegative_int(row: dict[str, Any], field: str) -> int:
    value = _required_int(row, field)
    if value < 0:
        raise CompanyResearchWorkspaceDataError(f'count field {field} cannot be negative')
    return value

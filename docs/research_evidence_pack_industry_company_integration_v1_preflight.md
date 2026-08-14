# Research Evidence Pack → Industry Research / Company Research Ordinary-User Integration v1

## Strict Architecture Preflight

### Status

```text
issue = #295
roadmap = #137
base = main@a3f3eab66cd9f75ae66ac4702963b1d31527b830
risk_tier = Strict Architecture Preflight
implementation_authorized = false
schema_or_owner_amendment_authorized = false
preflight_outcome = blocked_exact_case_revision_binding_missing_owner_amendment_required
```

This document answers one question: can the accepted `aquantai.research-evidence-pack.v1` read contract be integrated into the ordinary Industry Research result and Company Research workspace **without inventing research context authority that current accepted owners do not persist?**

The answer on the exact base above is **no**.

---

## 1. Product objective

The user should eventually be able to read an accepted industry/company research result and understand the evidence behind it without seeing internal database mechanics first.

Target navigation:

```text
结论 / 受益公司 / 公司研究判断
  -> 证据状态
  -> Claim 与 Evidence
  -> supports / contradicts / context
  -> 是否属于本次冻结的 Case Revision
  -> 官方 PDF 来源与页码（如有）
```

The integration is explanatory and read-only. It may not:

- accept Evidence automatically;
- create or rewrite Research Case state;
- rewrite Industry Thesis or Company Research history;
- recompute Investment Candidate state;
- call Provider/network/OCR/AI;
- create recommendation, target price, portfolio or trading behavior.

---

## 2. Accepted authority inventory

### 2.1 Evidence Ledger and Research Case

`industry_alpha/models.py` owns:

```text
ResearchCase
ResearchCaseRevision
EvidenceItem
Claim
ClaimRevision
ClaimEvidenceLink
CaseRevisionClaimLink
VerificationItem
```

`ResearchCaseRevision.id` is the authoritative exact research snapshot identity. `CaseRevisionClaimLink` decides which exact `ClaimRevision` rows are part of that exact Case Revision and their role (`conclusion`, `context`, `risk`).

Evidence belongs to a `ResearchCase` through `EvidenceItem.case_id`; a Case identity alone does **not** select a Case Revision.

### 2.2 Research Evidence Pack v1

Accepted architecture/implementation:

```text
Issue #288 / PR #289
Issue #290 / PR #294
contract = aquantai.research-evidence-pack.v1
```

The request requires both:

```text
research_case_id
research_case_revision_id
information_cutoff_date
recorded_at_utc
```

The service deliberately rejects hidden latest/name/ticker/similarity inference. It distinguishes per-Claim-binding membership:

```text
linked_to_selected_case_revision
accepted_unlinked_to_selected_case_revision
```

It also replays local-document receipt/citation integrity fail-closed. Therefore a future UI must not create a second, weaker provenance interpretation.

### 2.3 Industry Map and Stage 1

`industry_alpha/chain_map_models.py` persists `IndustryMap.case_id` and exact map revisions plus assertion→ClaimRevision links.

`industry_alpha/stage1_models.py` persists:

```text
Stage1Beneficiary.case_id
Stage1Beneficiary.map_id
Stage1BeneficiaryRevision.selected_map_revision_id
Stage1BeneficiaryClaimLink.claim_revision_id
Stage1CandidatePool.case_id
Stage1CandidatePool.map_id
Stage1CandidatePoolRevision.selected_map_revision_id
```

This freezes exact Case identity, Map identity/revision, beneficiary revision and ClaimRevision identities. It does **not** freeze `ResearchCaseRevision.id`.

A set of Claims or a selected Map Revision is not a valid substitute for one Case Revision. More than one Case Revision may exist for the same Case and may share Claims while differing in membership, role, chronology, summary or conclusion status.

### 2.4 Stage 2 Company Research

`industry_alpha/stage2_models.py` persists an exact frozen Stage-1 handoff:

```text
Stage2CompanyResearch.case_id
Stage2CompanyResearch.map_id
candidate_pool_revision_id
candidate_pool_membership_id
beneficiary_revision_id
selected_map_revision_id
stock_basic_record_id
```

It also persists exact Claim/Evidence links for the handoff and module revisions, including Company Research hypotheses and their Claim/Evidence links.

`Stage2CompanyResearchRevision` freezes the Company Research revision itself, its cutoff and recorded chronology. It does **not** carry or link to `ResearchCaseRevision.id`.

`industry_alpha/company_research_workspace_query.py` correctly validates exact Stage-1 identities and exact Claim/Evidence links, but it cannot manufacture Case-Revision membership semantics because no Case Revision owner binding exists in the Stage-2 graph.

### 2.5 Industry Thesis accepted output

`industry_alpha/industry_thesis_owner_acceptance_query.py` returns an accepted output containing:

```text
output_link_revision_id
reviewed_session_revision_id
accepted_session_revision_id
research_case_id
industry_map_id
industry_map_revision_id
accepted_candidate_pool_revision_id
ordered beneficiary/semantic bindings
information_cutoff_date
recorded_at_utc
```

`industry_alpha/industry_research_result_query.py` uses that exact accepted output, exact Map Revision, exact complete-beneficiary graph, optional explicit candidate snapshot and exact Company Research downstream revisions.

The accepted output does **not** include `research_case_revision_id`.

This is decisive: the Industry Research result knows the Case identity, but it does not know which exact Case Revision the user is supposed to use as the Evidence Pack membership anchor.

---

## 3. Why current read-only integration is unsafe

A tempting implementation could query all Case Revisions for `research_case_id` and pick one. Every such selector changes accepted research meaning.

The following are prohibited:

```text
latest visible Case Revision
max(revision_no)
Case Revision with maximum matching Claims
only Case Revision currently reachable
nearest information_cutoff_date
nearest recorded_at_utc
Case Revision sharing the accepted Map
Case Revision sharing the largest Stage-1/Stage-2 Claim set
```

These are not equivalent to an explicit owner decision.

Example failure mode:

```text
Case C
  Revision R1 = Claims A + B
  Revision R2 = Claims A + B + C

Industry Thesis output O was accepted while R1 represented the reviewed research state,
but O stores only Case C.

A later read that chooses latest(R2) silently reinterprets historical output O.
```

This violates exact history reopen and the existing Research Evidence Pack contract.

The same problem exists for Company Research. A Company Research revision may remain historically valid while the surrounding Research Case later gains a new revision. Selecting a newer Case Revision would silently change which Claims are considered linked/unlinked to that Company Research context.

---

## 4. Preflight outcome

The required Issue #295 outcome is:

```text
B. blocked_exact_case_revision_binding_missing_owner_amendment_required
```

Therefore **no production integration allowlist is activated by this preflight**.

The current accepted model cannot safely implement:

```text
Industry Research result -> exact Evidence Pack
Company Research workspace -> exact Evidence Pack
```

because the exact `research_case_revision_id` input is not owned by either accepted context.

---

## 5. Smallest future owner/schema amendment candidate

A future, separately authorized Strict amendment should add explicit append-only bindings rather than nullable inferred columns or historical backfill.

### 5.1 Industry Thesis accepted-output binding

Candidate owner:

```text
IndustryThesisOutputCaseRevisionBinding
```

Candidate persistence meaning:

```text
output_link_revision_id -> research_case_revision_id
```

Required invariants:

1. `output_link_revision_id` references exactly one accepted `IndustryThesisOutputLinkRevision`.
2. one authoritative binding exists at most once per output revision;
3. bound Case Revision belongs to the same `research_case_id` already frozen by the output;
4. bound Case Revision is visible inside the output's `information_cutoff_date` and `recorded_at_utc` boundary;
5. binding is created atomically by the accepted-output owner transaction for newly accepted outputs;
6. binding is append-only and immutable;
7. no later read may replace it with a newer Case Revision.

### 5.2 Company Research revision binding

Candidate owner:

```text
Stage2CompanyResearchRevisionCaseBinding
```

Candidate persistence meaning:

```text
company_research_revision_id -> research_case_revision_id
```

The binding belongs at **Company Research revision** level rather than Company Research identity level because Company Research history may evolve while the Case also evolves. Historical reopen must preserve the exact context for each revision.

Required invariants:

1. one authoritative Case Revision binding at most once per Company Research revision;
2. bound Case Revision belongs to `Stage2CompanyResearch.case_id`;
3. Case Revision is visible inside the Company Research revision's cutoff/recorded boundary;
4. binding is emitted atomically with the authoritative Company Research revision transaction for new revisions;
5. append-only and immutable;
6. no automatic rebinding when a newer Case Revision appears.

### 5.3 Why two explicit binding owners are preferred

A generic polymorphic `research_context_binding(target_type, target_id, ...)` would weaken database referential integrity and create a new generic owner abstraction not otherwise needed by P0.

Two narrow link tables preserve direct foreign keys and make ownership explicit.

Adding direct non-null columns to existing owner tables would require historical values. Those values cannot be safely backfilled from current data because the whole problem is that no exact historical Case Revision decision was persisted.

Therefore the candidate amendment should use **new append-only link rows with no heuristic backfill**.

---

## 6. Legacy behavior

Existing accepted output and Company Research revisions on `main@a3f3eab...` are legacy-unbound with respect to exact Case Revision context.

A future amendment must not guess historical bindings.

Required legacy state:

```text
evidence_context_binding = unavailable
reason = exact_case_revision_binding_not_persisted
```

Ordinary UI wording candidate:

```text
证据上下文未冻结，无法安全判断“是否已纳入本次研究修订”。
可查看现有研究结论，但不能把当前或最新 Case Revision 当作历史依据。
```

If the product later needs to attach a legacy result to a Case Revision, that must be an explicit user-reviewed append-only acceptance action in a separately designed workflow. It is not part of this preflight.

---

## 7. Future integration boundary after the binding amendment is accepted

The eventual integration should reuse existing owners rather than merge them.

### Industry Research

Authority chain:

```text
exact IndustryThesisOutputLinkRevision
-> exact IndustryThesisOutputCaseRevisionBinding
-> exact ResearchCaseRevision
-> Research Evidence Pack v1
```

Existing beneficiary and explained-result projections remain authoritative for product/chain/company/candidate meaning. Evidence Pack adds evidence explanation only.

### Company Research

Authority chain:

```text
exact Company Research revision selected by workspace/history semantics
-> exact Stage2CompanyResearchRevisionCaseBinding
-> exact ResearchCaseRevision
-> Research Evidence Pack v1
```

Existing module Claim/Evidence links remain authoritative for which Claims/Evidence belong to hypotheses, expectations, valuation observations, catalysts, risks and judgments. Evidence Pack remains authoritative for selected-Case-Revision membership and local-document provenance integrity.

### No duplicate provenance engine

A future UI/detail service may index/filter an already validated Evidence Pack by exact ClaimRevision IDs owned by Stage 1/Stage 2. It may not recreate a weaker local-document receipt validator or infer provenance from source locator/title/path.

---

## 8. Ordinary-user semantics to preserve

Once an exact binding exists, the UI may summarize evidence with Chinese-first states such as:

```text
已纳入本次研究证据
存在已接受但尚未纳入本次修订的证据
存在矛盾证据
暂无已接受证据
证据上下文未冻结
证据完整性异常
```

Technical detail can expose exact IDs, cutoff, recorded UTC, hashes, membership state and receipt/citation metadata.

Important separation:

```text
Evidence Pack state != research conclusion state
Evidence Pack state != candidate status
new Evidence != automatic research rewrite
accepted-unlinked Evidence != rejected Evidence
contradicting Evidence != automatic conclusion reversal
```

The user may inspect evidence and later choose an explicit research-review action, but this integration itself performs no acceptance or recomputation.

---

## 9. Historical and dual-as-of contract

The future integration must preserve the exact boundaries already accepted by both research and Evidence Pack owners.

For one historical accepted output or Company Research revision:

- its exact Case Revision binding never changes;
- Evidence/Claim rows outside requested information cutoff are invisible;
- rows recorded after requested `recorded_at_utc` are invisible;
- a newer Case Revision cannot replace the bound revision;
- a newer Company Research revision cannot replace an explicitly reopened older revision;
- a hidden supersession target remains represented only according to the existing Evidence Pack visibility contract;
- corrupted present provenance fails the Evidence Pack detail closed.

---

## 10. Query/performance direction

Because this preflight is blocked before implementation, it does not authorize a new query budget. It freezes these requirements for the later integration design:

1. no per-beneficiary Evidence Pack query loop;
2. no per-module receipt/citation query loop;
3. binding lookup must be set-wise/bounded;
4. Evidence Pack detail remains paginated and request-bound;
5. summary rendering must not silently truncate evidence and then claim complete coverage;
6. ordinary result rendering must remain usable when evidence detail is not expanded;
7. zero writes during GET/read projection;
8. zero external network/OCR/AI in evidence display.

A later integration preflight/implementation must state an exact SQL ceiling after the binding owner amendment is accepted.

---

## 11. Future amendment scope candidate — inactive

This is **not an implementation allowlist**. It is the smallest owner/schema family that a separate Strict amendment should inspect:

```text
industry_alpha/industry_thesis_models.py
industry_alpha/industry_thesis_owner_acceptance_*.py
industry_alpha/stage2_models.py
Stage2 Company Research command/write owner files
backend/database / Alembic migration files required for two append-only binding tables
focused migration/owner tests
```

The amendment must inventory exact write owners before freezing file paths. It may discover that existing commands need a dedicated preview/commit expected-context field so the user-reviewed exact Case Revision is part of deterministic fingerprints.

No amendment file is authorized by Issue #295.

---

## 12. Future integration file direction — inactive

Only after an accepted exact-binding amendment exists should a new implementation Issue consider read/UI files such as:

```text
industry_alpha/industry_research_result_*.py
industry_alpha/company_research_workspace_*.py
industry_alpha/research_evidence_pack_*.py
backend/api/industry_analysis.py
backend/api/company_research.py
industry_analysis/static/accepted_result.*
Company Research ordinary-user static/UI files if present and required
focused integration tests and zero-write demos
```

The future implementation allowlist must be re-derived from then-current exact `main`; this list does not pre-authorize those files.

---

## 13. Stop conditions

Stop and return to the project owner if any future work would:

- infer or backfill Case Revision identity;
- relax Research Evidence Pack exact selectors;
- add a second provenance/receipt authority;
- modify accepted history in place;
- auto-accept new Evidence or Claims;
- auto-recompute research/candidate conclusions from displayed evidence;
- require Provider/network/OCR/AI for ordinary evidence display;
- add recommendation/portfolio/trading behavior;
- change files beyond an explicitly frozen future Issue allowlist.

---

## 14. Governance gate for this architecture PR

This preflight PR must contain exactly:

```text
.codex/tasks/issue-295-research-evidence-pack-industry-company-integration-v1-preflight.md
docs/research_evidence_pack_industry_company_integration_v1_preflight.md
```

It remains Draft. Merge consideration requires:

```text
exact immutable HEAD
applicable CI = success
fresh fixed-HEAD architecture review = zero blockers
unresolved review threads = 0
separate project-owner merge authorization
```

Required review phrase:

```text
AUTHORIZED RESEARCH EVIDENCE PACK INDUSTRY/COMPANY ORDINARY-USER INTEGRATION V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Merging this document would authorize neither the two binding owners nor production ordinary-user integration.
# Issue #295 — Research Evidence Pack → Industry/Company Research Ordinary-User Integration v1 — Strict Architecture Preflight

## Authority

Project-owner instruction on 2026-08-14:

> 关闭 Issue #290，然后从当前精确 main@a3f3eab66cd9f75ae66ac4702963b1d31527b830 重新同步 Roadmap #137。进入：Research Evidence Pack → Industry Research / Company Research ordinary-user integration

Exact architecture base:

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
base = main@a3f3eab66cd9f75ae66ac4702963b1d31527b830
issue = #295
roadmap = #137
risk_tier = Strict Architecture Preflight
implementation_authorized = false
```

## Scope

This task may change only:

```text
.codex/tasks/issue-295-research-evidence-pack-industry-company-integration-v1-preflight.md
docs/research_evidence_pack_industry_company_integration_v1_preflight.md
```

No production code, API/UI implementation, tests, fixtures, workflow, dependency, schema, migration, Provider/network/OCR/AI, automatic acceptance, recommendation, portfolio, trading, release, tag or version changes are authorized.

## Owner inventory conclusion

Accepted main currently proves:

```text
ResearchCaseRevision is the authoritative Evidence Pack snapshot anchor.
Research Evidence Pack requires explicit research_case_id + research_case_revision_id.
IndustryThesisOutputLinkRevision freezes research_case_id, exact accepted map revision and accepted candidate-pool/member graph, but not research_case_revision_id.
Stage1 beneficiary/candidate-pool owners freeze case_id/map_id/map_revision/ClaimRevision identities, but not research_case_revision_id.
Stage2 Company Research freezes case_id/map_id/Stage-1 identities and exact Claim/Evidence links, but not research_case_revision_id.
```

Therefore no accepted owner graph supplies an explicit exact Research Case Revision for the proposed ordinary-user integration.

## Prohibited inference

The integration may not choose a Case Revision by:

```text
latest
max revision_no
maximum coverage
unique reachable revision
nearest cutoff
same map
same company
same Claim set
```

No read-layer heuristic may substitute for a frozen owner binding.

## Required preflight outcome

```text
outcome = blocked_exact_case_revision_binding_missing_owner_amendment_required
```

Pure read-only integration is not authorized from the current model because it cannot bind the Industry/Company Research context to the exact Case Revision required by `aquantai.research-evidence-pack.v1`.

## Smallest future amendment candidate

A later, separately authorized Strict owner/schema amendment should prefer explicit append-only binding rows over inferred or backfilled columns:

```text
Industry Thesis accepted output revision
  -> exact Research Case Revision

Company Research revision
  -> exact Research Case Revision
```

Candidate constraints:

- exact foreign keys to both owner revision and `research_case_revisions.id`;
- one authoritative binding per bound owner revision;
- bound Case Revision must belong to the same `case_id`;
- Case Revision must be visible inside the bound owner's information/recorded boundary;
- binding is append-only/immutable;
- binding is emitted atomically by the authoritative owner transaction for new owner revisions;
- legacy rows remain explicitly unbound; no latest/max/coverage backfill;
- unbound or ambiguous context fails closed in the future ordinary-user evidence integration.

The detailed preflight document freezes the rationale and future integration boundary.

## Future ordinary-user contract after a valid binding exists

The intended product flow remains:

```text
accepted Industry Research / Company Research context
  -> exact frozen Case Revision binding
  -> existing Research Evidence Pack integrity/provenance contract
  -> compact Chinese evidence state
  -> on-demand Claim/Evidence/PDF citation detail
```

Evidence Pack remains a read/explanation layer. It never automatically rewrites accepted research, accepts evidence, recomputes candidates or triggers network/AI work.

## Governance

The architecture PR must remain Draft. Merge consideration requires one immutable HEAD, applicable green CI, fresh fixed-HEAD architecture review with zero blockers, unresolved review threads = 0, and separate project-owner merge authorization.

Required review phrase:

```text
AUTHORIZED RESEARCH EVIDENCE PACK INDUSTRY/COMPANY ORDINARY-USER INTEGRATION V1 PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Merging this preflight would not authorize the owner/schema amendment or production integration.
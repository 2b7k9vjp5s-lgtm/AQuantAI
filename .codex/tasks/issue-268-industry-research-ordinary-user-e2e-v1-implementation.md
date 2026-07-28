# Issue #268 Task Snapshot — Industry Research Ordinary-User End-to-End Completion v1

## Authority

Project-owner instruction on 2026-07-28:

```text
继续下一步开发
```

Authoritative state:

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
base_branch = main
exact_base = b519f418fa82837e103e8a92a62720de33741524
architecture_issue = #266 / closed / completed
architecture_pr = #267 / merged
implementation_issue = #268
branch = feat/industry-research-ordinary-user-e2e-v1
risk_tier = Strict Implementation
workflow = .codex/WORKFLOW.md
```

PR #241 remains closed, Draft, unmerged, permanently frozen and read-only at
`3116a67ec472131eea3bf3d1bd9daee884c69ee9`.

## Objective

Close the two remaining deterministic end-to-end gaps:

1. add one server-owned canonical fingerprint over the complete commit-relevant
   Owner Acceptance View body and require it in Preview and Commit;
2. return an exact accepted-result continuation for
   `workflow_state = accepted_outputs_linked` from the history API.

The implementation reuses the existing Owner Context v2, owner-acceptance core,
accepted output assembly, complete beneficiary universe and optional exact
Investment Candidate overlay. It introduces no new persistence owner.

## Exact authorized files

```text
.codex/tasks/issue-268-industry-research-ordinary-user-e2e-v1-implementation.md
industry_alpha/industry_research_e2e_rules.py
backend/api/industry_analysis.py
backend/api/industry_analysis_acceptance.py
industry_analysis/static/owner_acceptance.js
tests/test_industry_analysis_acceptance_v2_api.py
tests/test_industry_analysis_phase2b.py
tests/test_industry_analysis_acceptance_v2_static.py
scripts/demo_industry_research_ordinary_user_e2e_v1.py
.github/workflows/local-tests.yml
```

No other file is authorized.

## Locked contracts

```text
snapshot_contract_version =
  aquantai.industry-thesis-owner-acceptance-view-snapshot.v1
```

The canonical snapshot includes:

```text
reviewed_session_revision_id
expected_session_latest_revision_number
reviewed_plan_fingerprint_sha256
owner_context
information_cutoff_date
owner_acceptance_plan_version
ordered members and complete exact options
candidate_pool_operation_contract
output_metadata_defaults
```

Canonical JSON uses UTF-8, `ensure_ascii=false`, sorted object keys, compact
separators and preserved list order. The SHA-256 is lowercase hexadecimal.

Preview and Commit both require the server-issued snapshot contract version and
content fingerprint. Commit also requires the existing preview fingerprint.

A current-view mismatch returns:

```text
code = industry_research_e2e_snapshot_body_mismatch
status = 409
message = 接受页面内容已变化，不能使用旧预览提交。
recovery = 保留填写内容并重新读取接受页面，再次预览。
```

The history continuation for an accepted revision is:

```text
kind = accepted_result
label = 查看已接受成果
reason_code = exact_accepted_outputs_linked
```

The path uses only the response-owned session ID, exact accepted session revision
ID and dual-as-of boundaries. It performs no lookup, write, candidate selection
or fallback.

## Validation

Required proof:

- stable repeated acceptance-view fingerprint;
- strict request DTOs require the fingerprint fields;
- member/options/default-body replacement with unchanged top-level IDs fails
  before owner writes;
- stale hash invalidates a prior preview;
- valid three-company Preview/Commit still succeeds once;
- zero-supported complete result remains unchanged;
- accepted history continuation is exact and dual-as-of bound;
- static JavaScript sends but never calculates the authoritative hash;
- focused tests, full pytest and all configured zero-network demos pass on one
  immutable HEAD.

## Locked exclusions

No schema, migration, dependency, Provider, network, credential, AI,
recommendation, portfolio, trading, scheduler, notification, release, tag or
version work. Do not update architecture baselines. Do not modify PR #241.

## Delivery gates

- one Draft PR linked to #268, #266/#267 and #137;
- exact Base-to-HEAD inventory inside the ten authorized files;
- `behind = 0`;
- exact-head CI success;
- fixed-head independent review containing exactly:

```text
AUTHORIZED INDUSTRY RESEARCH ORDINARY-USER END-TO-END V1 IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>
```

- zero unresolved review threads;
- separate project-owner authorization before Ready/merge.

Any new commit invalidates prior exact-head CI and review evidence.
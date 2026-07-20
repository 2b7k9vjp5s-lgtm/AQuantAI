# Issue #140 — Industry Beneficiary Workspace Architecture Preflight

## Authority

- GitHub Issue: #140
- Related roadmap: #137
- Merged predecessor: PR #139 / Issue #138
- Base commit: `3a8b74a5ef76bd34092ff96985bae0d3d2733c8f`
- Branch: `agent/issue-140-industry-beneficiary-workspace-preflight`
- Work type: Architecture Preflight, documentation only
- Released version remains `0.2.0`; merged capability remains v0.6D plus the read-only Evidence Intelligence product slice

## Objective

Define the smallest useful, existing-contract Industry Beneficiary Workspace that lets a local user inspect one selected industry map and the complete cutoff-visible persisted Stage 1 beneficiary set before any valuation or market-pricing filter, while preserving exact classification, revision, cutoff, provenance, conflicts, missing evidence and non-advisory meaning.

## Allowed files

1. `.codex/tasks/issue-140-industry-beneficiary-workspace-preflight.md`
2. `docs/industry_beneficiary_workspace_preflight.md`

No other file may change.

## Required decisions

- Separate fields that already have authoritative persisted owners from requested fields that do not exist.
- Preserve exact `direct / secondary / potential` Stage 1 values; no mapping to `direct / conditional / indirect / conceptual`.
- State whether existing Stage 1 beneficiary classification is displayed as D3 analytical research state because no general D2 rule version or analyst-owner field is persisted.
- Define a 2A Product Task candidate using existing accepted contracts only.
- Define 2B as a later Architecture Task for any new taxonomy, rule ownership, typed driver subtype or typed customer/certification/capacity/order-stage semantics.
- Define initial-load and explicit detail-load paths without N+1 graph loading.
- Define exact cutoff, frozen-revision, chronology, evidence, conflict and missing-data rules.
- Define one production-realistic offline golden path and one primary failure path.
- Define candidate implementation files, tests, exclusions and stop conditions after independent DoR approval.

## Locked exclusions

- no application code, API, UI, test or fixture changes;
- no schema or migration;
- no Provider or external network path;
- no new classification or renamed beneficiary taxonomy;
- no inference from stock code, provider name or free text;
- no valuation, score, ranking, recommendation, target price, expected return or signal;
- no canonical price or comparison eligibility;
- no release, tag or version change.

## Validation

```bash
git diff --check
git diff --name-only 3a8b74a5ef76bd34092ff96985bae0d3d2733c8f...HEAD
```

The changed-file inventory must contain exactly the two allowed files. Keep the PR Draft/Open/unmerged for independent fixed-head Definition-of-Ready review. Do not create the implementation Issue before that review is approved.

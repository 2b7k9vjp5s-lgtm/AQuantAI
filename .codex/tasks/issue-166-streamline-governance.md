# Issue 166 — Streamline Repository Governance

## Authority

- GitHub Issue: #166
- Required base: `13099ce1988dec05eaf674732fce3acb7f5fa080`
- Work type: governance/documentation reset
- Owner authorization: explicit chat approval on 2026-07-21

## Objective

Replace the uniform heavy workflow with risk-tiered governance that accelerates low-risk and standard delivery while preserving strict review for schema, external-data, AI-write, identity, destructive-history and investment-decision changes.

## Authorized files

1. `.codex/WORKFLOW.md`
2. `.codex/tasks/issue-166-streamline-governance.md`

No production code, schema, migration, API, UI, test, fixture, Provider, dependency, release or version change is authorized.

## Required result

- Light work: Issue/task snapshot optional; branch/PR/targeted validation/owner-authorized merge.
- Standard work: one Issue and one implementation PR; architecture decisions stay in the Issue/PR; one focused review.
- Strict work: architecture note plus implementation PR; one independent fixed-head architecture review and one independent fixed-head implementation review.
- Strict triggers are explicit and narrow.
- Consolidation is signal-based or after 5–6 implemented slices, not every two.
- Directory/file-family authorization is allowed for implementation.
- Documentation-only changes use documentation checks unless executable contracts are affected.
- Owner authorization remains mandatory for merge, release, version change and next-roadmap start.
- Existing local-first, no-hidden-network, provenance, cutoff, revision, secret and non-advisory rules remain unchanged.

## Transition rule

PR #165 may remain Draft/Open while implementation begins after owner authorization. Its independent architecture approval is still required before any Typed Beneficiary Evidence Semantics production PR is merged.

## Validation

- Confirm base-to-head changes exactly the two authorized files.
- Confirm the workflow retains explicit fail-closed and research-integrity rules.
- Run repository checks triggered by the PR.
- Record exact base/head and validation in the PR.

## Completion

The owner has authorized merge after author-side verification and passing checks. Close Issue #166 after merge.
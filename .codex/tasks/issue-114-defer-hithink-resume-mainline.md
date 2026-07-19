# Issue #114 - Defer Hithink and Resume ORM Lifecycle Mainline

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: #114
- Base and required ancestor: `ca2a9fa0ca4daea6b7318a50851272b74c4dc115`
- Branch: `docs/defer-hithink-resume-mainline`
- Work type: documentation/status synchronization only
- Released version remains `0.2.0`; merged capability remains v0.6D.
- Accepted application/consolidation implementation baseline remains `cf3ad09c9f9fb39dbaada7342435a8c7b2853b1a`.
- Migration decision: no migration.

## Objective

Record the account owner's decision to defer Hithink integration, preserve the accepted provider characterization as future reference, and restore ORM lifecycle characterization as the next independent project gate.

## Exact authorized files

1. `.codex/tasks/issue-114-defer-hithink-resume-mainline.md`
2. `docs/architecture_baseline.md`
3. `docs/review.md`
4. `docs/roadmap.md`

Do not modify any other path.

## Required edits

1. Keep Issue #108 / PR #109 as the accepted Hithink provider characterization; do not describe it as rolled back.
2. Record that Issue #112 closed as `not planned` and Draft PR #113 closed without merge at reviewed fixed head `b09fcd8e68f4d280407b483a7d114aa0b0e8a015` after the account owner chose to defer integration.
3. State that the seven-file probe implementation passed fixed-head scope/safety review and Actions `29691380530`, but no live probe ran, no API key was used and no live contract, permission or data-use acceptance exists.
4. State that no Hithink code, dependency, runtime/default-provider change, database/schema change or migration reached `main`.
5. Mark Hithink as a deferred future candidate that may be reconsidered only through new Architecture Preflight and explicit authorization.
6. Keep AKShare as the implemented controlled provider path and preserve all provider-specific history.
7. Preserve one provider per ingestion run/canonical series and the prohibitions on silent fallback, relabeling and row-level mixing.
8. Replace `Current documentation head` with a stable status-sync/base label tied to `ca2a9fa0ca4daea6b7318a50851272b74c4dc115`; do not predict this PR's eventual merge SHA.
9. Restore ORM lifecycle characterization as the next gate. It must inventory dynamic link-model factories, append-only listener registration, mapper/event registration, import-order behavior, duplicate listener risk, metadata/model identity, test isolation and supported-database behavior before any implementation decision.
10. Keep canonical market-price evidence, v0.6E and v0.7 later and unauthorized.
11. Preserve released version, capability stage, runtime surfaces and no-migration state.

## Validation

- Confirm the base-to-head diff contains exactly the four authorized files.
- Run `python -m pytest -q`.
- Run `python -m scripts.demo_research_flow`.
- Run `git diff --check`.
- Report exact results and environment-gated skips honestly.

## Locked exclusions

No Hithink/probe/provider code, live request, secret, dependency, environment-template change, AKShare change, ORM/model/listener implementation, database/schema/migration, test/fixture, CI, API/runtime behavior, release/version, v0.6E, v0.7 or PR #38 work.

## Stop gate

Push exactly the four authorized files to the linked Draft PR and keep it Draft/Open/unmerged for independent fixed-head review.
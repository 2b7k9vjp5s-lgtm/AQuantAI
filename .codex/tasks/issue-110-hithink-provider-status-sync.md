# Issue #110 - Hithink Provider Status Sync

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: #110
- Accepted characterization: Issue #108 / PR #109
- Base and required ancestor: `375a8d15b8a4f7ca80fe843fcfd93bccdeaa2d9a`
- Branch: `docs/hithink-provider-status-sync`
- Work type: documentation/status synchronization only
- Released version remains `0.2.0`; merged capability stage remains v0.6D.
- Accepted application/consolidation implementation baseline remains `cf3ad09c9f9fb39dbaada7342435a8c7b2853b1a`.
- Migration decision: no migration.

## Objective

Synchronize authoritative documents after PR #109 so Hithink is recorded as the preferred future A-share provider candidate, AKShare remains an explicit provider-specific alternative, and a credential-safe contract acceptance probe becomes the next independent gate.

## Authorized files

- `.codex/tasks/issue-110-hithink-provider-status-sync.md`
- `docs/architecture_baseline.md`
- `docs/review.md`
- `docs/roadmap.md`

## Required edits

1. Record Issue #108 / PR #109 as the accepted Hithink provider characterization.
2. Distinguish current documentation head `375a8d15b8a4f7ca80fe843fcfd93bccdeaa2d9a` from the unchanged accepted application/consolidation implementation baseline `cf3ad09c9f9fb39dbaada7342435a8c7b2853b1a`.
3. Record Hithink as a preferred future provider candidate, not an active default or implemented provider.
4. Preserve AKShare as an explicit provider-specific alternative and preserve all existing AKShare series/history.
5. State that one ingestion run and canonical series contain one provider only; prohibit silent fallback, provider relabeling and row-level provider mixing.
6. State that canonical ingestion may use reviewed REST or a separately reviewed market-dump importer; MCP/LLM calls are not canonical ingestion.
7. State that no production provider implementation has reached Definition of Ready.
8. Set the next gate to a credential-safe, no-database-write Hithink contract acceptance probe using a user-configured local secret only when executed.
9. Keep ORM lifecycle characterization deferred but not cancelled.
10. Preserve version, capability, runtime surfaces, no-migration state and all product exclusions.

## Validation

- verify the base-to-head diff contains exactly the four authorized files;
- run the full repository workflow and fixture demo;
- run `git diff --check`;
- report exact results and environment limitations honestly.

## Locked exclusions

No provider code, live API request, API key, secret, dependency, environment-template change, database/schema/migration, ingestion script, test/fixture, CI, runtime behavior, release/version, v0.6E, v0.7 or PR #38 work.

## Stop gate

Push the exact four-file docs-only synchronization to the linked Draft PR and keep it Draft/Open/unmerged for independent fixed-head review.
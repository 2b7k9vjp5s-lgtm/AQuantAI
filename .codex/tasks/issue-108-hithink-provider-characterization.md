# Issue #108 - Hithink Primary Provider Characterization

## Authorization

- Repository: `2b7k9vjp5s-lgtm/AQuantAI`
- Issue: #108
- Base and required ancestor: `586fd3e82460aead32537916394c9624b4e6eedd`
- Branch: `docs/hithink-provider-characterization`
- Work type: Architecture Preflight and documentation-only characterization
- Released version remains `0.2.0`; merged capability stage remains v0.6D.
- Migration decision: no migration is authorized by this task.
- No API key or live request is required or authorized.

## Objective

Characterize the official Hithink/Fuyao financial-data service as AQuantAI's preferred future A-share provider candidate while preserving AKShare as an explicit alternative and preserving all existing provider, ingestion, series-identity, cutoff and offline-execution invariants.

## Authorized files

- `.codex/tasks/issue-108-hithink-provider-characterization.md`
- `docs/hithink_provider_characterization.md`

## Required analysis

1. Inventory the existing `DataProvider` contracts for stock identity, daily OHLCV and trade calendar.
2. Inventory the controlled AKShare ingestion protocol, including one provider per run, complete snapshots, immutable attempts, exact scope, provider-specific canonical series identity, cutoff-aware reads and no automatic network access.
3. Map official Hithink REST and market-dump fields to existing normalized contracts without inventing values.
4. Define exact `thscode` parsing and exchange mapping for `.SH`, `.SZ` and `.BJ`; reject name/free-text inference.
5. Separate bounded REST collection, bulk market-dump collection and MCP/agent queries. MCP/LLM calls must not become canonical ingestion.
6. Define response validation for HTTP-200 business errors, request provenance and bounded retry classification.
7. Define market-dump manifest, checksum, row-count, uniqueness, coverage, failed-ticker and short-lived URL handling.
8. Preserve no-network imports, startup, tests, CI and fixture demos.
9. Record point-in-time limits for symbol catalogs, index constituents, financial reports and provider-side revisions.
10. Record account-capability, QPS, SLA, caching, long-term storage, display and redistribution questions that block implementation Definition of Ready.
11. Evaluate complete replacement, silent fallback/mixing and explicit provider-specific coexistence.
12. Decide whether a first implementation candidate can remain source-only and whether REST and bulk dump ingestion require separate implementation Issues.

## Required conclusions

- Hithink may be the preferred provider candidate, but existing AKShare series and ingestion history remain immutable and readable.
- One ingestion run and one canonical series contain one provider only.
- Any fallback is an explicit orchestration decision producing a distinct provider-specific series; no row-level provider mixing or silent fallback is allowed.
- Canonical ingestion uses REST or reviewed market dumps, not MCP or LLM-mediated tool calls.
- The first implementation slice, if later authorized, is limited to existing normalized contracts and unadjusted daily data unless a separate contract review approves more.
- Raw corporate-action events, adjusted-price derivation, financial statements, Hithink concept/industry data, hot lists and index constituents are outside the first implementation slice.
- No implementation Issue may open until exact contracts, account permissions and data-use rights satisfy the recorded Definition of Ready gates.

## Validation

- verify the base-to-head diff contains exactly the two authorized files;
- run the full repository workflow and fixture demo;
- run `git diff --check`;
- report exact results and environment limitations honestly.

## Locked exclusions

No provider implementation, live API request, API key, secret, dependency, environment-template change, database or schema change, migration, ingestion script change, test or fixture change, CI change, runtime behavior change, release/version change, v0.6E, v0.7 or PR #38 work.

## Stop gate

Push exactly the two documentation files to the linked Draft PR and keep it Draft/Open/unmerged for independent review. Do not open an implementation Issue from this branch.
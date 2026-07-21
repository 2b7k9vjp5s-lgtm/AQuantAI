# Issue #152 — Company Research Workspace baseline synchronization

## Authority

- Work type: architecture decision / documentation reset only.
- Required base: `bcc99f20a1486d3d39c737e3fc6d102b940d863e`.
- Branch: `docs/company-research-baseline-sync`.
- Related roadmap: Issue #137.
- Completed implementation: Issue #150 / PR #151.
- Release remains `0.2.0`.

## Objective

Synchronize `docs/architecture_baseline.md` after the independently approved and merged Company Research Workspace v1. The updated baseline must describe accepted runtime state and identify Slice 4 Evidence Ingestion Architecture Preflight as the next roadmap gate.

## Authorized files

1. `docs/architecture_baseline.md`
2. `.codex/tasks/issue-152-company-research-baseline-sync.md`

No other file is authorized.

## Required current-state corrections

- accepted application/product baseline is `bcc99f20a1486d3d39c737e3fc6d102b940d863e`;
- Company Research Workspace v1 is merged and available at `/company-research`;
- its accepted identity is one explicit persisted `company_research_id`;
- selector query count is exactly 3 and selected workspace query count is exactly 14;
- exact frozen Stage 1, stock, ingestion and v0.6A-v0.6D revision provenance remains visible;
- historical downstream revision mismatch remains visible and is not automatically relinked;
- full owning-domain detail remains explicit/on-demand;
- UI is Chinese-first, read-only, safe-DOM and non-advisory;
- Company Research is no longer listed as pending or unimplemented;
- PRs #149 and #151 appear in the accepted sequence;
- only one product/domain slice has completed since consolidation PR #145, so no consolidation pause is required yet.

## Next gate

The next roadmap gate is **Slice 4 Evidence Ingestion Architecture Preflight**.

The preflight must establish, before any implementation task exists:

1. exactly one explicitly authorized official source and its data-use boundary;
2. immutable raw capture ownership and retention;
3. source-specific normalization without Provider mixing or fallback;
4. deterministic fingerprint and deduplication rules;
5. explicit company/industry candidate matching with no silent identity inference;
6. human-review state before accepted EvidenceItem or claim linkage;
7. information time, fetched/imported time and recorded UTC chronology;
8. production-realistic offline golden path and failure path;
9. schema/migration/dependency/network impact;
10. evidence-grade and D0-D3 responsibility boundaries;
11. exact tests, exclusions and stop conditions.

## Locked exclusions

No production code, API, UI, schema, migration, Provider implementation/default, dependency, fixture/test behavior, release/version, live ingestion, external-network access, accepted-source decision, automatic evidence acceptance, AI promotion to D0, evidence-grade assignment, identity inference, ranking, recommendation, monitoring, portfolio or trading change.

This synchronization does not authorize Evidence Ingestion task synchronization or implementation.

## Validation

- base-to-head diff contains exactly the two authorized files;
- architecture baseline contains no stale statement that Company Research is pending;
- runtime surface, capability matrix, debt register and accepted sequence agree;
- next gate is preflight only;
- all shared invariants, Provider isolation and canonical-price no-DoR conclusions remain explicit;
- Draft PR remains open/unmerged pending independent fixed-head review.

# Issue #156 — Defer Evidence Ingestion and open Guarded AI preflight

## Authority

- Work type: architecture decision / documentation reset only.
- Required base: `a945b111cf97fa93d8257d6f5d495a4a842af3f2`.
- Branch: `docs/defer-ingestion-open-guarded-ai`.
- Related roadmap: Issue #137.
- Deferred work: Issue #154 / closed-unmerged PR #155.
- Release remains `0.2.0`.

## Objective

Synchronize `docs/architecture_baseline.md` after the owner decided that manual PDF import is not convenient and approved deferring Evidence Ingestion so it does not block project progress.

The synchronized baseline must preserve the fact that Evidence Ingestion remains unimplemented, retain Issue #154 / PR #155 as design history, and set **Guarded AI Research Assistance Architecture Preflight** as the next gate over existing accepted persisted records only.

## Authorized files

1. `docs/architecture_baseline.md`
2. `.codex/tasks/issue-156-defer-ingestion-open-guarded-ai.md`

No other file is authorized.

## Required baseline changes

- record Issue #154 / PR #155 as deferred and unmerged;
- state that no ingestion production code, schema, migration, dependency or network adapter entered `main`;
- state that manual PDF import is not required for the current product path;
- keep Evidence Ingestion unimplemented and requiring a new explicit restart Architecture Preflight;
- set Guarded AI Research Assistance Architecture Preflight as the next roadmap gate;
- limit the first AI candidate to user-invoked, read-only assistance over existing accepted data;
- preserve exact IDs, revisions, cutoffs and provenance;
- label model output D3 draft assistance rather than D0/D1/D2 accepted state;
- prohibit model-owned evidence acceptance, grading, identity acceptance, deterministic state, ranking, recommendation, alerts, portfolio or trading behavior;
- prohibit hidden browsing, crawling, search or data acquisition;
- require the later preflight to define adapter/model configuration, credentials, privacy, prompt-injection, redaction, cost, timeout, failure and offline-test boundaries;
- preserve Provider isolation, canonical-price no-DoR, non-advisory boundaries and release `0.2.0`.

## Guarded AI next-gate questions

The later preflight must resolve before any implementation:

1. the smallest explicit user job and exact accepted input identity;
2. input-manifest ownership, cutoff and revision freezing;
3. the separation of deterministic source projection and model-generated D3 text;
4. whether outputs are ephemeral or persisted;
5. if persisted, schema, append-only revision, model/adapter/version and prompt-template provenance;
6. explicit human review and discard/accept-for-notes workflow without accepted domain mutation;
7. prompt-injection and untrusted evidence-text handling;
8. redaction and provider data-retention/privacy boundaries;
9. credential storage and error redaction;
10. model allowlist, timeout, token/cost limits and deterministic failure vocabulary;
11. no hidden network in imports, startup, ordinary reads, tests, CI or fixture demos;
12. fake/local adapter fixture parity and no live-provider test dependency;
13. exact exclusions and stop conditions.

## Locked exclusions

No production code, AI adapter, API/UI behavior, schema, migration, dependency, Provider, external network, PDF ingestion, crawling, fixture/test behavior, release/version, automatic EvidenceItem or Claim creation, automatic evidence grade, identity inference, deterministic calculation, ranking, recommendation, monitoring, portfolio or trading change.

## Validation

- base-to-head diff contains exactly the two authorized files;
- baseline current state and route are internally consistent;
- Issue #154 / PR #155 are recorded as deferred, not merged or completed capability;
- the next gate is Guarded AI Architecture Preflight only;
- no implementation authorization is implied;
- Draft PR remains open/unmerged pending independent fixed-head review.

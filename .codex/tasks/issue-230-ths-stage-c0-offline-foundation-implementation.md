# Issue #230 — THS Stage C0 Offline Foundation Implementation

## Authority

- Project-owner authorization: `继续进行下一步` on 2026-07-25.
- Governing implementation Issue: #230.
- Parent architecture: #227 / merged PR #229.
- Exact implementation base: `2b6c94beaf83687e92e46514e24ca938538f8c85`.
- Architecture authority: `docs/ths_stage_c0_offline_foundation_preflight.md`.
- Risk tier: **Strict Implementation**.
- Workflow authority: `.codex/WORKFLOW.md`.

## Objective

Implement one production-reachable but structurally offline THS foundation for the frozen `a_share_index_daily_history` contract. The implementation validates synthetic selectors and synthetic response shapes, generates deterministic fingerprints and a dry-run plan, and proves no transport or credential path exists.

## Fixed scope

Authorized production package:

```text
datasource/ths_structured_provider/
```

Authorized behavior:

- immutable index-history endpoint contract;
- closed readiness statuses and blocked reasons;
- reserved synthetic selector namespace;
- deterministic ordered query plan;
- request/schema SHA-256 fingerprints;
- synthetic diagnostic redaction;
- strict envelope/index-row validation;
- offline demo and zero-network tests.

## Required invariants

```text
source_key = ths-account-structured-provider-v1
capability_key = a_share_index_daily_history
path = /api/a-share-index/prices/historical
query_order = thscode, interval, start, end
interval = 1d
maximum_window = 10 calendar years
synthetic_only = true
remote_executable = false
live_stage_c1_gate = blocked_quota_contract
```

No amount of readiness input may turn Stage C0 into an executor.

## Golden path

1. import all Stage C0 modules under side-effect guards;
2. load the immutable index-history contract;
3. construct `SYNTH.IDX.C0` with explicit millisecond bounds;
4. construct readiness with quota/completion/revision/key lifecycle unresolved;
5. generate a deterministic non-executable plan;
6. validate the success synthetic fixture;
7. emit stable request/schema fingerprints and ordinary-Chinese blockers;
8. expose no credential, request ID, Provider value, database state or downstream mutation.

## Failure path

Fail closed for:

- non-synthetic identity;
- reversed or over-ten-year windows;
- mutated contract/host/path;
- unknown fields, wrong types or non-ascending rows;
- unsafe diagnostic URL or sensitive labels;
- any forbidden transport, subprocess, secret or database import/use.

## Validation

- focused local result before push: `12 passed`;
- run full repository CI on the final immutable PR HEAD;
- run all existing demos;
- run `python -m scripts.demo_ths_stage_c0_offline` in CI;
- verify complete base-to-head inventory is within Issue #230;
- perform fixed-head implementation review with the exact phrase:

```text
AUTHORIZED THS STAGE C0 OFFLINE FOUNDATION IMPLEMENTATION APPROVED at fixed head <FULL_HEAD_SHA>
```

Any commit after CI or review invalidates that evidence.

## Migration and rollback

```text
schema_migration = none
data_backfill = none
persistent_state = none
credential_state = none
network_side_effect = none
```

Rollback is a code/test/fixture/demo/workflow revert.

## Locked exclusions

No HTTP/DNS/socket/subprocess transport, API key, environment-secret lookup, Provider SDK/CLI, source activation, acquisition attempt, Provider-valued fixture, database model/repository/migration, API/UI, Today Market publication, full-market ingestion, historical catch-up, corporate action, historical membership synthesis, scheduler, fallback, row mixing, recommendation, portfolio or trading behavior.

## Merge gate

The Draft PR requires passing exact-head CI, process-independent fixed-head implementation approval, zero unresolved review threads and separate project-owner authorization before merge. Issue #230 remains open until separately authorized for completion.

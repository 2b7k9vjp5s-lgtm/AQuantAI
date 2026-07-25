# Issue #227 — THS Stage C0 Offline Foundation Architecture Preflight

## Authority

- Project-owner authorization: `授权进行下一步开发` on 2026-07-25.
- Governing Issue: #227.
- Parent roadmap: #137.
- Accepted Provider architecture: #190 / merged PR #191.
- Controlled refresh: #219 / merged PR #220.
- Today Market automatic refresh: #221 / merged PR #222.
- THS source synchronization: #223 / merged PR #224.
- Contract evidence: #225 / merged PR #226.
- Exact branch base: `2c3c64156ce4dcf88cf3bd7015b71f1ad4e3b933`.
- Risk tier: **Strict Architecture Preflight**.
- Workflow authority: `.codex/WORKFLOW.md`.

## Objective

Define whether one useful, implementation-ready, zero-network Stage C0 can be separated from the still-blocked live Provider path.

Candidate name:

```text
THS Offline Contract and Request-Planning Foundation
```

This task is architecture/documentation only. It does not authorize production code, live Provider access, credentials, schema/migration, dependency changes, Provider-valued fixtures, data download, UI, scheduler, release, tag, version change, Issue closure or merge.

## Controlling state

```text
retention_gate = closed_for_documented_local_normalized_storage
fixture_policy = resolved_synthetic_only
retry_reference_contract = confirmed_from_official_client
live_stage_c1_gate = blocked_quota_contract
production_live_network_authorized = false
```

Unknown account quotas, dataset completion cutoffs, correction/revision/late-data behavior and API-key lifecycle remain fail-closed.

## Architecture question

Can AQuantAI implement only the static source-specific contract representation, selector validation, dry-run request planning, fingerprinting, redaction and synthetic response validation before live readiness facts close, while proving that no code path can perform network access or persist Provider data?

## Required source material

Re-read and reconcile:

- `.codex/WORKFLOW.md`;
- `docs/architecture_baseline.md`;
- `docs/ths_structured_provider_preflight.md`;
- `docs/ths_structured_provider_preflight_decisions.md`;
- `docs/controlled_ths_refresh_mvp_preflight.md`;
- `docs/today_market_automatic_daily_refresh_preflight.md`;
- `docs/today_market_ths_source_sync_preflight.md`;
- `docs/ths_today_market_capability_manifest.md`;
- `docs/ths_today_market_official_contract_appendix.md`;
- `docs/ths_today_market_contract_resolution.md`;
- `docs/ths_today_market_contract_evidence.md`;
- `pyproject.toml` package boundary;
- existing `datasource` ownership and zero-network tests.

## Required decisions

1. exact Stage C0 ownership and non-ownership;
2. exact static contract facts versus externally unresolved readiness facts;
3. exact future implementation package and files;
4. deterministic selector and dry-run request-plan contracts;
5. canonical credential-free request fingerprint;
6. synthetic fixture reachability rules;
7. response-envelope/schema validation behavior;
8. stable blocked reason codes and Chinese projections;
9. network-denial enforcement;
10. rollback and future Stage C1 consumption path.

## Locked Stage C0 boundary

Allowed future behavior only:

- static THS endpoint/capability contract registry;
- immutable source-specific readiness value objects;
- family-specific selector validation;
- deterministic dry-run planning;
- request/schema fingerprints;
- synthetic-only response validation;
- credential-safe redaction on invented inputs;
- fail-closed blocked classifications;
- zero-network tests and demo.

Prohibited:

- HTTP client, DNS, socket or shell transport;
- API-key lookup or secret-store integration;
- source activation for remote use;
- acquisition-attempt or raw-response persistence;
- schema, migration or database writes;
- Provider-valued fixture;
- FastAPI route or Today Market UI;
- current snapshot or historical ingestion;
- corporate-action implementation;
- fallback, source mixing or row mixing.

## Candidate future implementation family

The architecture may authorize only a bounded source-specific package under the already packaged `datasource*` family:

```text
datasource/ths_structured_provider/__init__.py
datasource/ths_structured_provider/contracts.py
datasource/ths_structured_provider/readiness.py
datasource/ths_structured_provider/selectors.py
datasource/ths_structured_provider/planner.py
datasource/ths_structured_provider/fingerprint.py
datasource/ths_structured_provider/redaction.py
datasource/ths_structured_provider/schemas.py
```

No `transport.py`, `client.py`, `credentials.py`, `repository.py` or persistence module is part of Stage C0.

Candidate supporting families:

```text
tests/test_ths_stage_c0_*.py
tests/fixtures/ths_stage_c0/*.json
scripts/demo_ths_stage_c0_offline.py
.github/workflows/local-tests.yml
.codex/tasks/issue-<IMPLEMENTATION_ISSUE>-ths-stage-c0-*.md
```

The preflight must confirm or narrow these families; it may not broaden them into a generic Provider framework.

## Required outcome

Exactly one:

```text
ready_for_separate_stage_c0_implementation_issue
blocked_no_safe_offline_slice
blocked_existing_owner_conflict
blocked_fixture_not_production_reachable
```

No outcome changes:

```text
live_stage_c1_gate = blocked_quota_contract
production_live_network_authorized = false
```

## Offline golden path

1. load one exact reviewed THS index-history contract;
2. validate one invented selector;
3. produce one deterministic redacted dry-run request plan;
4. mark it `not_executable` because quota/completion/key-lifecycle facts remain unresolved;
5. validate one synthetic response envelope and one synthetic index row;
6. produce deterministic request/schema fingerprints;
7. prove zero credential, zero network, zero Provider value, zero database write and zero downstream accepted-state mutation.

## Primary failure path

A host/path/field mismatch, selector bound violation, synthetic fixture with unreachable fields, unresolved required live fact, historical-membership request, corporate-action requirement or any network attempt must fail closed without request, persistence, fallback or publication.

## Architecture deliverables

Authorized files only:

```text
.codex/tasks/issue-227-ths-stage-c0-offline-foundation-preflight.md
docs/ths_stage_c0_offline_foundation_preflight.md
```

`docs/architecture_baseline.md` is not changed unless a concrete current-state conflict is found. No production file may change.

## Validation

- exact base and merge-base verification;
- complete documentation-only changed-file inventory;
- Markdown/reference consistency;
- secret/account/Provider-value scan;
- full repository CI on the immutable final HEAD;
- process-independent fixed-head architecture review;
- zero unresolved review threads.

Required review phrase:

```text
AUTHORIZED THS STAGE C0 OFFLINE FOUNDATION PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

Any new commit invalidates prior CI and fixed-head review.

## Stop conditions

Stop if work requires:

- weakening Issue #225 live gates;
- credentials, account identifiers, request IDs or Provider values;
- production network, secret loading, schema or migration;
- generic provider abstraction or fallback;
- browser replay, cookies, undocumented endpoints or quota probing;
- current membership represented as historical;
- Canonical Price, Evidence Ledger, Industry Map, beneficiary, Investment Candidate, recommendation, portfolio or trading changes;
- release, tag or version change.

## Merge and implementation gate

This architecture PR remains Draft until fixed-head gates pass. Merge requires a separate exact owner authorization. Even after merge, Stage C0 implementation requires a separate explicit owner instruction and one bounded Strict implementation Issue/PR.
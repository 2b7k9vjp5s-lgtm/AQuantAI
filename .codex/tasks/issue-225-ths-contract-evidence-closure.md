# Issue #225 — THS Contract Evidence Closure

## Authority

- Project-owner instruction: continue Stage B autonomously in work mode.
- Linked Issue: #225.
- Parent architecture: #223 / merged PR #224.
- Exact branch base: `1c5de620446ecbd8b36c22e6945348cb2556cf72`.
- Risk tier: **Strict External Contract Evidence Preflight**.
- Workflow authority: `.codex/WORKFLOW.md`.

## Objective

Synchronize new non-secret official evidence from the Tonghuashun-maintained `HiThink-Tech/Financial-API` repository and narrow the remaining implementation blockers without inferring missing account limits or market-data semantics.

This task does not authorize production Provider code, application live-network access, credentials, schema, migration, Provider-valued fixtures, UI work, release, merge or a Stage C implementation Issue.

## Exact evidence boundary

Official upstream repository:

```text
repository = HiThink-Tech/Financial-API
commit = f8cdea908469b1b3b8bfb88dbb4d4a3959b1905c
observed_at_utc = 2026-07-24
```

Reviewed files:

```text
README.md
python/toolkit/marketdb/README.md
hithink-finance-cli/src/infrastructure/fuyao/retry.ts
hithink-finance-cli/src/infrastructure/fuyao/client.ts
```

Canonical evidence excerpt SHA-256:

```text
b19b6841c9255c18b4d29b58c57029ef25dacef340d41d8f69875f0477ae64d4
```

No API key, account identifier, order information, request ID or Provider market value is included.

## Accepted determinations

```text
automated_personal_research_use_permission = confirmed_from_official_repository
local_normalized_market_data_retention_permission = confirmed_from_official_marketdb_product
derived_local_research_output_retention_permission = confirmed_from_official_workflows
local_duckdb_long_term_storage = explicitly_supported
full_market_results_local_persistence = explicitly_supported
```

The evidence supports local normalized storage, incremental synchronization, SQL analysis, factor/panel research and file export. It does not grant redistribution rights.

## Fixture decision

```text
public_repository_provider_valued_fixture = prohibited_without_explicit_permission
public_repository_fixture_strategy = synthetic_or_schema_only
provider_valued_fixture_required_for_stage_c = false
local_contract_validation_output = schema_and_envelope_fingerprints_only
```

Repository tests remain zero-network and may not contain actual Provider market values. A synthetic fixture must use only fields reachable through the reviewed production contract.

## Official reference-client retry facts

```text
default_timeout_ms = 30000
default_max_attempts = 3
retry_after_header_precedence = true
client_backoff = exponential_1s_2s_4s_capped_8s_plus_jitter
retryable_business_codes = [4001, 5001, 5002, 5003]
authentication_errors = non_retryable
validation_errors = non_retryable
```

These facts describe the official maintained client implementation. They do not establish account QPS, daily-total or concurrency entitlements.

## Remaining blockers

```text
qps_limit = unresolved
daily_total_limit = unresolved
concurrency_limit = unresolved
limit_scope = unresolved
stage_c_dataset_completion_time = unresolved
snapshot_complete_session_cutoff = unresolved
correction_revision_late_data_behavior = unresolved
stable_source_update_timestamp = unresolved
api_key_expiry_and_max_active_keys = unresolved
corporate_action_account_entitlement = pending_bounded_local_validation
historical_full_market_gap_fill = separately_blocked
historical_dated_membership = unsupported
```

The official README explicitly states that data permissions, call frequency and accessible capabilities depend on website/account authorization. Unknown values remain fail-closed.

## Required output

Authorized changed files:

```text
.codex/tasks/issue-225-ths-contract-evidence-closure.md
docs/ths_today_market_contract_evidence.md
```

No existing accepted architecture document is deleted or rewritten by this evidence-only slice. The new evidence document has focused precedence only for the facts it explicitly resolves.

## Required outcome

```text
retention_gate = closed_for_documented_local_normalized_storage
fixture_policy = resolved_synthetic_only
retry_reference_contract = confirmed_from_official_client
quota_gate = blocked
completion_and_revision_semantics_gate = blocked
production_implementation_authorized = false
overall_gate = blocked_quota_contract
```

`blocked_quota_contract` is the single controlling outcome for this task. Semantic facts remain separately listed as unresolved and must also close before Stage C readiness.

## Offline evidence golden path

1. Select the exact official upstream commit and reviewed files.
2. Verify the evidence contains no secrets, account identifiers, request IDs or Provider market values.
3. Map each quoted product/client behavior to one narrowly scoped contract fact.
4. Resolve local normalized retention and synthetic fixture strategy without expanding redistribution rights.
5. Preserve unresolved quota, completion, revision and key-lifecycle facts as blockers.
6. Publish no runtime configuration, schema, network path or Provider data.

## Primary failure path

If an official source does not explicitly establish a fact, retain `unresolved`; do not infer it from product positioning, source code defaults or successful account entitlement tests.

## Stop conditions

Stop if work would require:

- API keys, account identifiers or private support information;
- Provider-valued fixtures in the public repository;
- load testing or hidden-limit probing;
- browser session replay or undocumented endpoints;
- production network access, code, schema or migration changes;
- creation of a Stage C implementation Issue;
- merge without separate owner authorization.

## Strict delivery gates

Before merge consideration:

1. verify exact base-to-head inventory;
2. run applicable repository validation on the exact HEAD;
3. obtain a process-independent fixed-head review containing:

```text
AUTHORIZED THS CONTRACT EVIDENCE CLOSURE PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

4. resolve all review threads;
5. receive separate explicit project-owner merge authorization.

Any new commit invalidates prior CI and fixed-head review evidence.

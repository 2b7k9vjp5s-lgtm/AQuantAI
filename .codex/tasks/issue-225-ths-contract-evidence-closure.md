# Issue #225 — THS Contract Evidence Final Fail-Closed Resolution

## Authority

Project-owner instruction on 2026-07-27:

```text
进行下一步工作
```

This instruction is interpreted after:

```text
repository = 2b7k9vjp5s-lgtm/AQuantAI
default_branch = main
exact_base = 6e1a98f18cce689ad002e2fb8fa4f72ad1bd438d
runtime_integration_pr = #262 / merged
state_baseline_pr = #264 / merged
controlling_issue = #225
parent_roadmap = #137
risk_tier = Strict External Contract Evidence Preflight
```

Workflow authority remains `.codex/WORKFLOW.md`.

## Objective

Finalize Issue #225 in one explicit fail-closed state after rechecking current official public sources, without inferring missing account limits or market-data chronology.

This task does not authorize:

- production Provider code;
- application live-network access;
- credentials or credential storage;
- schema or migration changes;
- Provider-valued fixtures;
- source activation;
- a Stage C implementation Issue;
- merge, release, tag or version change.

## Current official evidence recheck

Observed on 2026-07-27:

```text
https://fuyao.aicubes.cn/docs/introduction/
https://fuyao.aicubes.cn/docs/quickstart/
https://fuyao.aicubes.cn/admin/
https://github.com/HiThink-Tech/Financial-API
latest_visible_official_repository_commit = f8cdea908469b1b3b8bfb88dbb4d4a3959b1905c
```

The public recheck confirms no newer official repository commit than the already reviewed pinned commit.

The current official material continues to support:

```text
automated_personal_research_use_permission = confirmed_from_official_repository
local_normalized_market_data_retention_permission = confirmed_from_official_marketdb_product
derived_local_research_output_retention_permission = confirmed_from_official_workflows
public_repository_fixture_strategy = synthetic_or_schema_only
public_repository_provider_valued_fixture = prohibited_without_explicit_permission
retry_reference_contract = confirmed_from_official_client
credential_mechanism = X-api-key
api_key_creation_and_management_shape = documented
```

The recheck does not establish account-specific numeric quotas, completion cutoffs, revision semantics or API-key lifecycle limits.

## Evidence precedence

The accepted evidence document remains:

```text
docs/ths_today_market_contract_evidence.md
```

It already records the controlling outcome `blocked_quota_contract` and has focused precedence for the facts explicitly resolved there.

No rewrite of the accepted evidence document, capability manifest, contract resolution or source-sync architecture is required for this finalization task.

## Resolved facts retained

```text
transport_contract = confirmed
authentication_shape = confirmed
required_candidate_entitlements = partially_confirmed
automated_personal_research_use_permission = confirmed_from_official_repository
local_normalized_research_storage = supported_by_official_product_evidence
derived_local_output_retention = confirmed_for_documented_local_research_workflows
fixture_policy = resolved_synthetic_only
reference_client_timeout_ms = 30000
reference_client_max_attempts = 3
reference_client_retry_after_precedence = true
reference_client_retryable_business_codes = [4001, 5001, 5002, 5003]
```

Reference-client behavior is not an account quota contract.

## Required unresolved facts

The following remain unresolved and must not be guessed:

```text
qps_limit
daily_total_limit
concurrency_limit
per_endpoint_or_global_limit_scope
account_specific_rate_limit_headers_or_capability_fields
stage_c_dataset_completion_time
snapshot_complete_session_cutoff
provider_correction_behavior
provider_revision_behavior
late_data_behavior
stable_source_update_timestamp
api_key_expiry
api_key_inactivity_expiry
maximum_active_keys
revocation_effect_time
rotation_contract
production_dump_api_key_authentication
current_account_dump_entitlement
```

The quick-start page documents that an API-key quantity ceiling exists, but it does not disclose the numeric ceiling or lifecycle contract. This does not close any required key-lifecycle fact.

No successful low-volume call, absence of a public limit, reference-client default or Mock assumption may substitute for these facts.

## Final deterministic resolution

```text
retention_gate = closed_for_documented_local_normalized_storage
fixture_policy = resolved_synthetic_only
retry_reference_contract = confirmed_from_official_client
quota_gate = blocked
completion_and_revision_semantics_gate = blocked
api_key_lifecycle_gate = blocked
production_dump_authentication_gate = blocked
production_implementation_authorized = false
overall_gate = blocked_quota_contract
resolution_mode = explicit_fail_closed
```

`blocked_quota_contract` is the single controlling Issue #225 outcome.

The unresolved completion, correction, revision, late-data, API-key lifecycle and dump-authentication facts remain named blockers under that controlling outcome.

## Consequences

Until a later separately reviewed official evidence packet changes the controlling state:

```text
stage_c_implementation_issue = prohibited
live_ths_source_activation = prohibited
application_live_network_access = prohibited
credential_setup = prohibited
production_http_transport = prohibited
provider_raw_capture = prohibited
provider_persistence = prohibited
schema_or_migration = prohibited
provider_valued_public_fixture = prohibited
runtime_provider_fallback = disabled
cross_provider_row_mixing = prohibited
```

The default application remains Mock-disabled and performs zero acquisition.

The accepted deterministic Mock remains test/demo infrastructure only and cannot close or bypass Issue #225.

## Exact authorized file

Only:

```text
.codex/tasks/issue-225-ths-contract-evidence-closure.md
```

No second documentation file, production file, test, fixture, workflow, dependency, schema, migration or Provider file is authorized.

## Validation

Required checks:

1. Base remains exact `6e1a98f18cce689ad002e2fb8fa4f72ad1bd438d`.
2. Base-to-HEAD contains exactly this one Markdown file.
3. `behind = 0`.
4. The official source identities and current public state are re-read without secrets or keyed requests.
5. Existing accepted evidence remains unchanged.
6. Repository CI succeeds on one exact immutable HEAD.
7. A fresh process-independent fixed-head review contains exactly:

```text
AUTHORIZED THS CONTRACT EVIDENCE CLOSURE PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

8. All review threads are resolved.
9. Merge requires a separate project-owner command equivalent to `批准合并 PR #<number>`.

## Post-merge boundary

Merging this documentation PR would only accept the explicit fail-closed outcome.

It would not authorize:

- closing Issue #225 without a separate owner instruction;
- creating a live Stage C1 Issue, branch or PR;
- credential or network work;
- fallback to Tushare, AKShare, scraping or another Provider;
- recommendation, portfolio or trading behavior.

Any future official evidence must enter a new separately authorized evidence amendment and must not rewrite this historical fail-closed decision.

Any new commit invalidates prior CI and fixed-head review evidence.

# THS Account Capability Manifest Template

## Purpose

This template records only non-secret facts needed to decide whether one account-authorized 同花顺 / HiThink capability may enter a separate Strict implementation Issue.

Do not place any API key, token, account identifier, Cookie, CAS ticket, signed request, private header, credential-bearing screenshot or downloaded Provider dataset in this file, an Issue, a PR, a fixture or a log.

The manifest is evidence metadata, not proof by assertion. Every `confirmed` value needs a non-secret evidence reference and fingerprint.

## Allowed fact states

Use exactly one state for each fact:

- `confirmed` — supported by reviewed non-secret account or contract evidence;
- `unsupported` — the official contract explicitly does not support the fact or behavior;
- `not_entitled` — the account does not include the capability;
- `unknown` — no reliable evidence exists;
- `pending_owner_evidence` — evidence is expected but has not been supplied;
- `not_applicable` — the fact does not apply to this capability and the reason is recorded.

Unknown, blank and pending values are never treated as enabled.

## Evidence reference rules

A public repository may record only:

- evidence kind, such as `official_account_console`, `official_contract`, `official_documentation`, `provider_support_reply` or `sanitized_sample`;
- non-secret document title or capability label;
- review date;
- SHA-256 of a locally retained evidence artifact when permitted;
- a short non-secret summary;
- local retention location category, never a credential-bearing path or account identifier.

Do not copy restricted documentation when its terms prohibit redistribution. A fingerprint and reviewed summary are sufficient.

## Manifest header

| Field | Value |
|---|---|
| Manifest version | `aquantai.ths-account-capability-manifest.v1` |
| Provider key | `ths-account-structured-provider-v1` |
| Intended use | personal, local, non-commercial research |
| Owner review date | `PENDING` |
| Contract/evidence review date | `PENDING` |
| Overall state | `pending_owner_evidence` |
| Evidence package fingerprint | `PENDING` |
| Credential profile key label | `PENDING` — label only, never a secret |

## Account-level authorization facts

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| Exact enabled product names | `pending_owner_evidence` |  |  | Use official account wording. |
| Exact enabled capability names | `pending_owner_evidence` |  |  | Do not infer from public docs. |
| Credential mechanism label | `pending_owner_evidence` |  |  | Example category only; never include a value. |
| Renewal behavior | `pending_owner_evidence` |  |  |  |
| Revocation behavior | `pending_owner_evidence` |  |  |  |
| Personal-use permission | `pending_owner_evidence` |  |  |  |
| Automated-access permission | `pending_owner_evidence` |  |  |  |
| Local-retention permission | `pending_owner_evidence` |  |  |  |
| Retention duration/limits | `pending_owner_evidence` |  |  |  |
| Contract expiry or revalidation rule | `pending_owner_evidence` |  |  |  |

## Network and request contract

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| Exact HTTPS host allowlist | `pending_owner_evidence` |  |  | No wildcard unless contract explicitly defines it. |
| TLS/transport requirements | `pending_owner_evidence` |  |  |  |
| Credential placement contract | `pending_owner_evidence` |  |  | Header/query category only; never copy a secret. |
| Request timeout guidance | `pending_owner_evidence` |  |  |  |
| Documented retry guidance | `pending_owner_evidence` |  |  | No inferred retry. |
| Rate limit | `pending_owner_evidence` |  |  | Unit and window required. |
| Daily quota | `pending_owner_evidence` |  |  |  |
| Concurrent request limit | `pending_owner_evidence` |  |  |  |
| Quota reset timezone/time | `pending_owner_evidence` |  |  |  |
| 401 behavior | `pending_owner_evidence` |  |  |  |
| 403 behavior | `pending_owner_evidence` |  |  |  |
| 429 behavior | `pending_owner_evidence` |  |  |  |

## Capability record template

Create one record per exact account capability. Duplicate this section without changing field meanings.

### Capability identity

| Field | Value |
|---|---|
| Capability key | `PENDING` |
| Official product name | `PENDING` |
| Official capability name | `PENDING` |
| Account entitlement state | `pending_owner_evidence` |
| Proposed AQuantAI data family | `instrument_identity` / `daily_market` / `company_action` / `financial_statement` / `taxonomy` / `market_attention` / `bulk_bootstrap` |
| Readiness state | `deferred_contract_incomplete` |

### Endpoint contract

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| HTTPS host | `pending_owner_evidence` |  |  | Must match account-level allowlist. |
| HTTP method | `pending_owner_evidence` |  |  |  |
| Endpoint contract key/path | `pending_owner_evidence` |  |  | Non-secret documented path only. |
| Documentation/schema version | `pending_owner_evidence` |  |  | Version or review date required. |
| Required selector fields | `pending_owner_evidence` |  |  | Names and semantics, no credential. |
| Optional selector fields | `pending_owner_evidence` |  |  |  |
| Pagination mode | `pending_owner_evidence` |  |  | page/cursor/none. |
| Stable ordering | `pending_owner_evidence` |  |  | Exact keys and direction. |
| Terminal condition | `pending_owner_evidence` |  |  |  |
| Response media type | `pending_owner_evidence` |  |  |  |
| Response schema/root shape | `pending_owner_evidence` |  |  |  |
| Unknown-field behavior | `pending_owner_evidence` |  |  |  |
| Maximum request window | `pending_owner_evidence` |  |  |  |
| Maximum rows/pages | `pending_owner_evidence` |  |  |  |
| Maximum response bytes | `pending_owner_evidence` |  |  | Project ceiling may be lower. |

### Identity and chronology

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| Stable Provider record identity | `pending_owner_evidence` |  |  |  |
| Stable Provider symbol identity | `pending_owner_evidence` |  |  |  |
| Exchange/market field semantics | `pending_owner_evidence` |  |  | No code-prefix inference. |
| Security type field semantics | `pending_owner_evidence` |  |  |  |
| Observation/effective time | `pending_owner_evidence` |  |  |  |
| Provider update time | `pending_owner_evidence` |  |  |  |
| Publication/disclosure time | `not_applicable` |  |  | Required for financial/disclosure facts when applicable. |
| Timezone | `pending_owner_evidence` |  |  |  |
| Historical coverage | `pending_owner_evidence` |  |  | Account-specific. |
| Late-arrival behavior | `pending_owner_evidence` |  |  |  |
| Correction/restatement behavior | `pending_owner_evidence` |  |  |  |
| Deletion/withdrawal behavior | `pending_owner_evidence` |  |  |  |

### Sanitized fixture reachability

| Fact | State | Non-secret value | Evidence reference/fingerprint | Notes |
|---|---|---|---|---|
| Sanitized response example available | `pending_owner_evidence` |  |  | Must contain no account or credential data. |
| Fixture fields reachable in production | `pending_owner_evidence` |  |  | No invented fixture-only fields. |
| Fixture response schema fingerprint | `pending_owner_evidence` |  |  |  |
| Null/missing-field examples | `pending_owner_evidence` |  |  |  |
| Error-response examples | `pending_owner_evidence` |  |  | 401/403/429/schema drift where permitted. |

## Deterministic readiness rule

A capability is `implementation_ready` only when all of the following are `confirmed` or validly `not_applicable`:

1. account entitlement;
2. permitted automated personal use;
3. permitted local retention;
4. exact HTTPS host;
5. exact method and endpoint contract;
6. request/response schema;
7. pagination and ordering;
8. rate/quota/concurrency behavior;
9. stable source identities;
10. chronology and timezone semantics;
11. correction/revision behavior;
12. sanitized production-reachable fixture.

Otherwise choose exactly one:

- `deferred_not_entitled`;
- `deferred_contract_incomplete`;
- `rejected_undocumented`;
- `blocked_retention_or_use`.

## Candidate first-slice declaration

The first implementation candidate remains 190-A and may include only capabilities marked `implementation_ready` that are required for:

- source authorization/capability revisions;
- dry-run request planning;
- acquisition attempts and immutable raw capture;
- Provider instrument identity candidates;
- explicit Listed Instrument mapping review;
- exact provenance reads;
- disabled-by-default smoke-test boundary.

Daily market, company actions, financial statements, taxonomy, market attention and bulk bootstrap remain deferred unless a later explicit Issue authorizes them.

## Review sign-off

| Field | Value |
|---|---|
| Reviewed by project owner | `PENDING` |
| Review date | `PENDING` |
| Overall gate result | `blocked_pending_account_facts` |
| Ready capability keys |  |
| Deferred capability keys |  |
| Rejected capability keys |  |
| Missing fact summary |  |

A completed template still requires a separate Strict architecture fixed-head review and explicit project-owner authorization before any implementation Issue is created.
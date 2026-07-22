# Issue #190 — Account-Authorized THS Structured Financial Data v1 Architecture Preflight

## Authority

- GitHub Issue: #190
- Product Roadmap: #137, Slice 6
- Required base: `2247499f698f1fbdea5fc33503678c682662c166`
- Branch: `docs/ths-structured-provider-preflight`
- Risk tier: **Strict**
- Owner authorization: use 同花顺 API for structured market, financial and market-attention data and proceed to the next development round on 2026-07-22
- Architecture only; no production adapter, schema, migration, dependency, credential, live request, release or version change

## Objective

Define one implementable Provider contract for the official account-authorized 同花顺金融数据 API used only for personal, local and non-commercial research.

The architecture must make one narrow decision:

> AQuantAI may later acquire documented structured data through one user-owned 同花顺 API credential and one source-specific adapter, while preserving immutable raw provenance and preventing Provider observations from silently becoming canonical price, official disclosure evidence or investment conclusions.

The output of this task is a Definition of Ready, not an implementation.

## Accepted source candidate

- Provider/operator: 同花顺 / HiThink official Financial Data API.
- Official documentation entry: `https://fuyao.aicubes.cn/docs/`.
- Access mode: user-owned account and officially issued credential only.
- Intended use: personal, local, non-commercial research.
- Production transport candidate: documented REST API only.
- One source registration and one source-specific adapter.
- Explicit user-initiated bounded commands only.
- No scheduler, daemon, webhook, startup fetch or read-triggered network request.

CLI, SDK, MCP and bulk dump tools may be assessed as auxiliary tooling, but they cannot become undocumented alternate runtime paths or owners of accepted ingestion state.

## Interim source portfolio

- 同花顺 owns structured Provider observations for accepted data families.
- CNINFO automated acquisition remains blocked until official Token/entitlement, retention, limits and PDF rights are confirmed.
- Official CNINFO announcement/PDF manual import is a separate future offline path.
- No cross-source fallback, row mixing, conflict suppression or automatic evidence promotion.

## Candidate data families

The architecture must explicitly accept, defer or reject:

1. listed-instrument and provider-symbol identity;
2. daily OHLCV/turnover and trading-calendar observations;
3. documented company actions;
4. balance sheet, income statement and cash-flow statement observations;
5. documented financial indicators with exact formula, period and unit semantics;
6. industry and concept taxonomies plus membership observations;
7. hot lists, ranking history, abnormal-move reasons, limit-up/continuous-limit-up and dragon-tiger-list observations;
8. optional bulk historical dump/bootstrap and local DuckDB interoperability.

## Required contract facts before implementation

The owner must supply or confirm non-secret facts for the actual account:

1. enabled product/capability names;
2. credential type and renewal/revocation behavior;
3. exact HTTPS host allowlist;
4. documented endpoint/method/request/response contracts;
5. pagination, ordering, time-zone and timestamp semantics;
6. rate limits, daily quota, concurrency and retry guidance;
7. local-retention and personal-use restrictions;
8. historical coverage and account-specific entitlement boundaries;
9. stable provider record and symbol identifiers;
10. correction, restatement, late-arrival and revision behavior.

Secret values never enter Issues, PRs, fixtures, logs, database rows or task files.

## Existing accepted boundaries

Reuse without changing meaning:

- existing market-data persistence where its complete-snapshot ownership actually matches the selected family;
- Listed Instrument identity and revision boundaries;
- Canonical Price and purpose-specific Comparison Eligibility ownership;
- Normalized Financial and Valuation contracts;
- Evidence Ledger ownership of accepted evidence;
- information cutoff and recorded-UTC leakage prevention;
- append-only accepted history;
- deterministic state outside LLM ownership;
- zero-network imports, startup, ordinary reads, tests, CI and fixture demos.

Do not reuse a table or command merely because both workflows involve data acquisition. Ownership must be established per data family.

## Required architecture decisions

### 1. Source authorization

Define append-only source authorization identity/revisions containing:

- stable source key;
- operator and product/capability labels;
- permitted personal non-commercial use basis;
- active/suspended/retired/pending state;
- credential profile key only;
- contract and capability-manifest fingerprints;
- retention/replay restrictions;
- review and expiry dates.

### 2. Credential and network boundary

Define:

- environment or approved local secret-store loading;
- disabled-by-default network profile;
- exact HTTPS host allowlist;
- timeout and bounded retry policy;
- no redirect to unreviewed hosts;
- credential-safe diagnostics;
- no secrets in request fingerprints.

### 3. User-initiated acquisition

Define bounded dry-run-capable commands requiring:

- exact source authorization revision;
- exact capability/data-family key;
- explicit instrument, date, period or list selector;
- maximum pages/items/bytes;
- explicit information cutoff, with request/fetch/recorded timestamps owned by the system;
- explicit remote-access confirmation;
- expected-latest protection where revisions are created.

### 4. Immutable L0 capture

Separate:

- acquisition attempt identity/revision;
- request fingerprint;
- immutable raw response object;
- response SHA-256 and byte length;
- request/fetch/recorded timestamps;
- endpoint contract and schema versions;
- credential-safe status and diagnostics.

Raw Provider data remains L0 audit state.

### 5. Instrument identity

Candidate generation may use only documented provider symbol, market/exchange fields and reviewed deterministic aliases. Code-prefix guessing, fuzzy matching and LLM-owned acceptance are prohibited.

### 6. Daily market and company-action semantics

Decide:

- raw versus adjusted price ownership;
- adjustment factor and corporate-action behavior;
- trading date/time zone;
- suspension and missing-day behavior;
- volume, amount and turnover units;
- duplicate/correction behavior;
- relationship to existing market-data persistence and Canonical Price.

Provider price observations must not silently replace accepted Canonical Price.

### 7. Financial-statement semantics

Keep separate:

- report period end;
- report type;
- disclosure/publication time;
- provider record time;
- currency and unit;
- consolidated versus parent scope;
- audited/unaudited state;
- original versus restated value;
- latest and historical revisions.

Null remains unknown. Derived values require separately versioned deterministic formulas.

### 8. Industry and concept semantics

Distinguish taxonomy identity/revision, current membership snapshot and historically effective membership. Current membership cannot be represented as historical as-of state without a documented effective-history contract.

### 9. Market-attention semantics

Preserve list type, ranking window, observation time, rank, provider value/score where documented, reason text and exact source identity.

Attention is market-state context only. It cannot create beneficiary status, evidence grade, candidate status, recommendation or accepted investment score.

### 10. Deterministic normalization and revisions

Define source-specific normalizers, strict required fields, schema versions, unknown-field handling, stable ordering, exact duplicates, correction/restatement append-only behavior and no silent overwrite.

### 11. Schema and migration candidate

Define minimum additive tables or explicit reuse decisions for:

- source authorization identities/revisions;
- acquisition attempt identities/revisions;
- immutable raw Provider response objects;
- provider instrument candidates;
- normalized market observations;
- company-action observations;
- financial statement observation identities/revisions;
- taxonomy and membership observations;
- market-attention observation identities/revisions;
- exact downstream provenance links.

Decide PostgreSQL/SQLite behavior, constraints, indexes, migration order, concurrency, byte ceilings and populated downgrade refusal.

### 12. Commands and reads

Candidate future commands:

1. register/update source authorization without secret material;
2. inspect an owner-supplied capability manifest;
3. plan one bounded request without network;
4. acquire one bounded data-family request;
5. normalize one immutable response;
6. review exact instrument identity candidates;
7. inspect exact Provider provenance;
8. run an opt-in contract smoke test disabled by default.

No API read endpoint may trigger acquisition.

### 13. Testing

Require:

- secret-free offline contract fixtures;
- zero-network imports/startup/ordinary reads/tests/CI/demos;
- one separately marked opt-in smoke test;
- request fingerprint and pagination determinism;
- credential redaction;
- 401/403/429/quota/timeout/contract-change behavior;
- unknown-field and schema-drift rejection;
- null/unit/currency/period handling;
- adjustment/restatement/correction append-only behavior;
- taxonomy current-versus-historical protection;
- market-attention time-window semantics;
- no automatic Evidence Ledger, candidate or recommendation mutation;
- PostgreSQL concurrency and supported SQLite behavior;
- populated downgrade refusal.

## Production-realistic golden path

The architecture document must specify one offline-replayable path:

1. active account-authorized source revision;
2. one exact provider-symbol to Listed Instrument candidate;
3. one bounded daily-market response;
4. one company-action response or explicit no-action result;
5. one financial-statement response with period/disclosure semantics;
6. one taxonomy/membership response;
7. one market-attention snapshot;
8. immutable raw capture and deterministic normalized observations;
9. exact provenance readback under both as-of boundaries;
10. no hidden fallback, automatic evidence acceptance, recommendation or background request.

## Primary failure path

No downstream accepted-state mutation when:

- credential/capability is absent, expired, revoked or outside entitlement;
- host, endpoint, schema, unit, period, timestamp or identifier differs from contract;
- source returns unauthorized, forbidden, rate-limited or quota-exhausted;
- identity is ambiguous;
- raw response exceeds reviewed limits;
- financial revisions conflict without append-only resolution;
- current taxonomy membership is requested as historical state without support;
- attention data is about to mutate beneficiary/candidate/recommendation state;
- chronology violates cutoff or recorded-UTC boundaries.

## Stop conditions

Do not authorize implementation if:

- only undocumented/private endpoints or browser-session replay are available;
- credentials require Cookie, CAS ticket, reverse engineering or bypass behavior;
- personal local retention or automated access is prohibited;
- account capabilities and limits cannot be established;
- multiple runtime providers or generic fallback become necessary;
- Provider data would silently replace Canonical Price or official disclosure evidence;
- the contract cannot be represented by secret-free offline fixtures.

## Deliverables

1. this task snapshot;
2. `docs/ths_structured_provider_preflight.md`;
3. `docs/ths_structured_provider_preflight_decisions.md`;
4. synchronized `docs/architecture_baseline.md`;
5. one Draft architecture PR based exactly on the required base;
6. documentation/CI validation and process-independent fixed-head architecture review.

## Required approval

`AUTHORIZED THS STRUCTURED PROVIDER PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`

## Locked exclusions

No production adapter, migration, dependency, credential, live request, scheduler, background worker, CNINFO automated acquisition, public scraping, browser replay, reverse-engineered endpoint, generic multi-provider fallback, news/research-report ingestion, OCR, automatic EvidenceItem or claim creation, automatic evidence grade, automatic accepted financial derivation, LLM-owned accepted state, unexplained score, recommendation, target price, portfolio, execution, trading, release, tag or version change.

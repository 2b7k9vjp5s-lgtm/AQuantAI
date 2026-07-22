# Investment Candidate Intelligence Layer v1 — Architecture Preflight

## 1. Status, authority and risk

- Architecture Issue: #179.
- Required base: `ccb949beb08d25d4b91ae970b1e1781a09d92f8e`.
- Predecessor: Canonical Price and Comparison Eligibility v1, merged through PR #178.
- Risk tier: **Strict**.
- Purpose code: `industry_beneficiary_investment_candidate_v1`.
- Rule version: `aquantai.investment-candidate-priority.v1`.
- This document authorizes architecture only. Production schema, migration and runtime require a separate Strict implementation Issue and PR.

This phase introduces valuation use, deterministic scoring, candidate buckets and bounded priority ordering. It therefore requires one independent fixed-head architecture review and one independent fixed-head implementation review.

## 2. Product decision

AQuantAI will support the following two-stage research method:

```text
Stage A — complete industry-beneficiary universe
  -> Stage B — current investment-candidate overlay
```

Stage A remains authoritative for which companies benefit from an industry change. Stage B answers a different question:

> Given the complete beneficiary universe and the currently accepted research state, which companies deserve the highest current investment-research priority, why, what is already reflected in price or expectations, and what could invalidate the thesis?

Stage B must not mutate, reclassify, delete or hide Stage A companies. Every exact candidate-pool member remains visible even when downstream research, price, valuation or evidence is missing.

The user-facing output is research-oriented and non-advisory. Supported candidate statuses are exactly:

- `priority_candidate`
- `watch_candidate`
- `awaiting_verification`
- `pricing_demanding`
- `evidence_insufficient`
- `not_current_candidate`

These statuses do not mean buy, sell or hold. They do not imply target price, expected return, position size or trading action.

## 3. Accepted baseline reused by v1

The implementation must reuse, not replace:

- one exact `Stage1CandidatePoolRevision` and all exact `Stage1CandidatePoolMembership` rows;
- exact Stage 1 beneficiary revisions;
- exact Typed Beneficiary Evidence Semantics revisions when available;
- exact Stage 2 Company Research revisions and their frozen hypotheses;
- exact supported Stage 2 market-expectation revisions;
- exact supported Stage 2 valuation-snapshot revisions;
- exact catalyst, risk and quality revisions from v0.6C/v0.6D when available;
- exact accepted Canonical Price revisions;
- exact Comparison Eligibility revisions for `company_research_price_context_v1`;
- exact accepted claim/evidence revisions referenced by explicit component assessments.

No existing upstream record is modified, backfilled, regraded or automatically rebound.

## 4. Semantic and derivation ownership

### 4.1 Explicit component assessment is D3

The eight component assessments are explicit analyst-owned D3 research judgments:

1. `industry_opportunity`
2. `beneficiary_strength`
3. `earnings_conversion`
4. `expectation_gap`
5. `valuation_context`
6. `catalyst_readiness`
7. `evidence_quality`
8. `risk_penalty`

Application code validates closed vocabulary, range, chronology, exact links and evidence requirements. It does not invent the component score.

An LLM may later draft a proposed component assessment through a separately reviewed adapter, but it may not persist, approve or silently replace accepted component state.

### 4.2 Aggregation is D2

Given exact accepted component revisions, application code deterministically calculates:

- weighted base score;
- business-quality score;
- risk penalty points;
- final score;
- candidate status;
- deterministic reason codes;
- bounded priority order.

These outputs are D2 because the rule is explicit, versioned and reproducible.

### 4.3 Canonical Price remains L3

Canonical Price and Comparison Eligibility retain their accepted ownership. The Investment Candidate layer can reference exact revisions but cannot change price, currency, unit, adjustment, source or eligibility semantics.

## 5. Component assessment contract

### 5.1 Common fields

Every component revision must contain:

- one exact stable component-assessment identity;
- one exact Stage 1 beneficiary revision;
- one exact Stage 2 Company Research revision;
- `component_code` from the closed eight-value vocabulary;
- `assessment_state`;
- `verification_state`;
- `score_value` when supported;
- rationale summary;
- falsification condition;
- falsification state;
- information cutoff date;
- recorded-at UTC;
- recorded-by actor;
- exact superseded revision when appending;
- expected-latest revision number;
- one or more exact upstream input links when state is supported.

### 5.2 Assessment state

`assessment_state` is exactly:

- `supported`
- `missing`
- `disputed`
- `not_applicable`

Rules:

- `supported` requires a score and exact input links;
- `missing` forbids a score and requires a stable missing reason;
- `disputed` may preserve a proposed score for display but it is not aggregation-eligible;
- `not_applicable` forbids a score and is not silently reweighted.

### 5.3 Verification state

`verification_state` is exactly:

- `verified`
- `pending`
- `failed`
- `not_applicable`

A supported component can still be `pending` when an explicit future verification event remains unresolved. A `failed` verification can trigger `not_current_candidate` when the component revision marks the failure as thesis-falsifying.

### 5.4 Score range and decimal rule

- score range: `0.00` through `100.00` inclusive;
- storage scale: two decimal places;
- input parsing: decimal text only, not binary float;
- rounding: `ROUND_HALF_EVEN`;
- NaN, infinity, exponent overflow and out-of-range values fail before write;
- score text and standardized decimal text are both preserved.

### 5.5 Exact input links

A component revision must link exact accepted revisions appropriate to its meaning.

| Component | Minimum required exact inputs for `supported` |
| --- | --- |
| `industry_opportunity` | exact selected map revision plus at least one exact industry-map observation or accepted claim revision |
| `beneficiary_strength` | exact beneficiary revision plus exact typed-beneficiary revision; positive execution claims require exact accepted claim/evidence links |
| `earnings_conversion` | exact Company Research revision plus at least one exact supported financial-hypothesis revision |
| `expectation_gap` | exact Company Research revision plus at least one exact supported market-expectation revision |
| `valuation_context` | exact Company Research revision, one exact supported valuation revision, one exact accepted Canonical Price revision and one exact eligible Comparison Eligibility revision |
| `catalyst_readiness` | exact supported catalyst revision or explicit missing state |
| `evidence_quality` | exact accepted claim/evidence revisions used by the other supported components; no score may be inferred from evidence count alone |
| `risk_penalty` | exact supported risk revision and explicit falsification links where applicable |

The implementation may use typed one-of input-link columns so database foreign keys preserve exact upstream identities. It must not store an unvalidated generic UUID with only a free-text type label.

## 6. No hidden inference

The following cannot create or change a component score:

- company name;
- stock-code prefix;
- Provider name;
- price movement by itself;
- evidence count by itself;
- document recency by itself;
- social/news volume;
- UI ordering;
- missing-value defaults;
- AI-generated prose;
- a newer compatible-looking upstream revision.

Every score is explicit D3 input. Every aggregate is deterministic D2 output.

## 7. Deterministic scoring rule v1

### 7.1 Positive-component weights

| Component | Weight |
| --- | ---: |
| `industry_opportunity` | 15.00% |
| `beneficiary_strength` | 20.00% |
| `earnings_conversion` | 20.00% |
| `expectation_gap` | 15.00% |
| `valuation_context` | 15.00% |
| `catalyst_readiness` | 10.00% |
| `evidence_quality` | 5.00% |

The positive weights sum to exactly 100.00%.

### 7.2 Base score

```text
base_score =
    industry_opportunity * 0.15
  + beneficiary_strength * 0.20
  + earnings_conversion * 0.20
  + expectation_gap * 0.15
  + valuation_context * 0.15
  + catalyst_readiness * 0.10
  + evidence_quality * 0.05
```

All arithmetic uses Decimal and `ROUND_HALF_EVEN`, standardized to two decimal places after each final calculated field.

### 7.3 Risk penalty

```text
risk_penalty_points = risk_penalty * 0.25
final_score = max(0.00, base_score - risk_penalty_points)
```

The maximum arithmetic deduction is 25.00 points. Independent risk gates still apply.

### 7.4 Business-quality score

To distinguish an attractive business from an unattractive current price, v1 calculates:

```text
business_quality_score =
  (
      industry_opportunity * 0.15
    + beneficiary_strength * 0.20
    + earnings_conversion * 0.20
    + catalyst_readiness * 0.10
    + evidence_quality * 0.05
  ) / 0.70
```

This score excludes expectation gap and valuation context. It is displayed only when all included components are aggregation-eligible.

### 7.5 Aggregation eligibility

A numeric aggregate is allowed only when:

- all seven positive components are `supported`;
- `risk_penalty` is `supported`;
- all component revisions are visible at both as-of boundaries;
- no component is disputed;
- no required exact upstream link is missing;
- the exact Canonical Price revision is accepted;
- the exact Comparison Eligibility revision is `eligible` for `company_research_price_context_v1`;
- valuation currency, unit, price kind and adjustment basis match the linked canonical contract;
- no thesis-falsification flag is active.

No missing component is treated as zero. No weight is redistributed.

## 8. Candidate status rule and precedence

Status is assigned in the following strict order.

### 8.1 Integrity failure rejects the entire write

The snapshot command fails before any insert when:

- candidate-pool membership is incomplete, duplicated or substituted;
- exact revision identities do not match their owning stable identities;
- chronology violates cutoff or recorded-UTC boundaries;
- source links are inconsistent;
- expected-latest protection fails;
- a hidden default or inferred selector would be required.

These are not member statuses. They are transaction-level failures.

### 8.2 `evidence_insufficient`

Use when the member is preserved in the complete universe but:

- Company Research is missing;
- a required component is `missing` or `not_applicable`;
- a component is `disputed`;
- price or valuation input is missing, stale, conflicting, rejected or ineligible;
- exact provenance is incomplete;
- no numeric aggregate is permitted.

### 8.3 `awaiting_verification`

Use when:

- no component is disputed;
- no thesis-falsification flag is active;
- one or more explicitly named verification items are `pending`;
- the reason codes identify what must be verified, such as certification, order, capacity, production or financial confirmation;
- the member is not aggregation-eligible yet.

This status is more specific than generic missing evidence.

### 8.4 `not_current_candidate`

Use when any of the following is true:

- `risk_penalty >= 75.00`;
- any linked risk/falsification record is explicitly thesis-falsifying and active;
- verification state is `failed` and marked material;
- a complete aggregate exists but neither priority, watch nor pricing-demanding criteria are met.

### 8.5 `pricing_demanding`

Use when all aggregation gates pass, risk is below 75.00, and:

- `business_quality_score >= 70.00`; and
- either `valuation_context < 40.00` or `expectation_gap < 40.00`.

This means the industry/company thesis may be strong while current price or market expectations appear demanding. It is not a sell instruction.

### 8.6 `priority_candidate`

Use when all aggregation gates pass and all are true:

- `final_score >= 75.00`;
- `beneficiary_strength >= 65.00`;
- `earnings_conversion >= 65.00`;
- `expectation_gap >= 50.00`;
- `valuation_context >= 50.00`;
- `risk_penalty < 50.00`.

### 8.7 `watch_candidate`

Use when all aggregation gates pass and:

- `final_score >= 60.00`;
- `risk_penalty < 65.00`;
- priority and pricing-demanding rules did not match.

### 8.8 Remaining complete aggregates

Any remaining aggregation-eligible member is `not_current_candidate`.

## 9. Bounded priority order

Priority ordering is permitted only inside one exact snapshot revision.

Only `priority_candidate` and `watch_candidate` members receive a non-null `priority_ordinal`.

Sort order is exactly:

1. `priority_candidate` before `watch_candidate`;
2. final score descending;
3. business-quality score descending;
4. risk penalty ascending;
5. beneficiary-strength score descending;
6. beneficiary UUID ascending.

The UI may highlight the first three ordered members as `重点候选`, but must display the complete candidate-pool universe on the same page.

The order cannot be used across different snapshot revisions, candidate pools, rule versions or as-of boundaries.

## 10. Closed deterministic reason-code vocabulary

The initial rule version permits only the following member reason codes, sorted lexicographically before persistence and output:

- `canonical_price_conflicting`
- `canonical_price_ineligible`
- `canonical_price_missing`
- `canonical_price_stale`
- `component_disputed`
- `critical_component_missing`
- `earnings_conversion_weak`
- `evidence_quality_low`
- `expectation_already_reflected`
- `expectation_input_disputed`
- `expectation_input_missing`
- `falsification_triggered`
- `market_attention_not_available_v1`
- `priority_threshold_met`
- `pricing_demanding`
- `risk_high`
- `score_below_watch_threshold`
- `valuation_input_disputed`
- `valuation_input_missing`
- `verification_failed`
- `verification_pending`
- `watch_threshold_met`

Free-text rationale may explain the result but cannot replace core status or reason codes.

## 11. Canonical Price and valuation boundary

### 11.1 Exact price use

The valuation component must bind:

- one exact accepted Canonical Price revision;
- one exact eligible Comparison Eligibility revision;
- purpose `company_research_price_context_v1`;
- exact instrument revision;
- exact series-contract revision;
- currency;
- unit `currency_per_share`;
- price kind `official_close`;
- adjustment basis;
- trade date;
- information cutoff and recorded UTC.

### 11.2 Stage 2 valuation observation

The valuation component must also bind one exact supported `Stage2ValuationSnapshotRevision` belonging to the exact Company Research revision.

Existing v0.6B valuation rows are contextual research observations. They are not silently upgraded to normalized multiples or peer-comparable metrics. The analyst-owned `valuation_context` component score explains how the exact valuation observation and canonical price are interpreted.

### 11.3 v1 exclusions

v1 does not calculate:

- fair value;
- target price;
- expected return;
- automatic PE/PS/EV-to-EBITDA normalization;
- FX conversion;
- corporate-action reconstruction;
- raw share-price magnitude comparison;
- cross-market peer arithmetic.

A later normalized-valuation contract can be added only through another Strict architecture task.

## 12. Expectation-gap boundary

The `expectation_gap` component is an explicit D3 research assessment linked to one or more exact supported market-expectation revisions.

It must state:

- period horizon;
- expectation kind;
- direction;
- confidence;
- basis;
- exact hypothesis/claim/evidence links;
- what observation would close or falsify the gap.

The component cannot be inferred from recent price movement, article count, social attention or a hidden consensus feed.

## 13. Market-attention boundary

External news, social-media, fund-flow, brokerage and real-time market-attention data are not available in v1.

`market_attention` is not part of the scoring formula. The UI must disclose `market_attention_not_available_v1` rather than silently treating it as neutral.

Adding market attention requires a separate Strict Provider/ingestion architecture with source authorization, immutable raw capture, normalization, identity and chronology rules.

## 14. Candidate additive persistence design

A future implementation migration is expected to be `20260722_0014_investment_candidate_intelligence.py` and create exactly eight additive tables.

### 14.1 `investment_candidate_component_assessments`

Stable identity for one beneficiary/component/assessment key.

Minimum fields:

- UUID primary key;
- beneficiary ID;
- component code;
- explicit assessment key;
- created-at UTC;
- uniqueness on beneficiary ID, component code and assessment key.

### 14.2 `investment_candidate_component_revisions`

Append-only D3 component revisions.

Minimum fields:

- UUID primary key;
- component-assessment ID;
- revision number;
- exact beneficiary revision ID;
- exact Company Research revision ID;
- assessment state;
- verification state;
- source score text;
- standardized score Decimal(5,2), nullable by state;
- rationale;
- falsification condition and state;
- information cutoff date;
- recorded-at UTC;
- recorded-by;
- supersedes revision ID;
- unique assessment/revision number;
- expected-latest protection in command logic.

### 14.3 `investment_candidate_component_input_links`

Typed exact upstream revision links for one component revision.

The implementation should use nullable typed foreign-key columns with a database check that exactly one target is set. Authorized target families are limited to the accepted map, beneficiary semantics, Company Research, hypothesis, expectation, valuation, catalyst, risk, quality, Canonical Price, Comparison Eligibility and claim/evidence revision families required by this architecture.

### 14.4 `investment_candidate_snapshots`

Stable identity for one candidate pool, purpose and explicit snapshot key.

Minimum fields:

- UUID primary key;
- candidate-pool ID;
- purpose code;
- snapshot key;
- created-at UTC;
- uniqueness on candidate-pool ID, purpose and snapshot key.

### 14.5 `investment_candidate_snapshot_revisions`

Append-only deterministic snapshot revisions.

Minimum fields:

- UUID primary key;
- snapshot ID;
- revision number;
- exact candidate-pool revision ID;
- purpose code;
- rule version;
- information cutoff date;
- recorded-at UTC;
- recorded-by;
- supersedes revision ID;
- unique snapshot/revision number.

### 14.6 `investment_candidate_members`

Complete immutable membership and deterministic output for one snapshot revision.

Minimum fields:

- UUID primary key;
- snapshot-revision ID;
- exact candidate-pool membership ID;
- exact beneficiary ID and beneficiary-revision ID;
- exact Company Research revision ID when present;
- exact typed-beneficiary revision ID when present;
- exact canonical-price revision ID when present;
- exact Comparison Eligibility revision ID when present;
- base score, business-quality score, risk-penalty points and final score when aggregation-eligible;
- candidate status;
- priority ordinal when eligible;
- recorded-at UTC;
- uniqueness preventing duplicate or substituted pool members.

The command must compare the complete stored member set to the exact candidate-pool membership set before any insert.

### 14.7 `investment_candidate_member_component_links`

Exact component revisions used by each member and the deterministic contribution.

Minimum fields:

- member ID;
- component code;
- exact component-revision ID;
- rule weight;
- contribution amount;
- unique member/component code.

### 14.8 `investment_candidate_member_reason_codes`

Deterministic sorted reason codes.

Minimum fields:

- member ID;
- reason code;
- ordinal;
- unique member/reason code and member/ordinal.

## 15. Migration and downgrade rules

The implementation migration must:

- create only the eight new tables;
- alter no existing table;
- perform no data backfill;
- preserve PostgreSQL and supported SQLite behavior;
- use explicit checks and uniqueness constraints;
- register append-only ORM models;
- check all eight tables for rows before any downgrade drop;
- refuse the downgrade before dropping anything when any table is populated;
- drop empty tables in reverse dependency order.

No existing Stage 1, Stage 2, Evidence Ledger, Canonical Price or Company Comparison record can be rewritten.

## 16. Command boundary

Future implementation provides exactly two local structured-input commands:

```text
python -m scripts.record_investment_candidate_component --input <local-json-path>
python -m scripts.record_investment_candidate_snapshot --input <local-json-path>
```

Both commands must:

- read bounded UTF-8 JSON only;
- reject unknown fields;
- support `--dry-run`;
- emit deterministic strict JSON with `allow_nan=False`;
- require explicit IDs, actor, cutoff and recorded UTC;
- use expected-latest revision protection;
- re-read the exact graph inside one transaction;
- perform no network or AI call;
- produce credential-safe stable errors;
- commit identity, revision and links atomically;
- create zero rows on validation failure.

The snapshot command accepts the complete explicit member manifest and rejects any manifest that is not set-equal to the exact persisted candidate-pool membership.

## 17. Read API and workspace

### 17.1 Exact-ID APIs

```text
GET /investment-candidates/component-revisions/{component_revision_id}
GET /investment-candidates/snapshot-revisions/{snapshot_revision_id}
```

Both require:

- `as_of_cutoff=YYYY-MM-DD`
- `as_of_recorded_at_utc=<timezone-aware UTC>`

No endpoint selects the latest record by default. No name, ticker, similarity or code-prefix lookup is permitted.

### 17.2 Chinese-first workspace

Add a read-only `/investment-candidates` workspace requiring one exact snapshot-revision ID and both as-of boundaries.

The page displays:

1. snapshot purpose, rule version and chronology;
2. complete candidate-pool member count and integrity state;
3. highlighted top three current candidates when present;
4. full-universe table without hidden filtering;
5. separate industry-benefit and investment-candidate columns;
6. all component scores, states, weights and contributions;
7. price/valuation eligibility and provenance;
8. catalyst, risk, missing, disputed and falsification states;
9. deterministic reason codes;
10. explicit non-advisory notice.

The page contains no trade button, position control, target price, expected return or portfolio action.

## 18. Query and performance boundary

The implementation must use set-based reads with query count bounded independently of member count.

The initial workspace read must not load full evidence bodies for every member. It may show exact provenance identifiers and component summaries, then load owning-domain details only after explicit user action.

The architecture does not authorize a generic scoring engine or generic comparison framework. The read model remains product-local to Investment Candidate Intelligence v1.

## 19. Chronology and revision visibility

Every accepted write and read enforces both:

- information cutoff date;
- recorded-at UTC.

A component or upstream revision is visible only when both its information cutoff and recorded time are within the requested boundaries.

The snapshot revision cannot contain an upstream revision recorded after the snapshot recorded time, even when its information date is older.

Corrections append revisions. Existing component and snapshot revisions are immutable.

## 20. Golden path

The offline production-realistic fixture creates:

1. one exact candidate-pool revision containing exactly three memberships;
2. exact beneficiary and typed-semantics revisions for all three;
3. exact Company Research, expectation, valuation, catalyst, risk and quality revisions as required;
4. exact accepted Canonical Price and eligible Comparison Eligibility revisions for members with supported valuation context;
5. explicit component revisions with exact source links;
6. one deterministic snapshot revision.

Expected member outcomes:

- Member A: all gates pass, final score at least 75, status `priority_candidate`;
- Member B: business-quality score at least 70 and valuation or expectation score below 40, status `pricing_demanding`;
- Member C: one explicit critical missing input, status `evidence_insufficient` with no aggregate score.

All three memberships remain visible. The fixture verifies:

- exact set equality with the candidate pool;
- exact revision provenance;
- Decimal calculations and tie breaks;
- sorted reason codes;
- both as-of boundaries;
- exact-ID API output;
- Chinese-first full-universe workspace;
- zero hidden network.

## 21. Primary fail-closed path

The primary rejection fixture supplies a snapshot manifest that omits one candidate-pool member and attempts to use a newer compatible-looking revision for another member.

Expected result:

- stable public error `investment_candidate_universe_mismatch`;
- zero snapshot, revision, member, link or reason rows written;
- no fallback to a smaller universe;
- no automatic revision substitution.

Additional failures include:

- stale expected-latest revision;
- score out of range or malformed decimal;
- supported component without required links;
- disputed component included in aggregation;
- ineligible/stale/conflicting price used by valuation context;
- later-information leakage;
- active falsification incorrectly classified as priority/watch;
- unknown reason code;
- non-deterministic or duplicate priority ordinal.

## 22. Stop conditions

Return to architecture rather than improvising if implementation discovers:

- a component field without an authoritative owner;
- a required upstream revision cannot be reached through reviewed production boundaries;
- valuation meaning depends on parsing free text;
- priority requires an external consensus, news, social or fund-flow source;
- a score requires silent imputation or hidden reweighting;
- the complete candidate-pool universe cannot be frozen exactly;
- more than the one planned additive persistence boundary is required;
- project-level documents materially disagree.

## 23. Validation requirements for implementation

Strict implementation validation must include:

- component command/model tests;
- snapshot command/model tests;
- Decimal and threshold boundary tests;
- status precedence tests;
- complete-universe set-equality tests;
- stale expected-latest rollback;
- append-only mutation rejection;
- exact upstream revision and chronology tests;
- canonical-price/eligibility compatibility tests;
- missing, disputed, pending and falsification tests;
- deterministic tie-break and top-three tests;
- exact-ID API tests;
- GET-only and explicit-as-of tests;
- bounded query-count tests;
- SQLite migration tests;
- PostgreSQL migration round trip, constraints, concurrency and populated-downgrade refusal;
- full relevant regression;
- offline golden-path fixture demo;
- no-hidden-network tests.

## 24. Authorized future implementation file families

A later implementation Issue may authorize only the nearest existing product-local families:

- `.codex/tasks/issue-*-investment-candidate-*`
- `industry_alpha/investment_candidate_*`
- `backend/api/investment_candidate.py`
- minimal `backend/main.py` registration
- product-local template/static files for `/investment-candidates`
- `scripts/record_investment_candidate_component.py`
- `scripts/record_investment_candidate_snapshot.py`
- bounded `scripts/README.md`
- `migrations/env.py`
- `migrations/versions/20260722_0014_investment_candidate_intelligence.py`
- focused `tests/test_investment_candidate*`
- existing migration-head assertions where the only change is `20260722_0013` to `20260722_0014`
- bounded `docs/architecture_baseline.md` completion update.

Do not create a generic score framework, generic rule engine, generic portfolio engine or generalized product workspace.

## 25. Later roadmap, not included in v1

After this v1 is implemented and validated, separately governed phases may add:

1. normalized valuation metric contracts such as PE/PS/EV-to-EBITDA with explicit accounting-period and forecast semantics;
2. authorized market-attention data such as news, social interest, volume or fund-flow observations;
3. guarded AI drafts of component assessments for explicit human confirmation;
4. daily snapshot generation and change alerts;
5. research-priority change explanations.

Each addition must preserve the full beneficiary universe and non-advisory boundary.

## 26. Locked exclusions

This architecture does not authorize:

- external network, Provider, crawler, browser or ingestion changes;
- hidden consensus, news, social or fund-flow acquisition;
- broker connectivity or trade execution;
- portfolio, position or order state;
- buy/sell/hold instructions;
- target price, fair value or expected return;
- performance promises;
- AI-owned accepted state;
- free-text-derived scores;
- evidence-count-derived scores;
- missing-value imputation or silent reweighting;
- automatic relinking to newer revisions;
- existing-row mutation or backfill;
- release, tag or version change.

## 27. Independent approval text

The exact required architecture approval is:

`INVESTMENT CANDIDATE INTELLIGENCE PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`

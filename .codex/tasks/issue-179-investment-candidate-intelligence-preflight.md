# Issue #179 — Investment Candidate Intelligence Layer v1 Architecture Preflight

## Authority

- GitHub Issue: #179
- Required base: `ccb949beb08d25d4b91ae970b1e1781a09d92f8e`
- Risk tier: **Strict**
- Owner authorization: `进行下一阶段开发，完成目标实现` on 2026-07-22
- Architecture only; no production schema, migration, runtime, Provider, release or version change
- `docs/investment_candidate_intelligence_verification_correction.md` is the authoritative correction for verification-state semantics and supersedes only the conflicting verification portions of the main preflight.

## Objective

Define one implementable, local-first and non-advisory architecture that preserves the complete Stage 1 beneficiary candidate-pool universe and adds a separate transparent Investment Candidate overlay capable of identifying current priority candidates for research.

The architecture must support a user-facing answer to:

> After identifying all companies that benefit from an industry change, which companies are current investment candidates, why, what is already priced in, what remains unverified, and what could falsify the thesis?

The answer must remain research assistance rather than buy/sell/hold advice.

## Required product contract

```text
exact complete candidate-pool revision
  -> exact beneficiary / typed-semantics / company-research revisions
  -> exact canonical-price and Comparison Eligibility revisions
  -> explicit component assessments
  -> deterministic complete-universe snapshot
  -> transparent candidate bucket and bounded priority
```

No investment-candidate status may mutate, replace, filter or reclassify the owning Stage 1 beneficiary records.

## Required components

1. `industry_opportunity`
2. `beneficiary_strength`
3. `earnings_conversion`
4. `expectation_gap`
5. `valuation_context`
6. `catalyst_readiness`
7. `evidence_quality`
8. `risk_penalty`

For each component, close:

- authoritative owner and D-level;
- accepted value/state vocabulary;
- exact upstream revision links;
- rationale, evidence and falsification requirements;
- cutoff and recorded-time behavior;
- missing, disputed and not-applicable behavior;
- prohibition on free-text, Provider-name, code-prefix, evidence-count or AI inference.

## Required deterministic output

Candidate statuses:

- `priority_candidate`
- `watch_candidate`
- `awaiting_verification`
- `pricing_demanding`
- `evidence_insufficient`
- `not_current_candidate`

Any numeric score or ordering must expose component values, weights, contributions, penalties, rule version, missing treatment and deterministic tie breaks. No unexplained total score is permitted.

Pending and failed verification follow the correction contract: both require explicit closed item code plus bounded question text, both prohibit aggregation, pending yields `awaiting_verification`, and failed yields `not_current_candidate` after existing missing/disputed precedence.

## Required architecture decisions

- stable snapshot identity and append-only revisions;
- complete frozen membership copied exactly from one candidate-pool revision;
- exact member-level upstream revision graph;
- component assessment identity/revision model;
- deterministic aggregation rule and reason-code vocabulary;
- closed verification-state, materiality, item-code and question contract;
- Canonical Price and Comparison Eligibility use;
- valuation and expectation-gap boundaries;
- minimum additive schema;
- populated downgrade refusal before any drop;
- local JSON-only write commands with dry-run and expected-latest protection;
- exact-ID read-only APIs and Chinese-first `/investment-candidates` workspace;
- offline golden path, primary failure path and stop conditions.

## Golden path

One exact candidate-pool revision has three members. The fixture creates explicit accepted upstream records and component assessments so that deterministic snapshot output contains:

1. one `priority_candidate`;
2. one `pricing_demanding` member;
3. one `evidence_insufficient` member.

All three remain visible. Exact provenance, component contributions, reason codes, cutoff, recorded UTC and zero hidden network are verified.

## Primary failure path

Fail before any write if:

- any exact candidate-pool member is omitted, duplicated or substituted;
- any frozen revision lies outside either as-of boundary;
- a critical price/valuation input is stale, conflicting, rejected or ineligible;
- a component value requires hidden inference or an unowned default;
- a pending/failed verification lacks its closed item code and exact bounded question.

No partial snapshot, fallback selection or silent reweighting is allowed.

## Deliverables

- this task snapshot;
- `docs/investment_candidate_intelligence_preflight.md`;
- `docs/investment_candidate_intelligence_verification_correction.md`;
- Draft architecture PR based exactly on the required base;
- repository checks and author fixed-head handoff;
- independent fixed-head architecture review.

## Locked exclusions

No production implementation, schema, migration, external network, Provider, ingestion, browsing, crawling, news/social/fund-flow acquisition, target price, fair value, expected return, performance promise, buy/sell/hold output, position sizing, portfolio state, broker/trading capability, AI-owned accepted state, hidden inputs, missing-value imputation, existing-row mutation/backfill, release, tag or version change.

## Required approval text

`INVESTMENT CANDIDATE INTELLIGENCE PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`

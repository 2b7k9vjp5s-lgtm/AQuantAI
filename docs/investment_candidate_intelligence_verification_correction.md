# Investment Candidate Intelligence v1 — Verification Contract Correction

## Status and authority

- Architecture Issue: #179.
- Architecture PR: #180.
- Required base: `ccb949beb08d25d4b91ae970b1e1781a09d92f8e`.
- Risk tier: **Strict**.
- This correction resolves the independent fixed-head review findings on the first PR #180 head.
- It supersedes only the conflicting verification-state portions of sections 5.3, 7.5, 8.3, 8.4, 14.2 and 23 of `docs/investment_candidate_intelligence_preflight.md`.
- All other architecture decisions, exclusions and the exact eight-table boundary remain unchanged.

## Decision

Verification state is explicit analyst-owned D3 state. It cannot be inferred from free text, evidence count, Provider metadata, recency, UI state or AI output.

Every component revision stores:

- `verification_state`;
- `verification_material`;
- `verification_item_code`;
- `verification_question`.

The closed `verification_state` vocabulary remains:

- `verified`
- `pending`
- `failed`
- `not_applicable`

The closed `verification_item_code` vocabulary is:

- `certification`
- `order`
- `capacity`
- `production`
- `financial_confirmation`
- `customer_confirmation`
- `other_explicit`

`verification_question` is bounded analyst-authored text that states the exact unresolved or failed verification question. It is explanatory D3 content and cannot itself change a score or status outside the deterministic rules below.

## State constraints

The component write contract must enforce:

1. `verified`
   - `verification_material = false`;
   - `verification_item_code` is null;
   - `verification_question` is null.
2. `not_applicable`
   - `verification_material = false`;
   - `verification_item_code` is null;
   - `verification_question` is null.
3. `pending`
   - `verification_material = true`;
   - `verification_item_code` is required from the closed vocabulary;
   - `verification_question` is required and non-empty;
   - numeric aggregation is prohibited.
4. `failed`
   - `verification_material = true`;
   - `verification_item_code` is required from the closed vocabulary;
   - `verification_question` is required and non-empty;
   - numeric aggregation is prohibited.

V1 does not support non-material pending or failed verification. A future distinction requires a separately reviewed rule version rather than a hidden boolean interpretation.

## Aggregation eligibility correction

A numeric aggregate is allowed only when every component revision has:

- `assessment_state = supported`;
- `verification_state` in `verified / not_applicable`;
- complete exact input links;
- visibility at both as-of boundaries;
- no active falsification state;
- all existing Canonical Price and Comparison Eligibility gates satisfied.

Therefore:

- any `pending` verification produces no base score, business-quality score, risk-penalty points, final score, contribution amount or priority ordinal;
- any `failed` verification produces no numeric aggregate or priority ordinal;
- no missing weight is imputed or redistributed.

## Candidate-status precedence correction

After transaction-level integrity checks and the existing missing/disputed rules:

1. `failed` verification yields `not_current_candidate` with `verification_failed`;
2. `pending` verification yields `awaiting_verification` with `verification_pending`;
3. only fully verification-eligible members proceed to numeric scoring and the pricing/priority/watch rules.

The UI and exact-ID API must display both `verification_item_code` and `verification_question` whenever the state is `pending` or `failed`. The generic deterministic reason code remains stable; the closed item code identifies what is pending or failed without expanding the reason-code vocabulary combinatorially.

## Persistence correction

The exact eight-table design remains unchanged.

`investment_candidate_component_revisions` additionally owns:

- `verification_material BOOLEAN NOT NULL`;
- `verification_item_code VARCHAR(40) NULL`;
- `verification_question VARCHAR(2000) NULL`.

The migration must add database checks for:

- the closed verification-item vocabulary;
- the state/material/item/question combinations above;
- no nullable or default path that silently converts pending/failed verification into aggregation eligibility.

No ninth table, generic task framework or automatic verification workflow is authorized.

## Command and read contract

The component command must:

- reject unknown verification item codes;
- require the item code and question for pending/failed;
- reject either field for verified/not-applicable;
- reject `verification_material = false` for pending/failed;
- reject `verification_material = true` for verified/not-applicable;
- preserve the fields in dry-run output and append-only persistence.

The component and snapshot read surfaces must expose the stored fields unchanged. The snapshot command must apply the corrected status precedence before any score calculation.

## Required validation

Focused and regression tests must prove:

- pending verification blocks every aggregate field and yields `awaiting_verification`;
- failed verification blocks every aggregate field and yields `not_current_candidate`;
- verified/not-applicable components remain aggregation-eligible when all other gates pass;
- invalid state/material/item/question combinations fail before persistence;
- unknown item codes fail closed;
- API and workspace expose the exact item code and question;
- no migration table-count change and no existing-table mutation/backfill.

## Locked exclusions

This correction does not authorize external verification services, notifications, tasks, background jobs, Provider/network access, AI-owned verification state, automatic evidence acceptance, score inference, portfolio state, trading or any later roadmap capability.

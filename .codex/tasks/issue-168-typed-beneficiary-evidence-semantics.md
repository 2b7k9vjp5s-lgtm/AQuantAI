# Issue 168 — Typed Beneficiary Evidence Semantics v1

## Authority

- GitHub Issue: #168
- Risk tier: Strict
- Required base: `6f4d8aa8d8c8064e696a9c3fa2fe1632135bcacc`
- Architecture: Issue #164 / PR #165 fixed head `67fbf8dbe8577d0c33078ae6bff562a72b4277aa`
- Owner authorized implementation start on 2026-07-21.
- Issue #168 comments authorize the lower-risk API split at `backend/api/beneficiary_semantics.py` plus minimal registration in `backend/main.py`.
- Issue #168 comments authorize assertion-only Alembic head compatibility updates in five existing migration round-trip tests.

Implementation may proceed before PR #165 merges, but this implementation may not merge until the architecture fixed head is independently approved and the implementation fixed head is independently reviewed.

## Objective

Add one append-only semantic profile layer for an explicit existing Stage 1 beneficiary, with CLI-only writes, exact frozen beneficiary/map/driver/claim revisions, read-only API/page detail, explicit missing/conflict states and no inference, ranking, recommendation, price or trading semantics.

## Authorized file families

- this task snapshot;
- `migrations/env.py` and migration `20260721_0012_typed_beneficiary_evidence_semantics.py`;
- `industry_alpha/beneficiary_semantics_*.py`;
- `backend/api/beneficiary_semantics.py` and the minimal router registration in `backend/main.py`;
- `scripts/record_beneficiary_semantics.py` and command documentation;
- minimal `industry_research/static/industry_research.html` and `.js` integration;
- `tests/test_beneficiary_semantics*.py`;
- assertion-only head-version updates in `tests/test_benchmark_migration.py`, `tests/test_sector_migration.py`, `tests/test_stage1_beneficiaries_postgres.py`, `tests/test_stage2_company_research_postgres.py`, and `tests/test_stage2_expectations_valuation_postgres.py`.

## Required invariants

- Existing v0.5A-v0.6D tables and frozen links remain unchanged.
- Legacy `direct / secondary / potential` is preserved and never automatically mapped.
- New taxonomy is exactly `direct / conditional / indirect / conceptual` at version `aquantai.typed-beneficiary-evidence-semantics.v1`.
- Values are explicit analyst D3 judgments. Code validates; it never infers from names, codes, Provider text, rationale, claims or AI output.
- Positive assertion links are limited to claim revisions already frozen by the exact beneficiary revision.
- Evidence Ledger remains the only evidence owner.
- Missing, disputed and not-applicable are distinct.
- Local CLI is the only write path; API and page are read-only.
- All writes are atomic and append-only.
- Migration performs no backfill; populated downgrade fails before any drop.
- No network access, LLM calls, scores, rankings, valuation, recommendations, alerts, portfolio or trading.

## Validation

- focused vocabulary/model/command/query/API/UI/migration tests;
- exact cutoff, chronology, supersession and stale expected-latest coverage;
- no-network coverage;
- full CI with PostgreSQL and fixture demo;
- record exact base/head and changed-file inventory before review.

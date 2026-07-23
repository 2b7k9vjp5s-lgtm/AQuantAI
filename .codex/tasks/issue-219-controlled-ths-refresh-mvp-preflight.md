# Issue #219 — Controlled THS Data Refresh MVP Architecture Preflight

## Authority

- Governing Issue: #219.
- Product roadmap: #137.
- Accepted Provider architecture: Issue #190 / PR #191.
- Project-owner authorization: `按计划进去下一步开发` on 2026-07-23.
- Exact architecture base: `2e1f8000fe1e431142d07be718729962f65bb2cd`.
- Branch: `docs/controlled-ths-data-refresh-mvp-preflight`.
- Risk tier: **Strict Architecture Preflight**.
- Workflow: `.codex/WORKFLOW.md`.

## Objective

Close the non-secret, account-specific capability gap between the accepted generic THS Provider architecture and a later bounded Strict implementation Issue.

The preflight must produce:

1. one owner-completable secret-free account capability manifest;
2. deterministic readiness states per capability;
3. one bounded 190-A Provider foundation and instrument-identity implementation boundary;
4. exact migration, command, read, test, rollback and failure-path candidates;
5. one explicit final gate result.

## Current gate result

`blocked_pending_account_facts`

This result remains authoritative until every required first-slice contract fact is supported by owner-provided non-secret evidence. Public documentation, Provider reputation and inferred account access are insufficient.

## Authorized files

- `.codex/tasks/issue-219-controlled-ths-refresh-mvp-preflight.md`;
- `docs/controlled_ths_refresh_mvp_preflight.md`;
- `docs/ths_account_capability_manifest_template.md`;
- optional focused `docs/architecture_baseline.md` synchronization only if needed before fixed-head review.

No production code, schema, migration, dependency, workflow, credential or live request is authorized.

## Required decisions

- exact capability-manifest fields and allowed states;
- evidence reference and fingerprint treatment;
- source authorization/capability state transitions;
- credential-profile boundary and redaction;
- exact host/endpoint allowlisting and request-plan validation;
- immutable raw-byte contract and ceilings;
- request fingerprint, idempotency and changed-content behavior;
- Provider symbol candidate versus accepted Listed Instrument mapping;
- exact commands and reads for a later implementation;
- first-slice migration/rollback/downgrade candidate;
- zero-network CI and disabled opt-in smoke-test separation;
- deferred 190-B and 190-C data families.

## Required golden path

The architecture must define an offline path from a reviewed secret-free capability manifest through dry-run request planning, sanitized fixture binding, immutable raw capture, exact instrument candidate review and exact provenance readback, with no automatic downstream promotion.

The path is specification-only until owner-provided evidence and sanitized fixtures exist.

## Primary failure path

Incomplete entitlement, host, endpoint, limits, retention, identity, chronology or fixture evidence keeps the capability blocked. The project must not probe the service, infer missing facts, use browser replay or select an alternate Provider.

## Locked exclusions

No:

- production adapter or live network;
- credential/token/account identifier;
- schema or migration implementation;
- browser session, Cookie/CAS ticket, reverse-engineered signature or undocumented endpoint;
- generic multi-provider framework or fallback;
- scheduler, background worker, notification or Daily Radar;
- automatic Canonical Price, Evidence Ledger, financial, taxonomy, beneficiary or Investment Candidate mutation;
- AI-owned accepted state;
- recommendation, target price, position sizing, broker or trading behavior;
- release, tag or version change.

## Delivery gates

1. Keep the PR Draft.
2. Verify base-to-head remains documentation-only.
3. Validate no secrets, credentials, account identifiers or copied Provider datasets exist.
4. Obtain process-independent fixed-head architecture review using:

`AUTHORIZED CONTROLLED THS DATA REFRESH MVP PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>`

5. Resolve all review threads.
6. Await separate project-owner authorization before merge.
7. Do not create a production implementation Issue while the result is `blocked_pending_account_facts`.
8. Any new commit invalidates fixed-head validation and review.
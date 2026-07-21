# Codex Repository Workflow

This file defines the standing execution rules for Codex work in AQuantAI.

## Authority order

1. The linked GitHub Issue is authoritative for product scope, acceptance criteria, exclusions and status when an Issue is required.
2. `docs/architecture_baseline.md` is authoritative for project state, domain ownership, dependency direction and shared architecture invariants.
3. A matching `.codex/tasks/` file is required only for Strict work or when an Issue explicitly requests one.
4. The active PR contains the change and validation record.
5. Explicit project-owner chat authorization may start work, approve a governance transition or authorize merge, but must be summarized in the Issue or PR before completion.

If Issue scope, architecture ownership, branch state or PR instructions materially conflict, stop the affected change and report the conflict. Do not use process formality to block unrelated safe work.

## Risk tiers

Every change must be classified before editing.

### Light

Use Light for:

- documentation, copy, styles and static layout;
- tests that do not change product contracts;
- internal refactors with unchanged public behavior;
- small bug fixes with no schema, external-data, AI-write, identity or destructive-history impact.

Process:

- Issue and task snapshot are optional;
- use one branch and one PR;
- run targeted validation appropriate to the changed files;
- author-side review plus passing checks is sufficient;
- merge still requires explicit owner authorization.

### Standard

Use Standard for:

- new read-only APIs over accepted models;
- local CLI or ordinary domain logic using existing schemas;
- bounded front-end and back-end features with no Strict trigger;
- additive behavior confined to one main domain capability.

Process:

- one implementation Issue and one PR;
- record objective, ownership, contracts, cutoff rules, migration decision, tests and exclusions in the Issue or PR;
- no separate Architecture Preflight PR is required;
- use one focused review and targeted plus regression validation;
- exact individual filenames are not mandatory when an authorized directory or file family is clear;
- merge requires explicit owner authorization.

### Strict

Use Strict only when a change includes any of:

- database schema or migration;
- external network, Provider, ingestion, crawling, browsing or data acquisition;
- AI data transmission, AI-owned acceptance or automated persistence;
- authentication, authorization or identity controls;
- destructive operations, backfill, history rewrite or downgrade risk;
- ranking, scoring, recommendations, valuation, target price, expected return, portfolio or trading semantics;
- modification of a core cross-domain contract or frozen-history boundary.

Process:

- one architecture note or Architecture Preflight and one implementation PR;
- a `.codex/tasks/` snapshot is required;
- one independent fixed-head architecture review before production merge;
- one independent fixed-head implementation review before production merge;
- implementation may begin in parallel after the architecture note exists and the owner explicitly authorizes it, but the implementation PR must not merge before architecture approval;
- avoid extra synchronization, reset or consolidation PRs unless a concrete blocker requires them.

Do not escalate a task merely because it is large. Escalate only because its risk matches a Strict trigger.

## Definition of Ready

### Light

A clear requested result and bounded changed area are sufficient.

### Standard

The Issue or PR must state:

- one objective;
- accepted inputs and outputs;
- authoritative owner for material fields;
- selectors, cutoff and missing-data behavior;
- migration decision;
- acceptance tests and exclusions.

### Strict

The architecture note must additionally establish:

- exact revision and provenance boundaries;
- one production-realistic offline golden path;
- the most important failure path;
- migration, rollback and downgrade behavior;
- explicit stop conditions and locked exclusions.

Green CI alone does not establish domain ownership or product meaning.

## Start protocol

Before editing:

1. Inspect the current base, relevant Issue or request, architecture baseline, active PR and latest CI relevant to the change.
2. Confirm the risk tier and summarize it in the Issue or PR.
3. Confirm the branch base and avoid unrelated branches and PRs, including PR #38.
4. Reuse the existing branch and PR when scope is unchanged.
5. For Standard and Strict work, authorize a directory or file family where practical instead of predicting every helper filename.

## Implementation rules

- Preserve the local-first, personal-use, research-only and non-advisory boundary.
- Keep deterministic calculations, canonicalization and workflow state outside LLM ownership.
- Do not add broker connectivity, real orders, trading buttons, automated trading or investment recommendations.
- Do not access external networks during imports, FastAPI startup, tests, CI, fixture demos or ordinary read use.
- Never put credentials, tokens, connection strings or secrets in source, logs, fixtures, Issues, PRs or task files.
- Use explicit selectors, cutoff dates, provenance, missing-data behavior and fail-closed semantics.
- Bind exact accepted revisions when frozen research history is required; do not select newer compatible-looking records.
- A fixture success path must use fields and contracts reachable through the reviewed production boundary.
- Do not infer product meaning from provider name, free text, security code, company name or an unreviewed default.
- Do not silently broaden scope into a later roadmap stage.

## Golden-path-first rule

Before expanding a rejection matrix, prove one complete success path using production-realistic offline inputs. The path must demonstrate:

- every required field has an authoritative source;
- fixture data does not add information unavailable to production;
- canonical values have one owner;
- output meaning does not depend on hidden inference.

## Reset threshold

Return to architecture work only when:

- a material field has no authoritative owner;
- the reviewed production boundary cannot reach the success path;
- core meaning depends on free-text, provider-name, security-code or AI inference;
- the task unexpectedly introduces more than one new infrastructure boundary;
- project-level documents materially disagree.

Do not require two failed planning rounds when the ownership or reachability failure is already clear.

## Consolidation cadence

Consolidation is not mandatory after every two slices.

Trigger it when either:

- 5–6 implemented domain slices have accumulated since the last review; or
- there is concrete evidence of duplicated models, validators or serializers, schema/frozen-link complexity, inconsistent APIs, material test-duration growth, or conflicting ownership.

A consolidation review may decide no refactor is needed. Never generalize only for aesthetic uniformity.

## Validation and reporting

- Match validation effort to risk and changed surfaces.
- Documentation-only changes use Markdown, links and repository checks; full database regression is required only when executable contracts or runtime configuration are affected.
- Standard implementation uses focused tests plus relevant regression coverage.
- Strict implementation uses focused tests, full relevant regression and the offline golden path.
- Record base/head, risk tier, changed file families, validation results, limitations and exclusions in the PR.
- Verify the complete base-to-head inventory stays within authorized directories or file families.
- Keep Strict architecture and implementation PRs Draft until their required reviews; Light and Standard PRs may become Ready after author verification and passing checks.

## Independent review

Independent fixed-head review is mandatory only for Strict architecture and Strict implementation work, or when the owner explicitly requests it.

Review should focus on:

- scope and ownership;
- frozen revision/provenance integrity;
- migration and rollback safety;
- hidden network or inference paths;
- test sufficiency;
- prohibited recommendation, price or trading semantics.

Do not generate exhaustive ceremonial checklists when a concise risk-focused review is sufficient.

## Transition rule for PR #165

PR #165 remains a Strict architecture artifact. Its implementation may begin after explicit owner authorization, but neither PR #165 nor the related production implementation may merge without the required independent fixed-head architecture approval. Avoid additional planning layers between the approved architecture and implementation.

## Completion actions

Explicit project-owner authorization is always required before:

- merging a PR;
- closing an implementation Issue as completed;
- starting the next roadmap phase;
- creating a release or tag;
- changing the project version.

Never rebase or force-push reviewed fixed-head history. Never create a migration outside an authorized Strict implementation Issue.
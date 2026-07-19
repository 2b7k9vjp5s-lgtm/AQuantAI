# Codex Repository Workflow

This file defines the standing execution rules for Codex work in AQuantAI.

## Authority order

1. The linked GitHub Issue is authoritative for product scope, acceptance criteria, exclusions and status.
2. `docs/architecture_baseline.md` is authoritative for project state, domain ownership, dependency direction and shared architecture invariants.
3. The matching file under `.codex/tasks/` is the executable snapshot for the current planning, implementation or review cycle.
4. The active Draft PR contains the change and validation record.
5. A chat message starts an already authorized action; it does not silently override GitHub scope or architecture ownership.

If the Issue, architecture baseline, task file, branch state or PR instructions conflict, stop without changing code and report the conflict in the Issue and PR.

## Work types

Every Issue must identify exactly one work type:

- architecture decision or documentation reset;
- task synchronization/planning;
- application implementation;
- consolidation/refactoring characterization;
- release or operational handoff.

A planning Issue does not authorize application implementation. A documentation Issue does not authorize models, migrations, APIs, fixtures, tests or behavior changes.

## Architecture Preflight

Before a new feature Issue is created, the architecture reviewer must establish:

1. the user problem and why existing capability is insufficient;
2. the authoritative domain owner for every material field;
3. the real provider, persisted record or accepted upstream revision supplying every input;
4. one production-realistic offline golden path;
5. the most important failure path;
6. dependency, migration and runtime-surface impact;
7. conflicts with existing architecture or roadmap documents;
8. the smallest viable slice and explicit exclusions.

Do not use a Codex task file to discover fundamental field ownership, provider reachability or product meaning.

## Definition of Ready

Task synchronization or implementation may begin only when the linked Issue contains:

- one unambiguous objective;
- accepted input and output contracts;
- an explicit field/domain ownership table;
- a reachable production-realistic golden path;
- fixture/provider contract-parity evidence;
- exact selectors, cutoff and chronology rules;
- an explicit migration decision;
- bounded scope with no more than one main domain capability and one infrastructure change;
- acceptance tests, exclusions and stop conditions.

Green CI from prior work does not satisfy these requirements by itself.

## Start protocol

Before editing:

1. Fetch `origin` and inspect the Issue, `docs/architecture_baseline.md`, task file, Draft PR, latest review and latest CI result.
2. Confirm repository, branch, base commit and required ancestor SHA.
3. Confirm the Issue work type and that its authorization matches the requested files and behavior.
4. Confirm there are no unexpected commits after the reviewed head. Task-synchronization commits that only change `.codex/` are allowed only when the task explicitly identifies them.
5. Keep the existing branch and Draft PR unless the task requires a new one.
6. Do not modify unrelated branches or pull requests, including PR #38.

## Implementation rules

- Preserve the local-first, personal-use, research-only and non-advisory boundary.
- Keep deterministic calculations, canonicalization and workflow state outside LLM ownership.
- Do not add broker connectivity, real orders, trading buttons, automated trading or investment recommendations.
- Do not access external networks during imports, FastAPI startup, tests, CI, fixture demos or ordinary read use.
- Never put credentials, tokens, connection strings or secrets in source, logs, fixtures, Issues, PRs or task files.
- Use explicit selectors, cutoff dates, provenance, missing-data behavior and fail-closed semantics.
- Bind exact accepted revisions when the architecture requires frozen research history; do not select newer compatible-looking records.
- A fixture success path must use fields and contracts reachable through the reviewed production adapter boundary.
- Do not silently broaden scope, create a later-phase entity or begin a later roadmap stage.

## Golden-path-first rule

Before expanding a rejection matrix, prove one complete success path using production-realistic offline inputs. The path must demonstrate:

- the actual adapter or persistence contract can produce every required field;
- canonical values have one authoritative owner;
- fixture data does not add information unavailable to the production path;
- the output has the intended domain meaning without free-text, provider-name, security-code or fallback inference.

A large negative-test plan cannot compensate for an unreachable success path.

## Reset threshold

Stop the current plan and return to architecture preflight when any of the following occurs:

- two rounds of foundational planning blockers;
- a reviewed production adapter cannot reach the planned success path;
- a material field has no single authoritative owner;
- core meaning depends on provider name, free text, security-code inference or an unreviewed default;
- one slice requires multiple new infrastructure boundaries;
- project-level documents materially disagree about the feature.

Provider reachability or ownership failure can trigger immediate reset without waiting for two rounds. Preserve the branch and review history; close superseded work without merge and create a new architecture Issue rather than endlessly extending the task file.

## Consolidation cadence

After every two domain slices, pause feature expansion for a consolidation review covering:

- current-state documentation;
- repeated models, repositories, validators and serializers;
- schema and frozen-link growth;
- test count, duration and cross-product growth;
- API consistency;
- next-stage input reachability and field ownership.

A consolidation review may decide to keep stable schemas unchanged. Do not generalize merely for aesthetic uniformity.

## Validation and reporting

1. Run every command listed in the task file.
2. Record exact pass, skip and warning counts plus environment limitations.
3. Update the Draft PR and linked Issue with:
   - base and head SHA;
   - work type and authorization state;
   - architecture and data-contract decisions;
   - changed files;
   - exact validation results;
   - demonstration output where authorized;
   - known limitations, debt and exclusions.
4. Verify the complete base-to-head changed-file inventory matches the authorized list.
5. Keep the PR Draft unless the task explicitly authorizes Ready status.
6. Stop after synchronization and wait for ChatGPT review.

Green CI is necessary regression evidence, but architecture acceptance also requires domain ownership, production reachability, fixture parity, explicit semantics and scope coherence.

## Prohibited completion actions

Unless the project owner explicitly authorizes them in chat and the authorization is synchronized to GitHub:

- do not merge a PR;
- do not close the implementation Issue as completed;
- do not create a release or tag;
- do not change the project version;
- do not start the next roadmap phase;
- do not create a migration outside the exact authorized implementation task;
- do not rebase or force-push reviewed history.
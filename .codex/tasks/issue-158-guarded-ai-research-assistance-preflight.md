# Issue #158 — Guarded AI Research Assistance v1 Architecture Preflight

## Authority

- Work type: Architecture Preflight, documentation only.
- Required base: `bd8e1136b3805fd7286a9b197bbd3cfa141c9fc0`.
- Branch: `docs/guarded-ai-research-assistance-preflight`.
- Related roadmap: Issue #137.
- Related route reset: Issue #156 / PR #157.
- Deferred ingestion design: Issue #154 / closed-unmerged PR #155.
- Release remains `0.2.0`.

## Objective

Define the smallest useful Guarded AI Research Assistance v1 over existing accepted persisted Company Research data.

The user explicitly selects one persisted `company_research_id` and one optional `as_of_cutoff`, previews the exact deterministic input, and explicitly requests a clearly labeled D3 research draft.

The draft may summarize evidence-backed context, expose supporting and conflicting evidence, identify missing proof, propose research questions and provide a human review checklist. It must not create or mutate accepted research state.

## Authorized files

1. `docs/guarded_ai_research_assistance_preflight.md`
2. `.codex/tasks/issue-158-guarded-ai-research-assistance-preflight.md`

No other file is authorized.

## Required decisions

The preflight must settle:

1. one explicit `company_research_id` identity and optional cutoff;
2. deterministic immutable input manifest and fingerprint;
3. reuse of the accepted Company Research fixed-query boundary;
4. local input preview before any model request;
5. D3-only structured output with manifest-ID citations;
6. ephemeral-only v1 with no new persistent state;
7. model adapter isolation from database and deterministic calculations;
8. one explicit runtime AI provider profile, no default and no fallback;
9. opt-in remote call only after explicit user action;
10. no browsing, search, crawling, tools or evidence acquisition;
11. prompt-injection treatment of all evidence text as untrusted data;
12. credential, privacy, redaction and provider data-use boundaries;
13. token, cost, timeout, cancellation, retry and failure contracts;
14. fake/local adapter tests with no real remote calls in tests or CI;
15. exact implementation candidate files, tests, exclusions and stop conditions.

## Accepted smallest-slice direction

Unless characterization disproves it, the preflight should accept:

- company-scoped generation only;
- no ResearchCase-wide, industry-wide or multi-company generation;
- existing `CompanyResearchWorkspaceContract` as the only data source;
- manifest builder and prompt projection as deterministic application code;
- adapter receives no database/session/repository object;
- ephemeral response only;
- no schema or migration;
- one explicit OpenAI-compatible HTTPS provider profile configured by environment variables;
- no built-in provider URL, model, key or silent fallback;
- strict structured output validation;
- manifest citations only;
- no generic agent framework, tool calling, vector database or retrieval layer;
- no release or version change.

## Candidate routes

- `GET /company-research/research/{company_research_id}/ai-draft-input?as_of_cutoff=YYYY-MM-DD`
- `POST /company-research/research/{company_research_id}/ai-drafts`

The implementation may add one explicit action to the existing `/company-research` page only after a separate Product/Architecture implementation task is authorized.

## Required invariants

- no silent identity or cutoff default;
- no model call during page load, startup, imports, ordinary reads, tests, CI or fixture demos;
- no model access to database, filesystem, credentials other than its explicit API key, or market-data Provider credentials;
- no AI-owned record selection, cutoff, ordering, fingerprint, calculation or classification;
- no automatic EvidenceItem, Claim, ClaimEvidenceLink, Stage 1 or v0.6A-v0.6D mutation;
- no automatic identity acceptance, evidence grade or derivation promotion;
- no ranking, scoring, recommendation, target price, expected return, alert, portfolio or trading state;
- no accepted-history mutation;
- no hidden provider/model fallback;
- all generated text remains visibly D3 draft assistance.

## Validation

- base-to-head diff contains exactly the two authorized files;
- preflight records exact input/output contracts;
- query budget and deterministic manifest path are explicit;
- ephemeral/no-schema decision is explicit;
- provider profile and no-fallback rules are explicit;
- privacy, prompt-injection, credentials, cost and failure boundaries are explicit;
- implementation file candidate list is exact enough for a later bounded task;
- tests include fake/local adapter, invalid citations and malicious evidence text;
- full existing pytest and fixture demo remain required;
- Draft PR stays open/unmerged pending independent fixed-head Definition-of-Ready review.

## Stop conditions

Stop and do not recommend implementation if the useful slice requires:

- inferred identity or silent fallback;
- model-owned data selection or deterministic logic;
- browsing, tools or external evidence acquisition;
- accepted-state mutation;
- a generic autonomous-agent framework;
- unresolved secrets or provider data-use handling;
- real remote calls in tests/CI;
- unbounded input, cost or retries;
- ranking, recommendation or price-judgment semantics;
- weakening existing revision, cutoff, provenance or append-only rules.

## Completion gate

Do not create an implementation Issue, write production code, mark the PR ready, merge or close Issue #158 without:

1. author review at one fixed HEAD;
2. successful CI at that exact HEAD;
3. independent Definition-of-Ready approval naming that exact HEAD;
4. explicit owner authorization.
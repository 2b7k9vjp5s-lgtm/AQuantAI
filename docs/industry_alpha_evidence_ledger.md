# Industry Alpha Evidence Ledger v0.5A

## Scope

v0.5A is a local, append-only record of human-entered or deterministic fixture research material. It records provenance, revisions, conflicts, and follow-up verification. It does not fetch or summarize sources, score industries, map beneficiaries, run an LLM, recommend securities, or trade.

The ledger uses the existing SQLAlchemy engine/session boundary and PostgreSQL database. Migration `20260718_0005` adds only v0.5A objects and does not alter market-data or Market Cockpit tables.

## Relational Model

| Table | Immutable purpose | Stable key |
| --- | --- | --- |
| `research_cases` | Case identity and origin only | UUID and unique `case_key` |
| `research_case_revisions` | Title, question, workflow state, conclusion status, cutoff, and supersession history | `(case_id, revision_no)` |
| `evidence_items` | User-assigned A/B/C/D evidence and provenance | UUID; optional unique `(case_id, content_fingerprint)` |
| `claims` | Claim identity only | UUID and unique `(case_id, claim_key)` |
| `claim_revisions` | Versioned fact or inference text and status | `(claim_id, revision_no)` |
| `claim_evidence_links` | `supports`, `contradicts`, or `context` relation to an exact claim revision | Exact revision/evidence/relation tuple |
| `case_revision_claim_links` | Exact claim revisions frozen into a case revision as conclusion, context, or risk | Exact case revision/claim revision/role tuple |
| `verification_items` | The revision-specific `后续验证清单` | `(case_revision_id, item_no)` |

Workflow state (`open`, `paused`, `completed`, `archived`) and formal conclusion status (`unassessed`, `insufficient_evidence`, `supported`, `disputed`, `rejected`) are independent fields. Neither is inferred from the other. A completed revision must be created in the same transaction as at least one verification item.

## Evidence And Claims

Evidence grades are user-assigned provenance classifications:

- `A`: primary official, regulatory, filing, statistical-authority, or directly attributable first-party evidence.
- `B`: attributable secondary research, media, or industry evidence with a discernible method.
- `C`: attributable indirect or tertiary context.
- `D`: unverified lead, rumor, community assertion, or concept-stock list.

Facts cannot carry inference confidence or basis. Every inference requires `low`, `medium`, or `high` confidence and a non-empty basis. A supported claim revision requires at least one supporting A/B/C item. D-only support is rejected. A disputed claim revision requires contradictory evidence, and a revision with visible contradiction cannot be supported.

A supported case conclusion freezes at least one exact supported conclusion claim, each backed by A/B/C support and free of contradiction. A disputed case conclusion freezes at least one disputed or contradicted conclusion claim. Conflicts, D-grade leads, and missing evidence remain visible; later revisions never erase them.

## Commands And Immutability

Command services provide transactional operations for case creation, case revision append, evidence append, claim creation/revision append with links, standalone compatible links, and verification metadata. Revision numbering locks the stable case or claim identity and assigns `max(revision_no) + 1`; database uniqueness remains the final guard.

Accepted rows have no update/delete repository method. A SQLAlchemy session guard rejects ordinary ORM updates and deletes and rolls back the transaction. Corrections use a new revision or superseding evidence record. Duplicate identities, duplicate fingerprints, invalid status promotion, and cross-case links reject the complete command without partial rows.

Every append also enforces exact monotonic UTC recording time. A revision cannot predate its stable identity or prior revision; evidence cannot predate its case or superseded evidence; links cannot predate either endpoint; frozen conclusion membership cannot depend on later-recorded qualifying evidence or links; and checklist items cannot move backward relative to their case revision or prior item. Invalid timestamps are rejected without clamping and the complete command rolls back.

Required text fields accept strings only. Optional text fields accept only strings or `None`; blank optional strings normalize to `None`. Numbers and arbitrary objects are never converted with `str()`.

## Historical Cutoff

For `as_of_cutoff=D`, a dated row is visible only when both are true:

```text
information_cutoff_date or information_date <= D
UTC_DATE(recorded_at_utc) <= D
```

Rows without an independent information date additionally require their parent endpoints to be visible and require their own UTC recording date to be no later than `D`. This applies to evidence links, frozen claim membership, conflicts, and verification items. Therefore an old document entered later does not leak into an earlier view.

The query returns the latest visible case revision, the latest visible revision for each claim, and complete visible revision histories. Omitting `as_of_cutoff` means all currently recorded history; no hidden wall-clock cutoff is applied. Sorting is stable by case/claim keys, revision numbers, evidence dates/timestamps/UUIDs, link relation, and checklist item number.

## Read-Only API

```text
GET /industry-alpha/cases
GET /industry-alpha/cases/{case_id}
```

Both routes accept optional ISO `as_of_cutoff=YYYY-MM-DD`. A missing or cutoff-invisible case returns 404, an invalid cutoff returns 422, and unavailable database configuration/schema returns 503. Responses include evidence grades, explicit contradiction entries, frozen memberships, `verification_items`, the Chinese `后续验证清单` label, and research-only disclaimers. POST, PUT, PATCH, and DELETE routes are not present.

Configuration failures use a fixed public 503 message. Database URLs, passwords, local paths, driver errors, and exception details are never echoed in the response.

## Offline Demo

```bash
python -m scripts.demo_evidence_ledger
```

The isolated fixture contains two case revisions, a fact, an inference, A/B/C evidence, a D-grade contextual lead, a contradiction, and a completed revision with follow-up verification. Its earlier cutoff excludes the later contradiction, revision, and checklist. It uses no network and does not write the configured database.

## Exclusions

v0.5A does not implement industry-chain conclusions, drivers, bottlenecks, value-pool findings, company mappings, Stage 2 research, valuation, watchlists, portfolios, provider or LLM execution, scraping, scheduling, recommendations, signals, broker connectivity, orders, or trading. It is research record-keeping, not investment advice.

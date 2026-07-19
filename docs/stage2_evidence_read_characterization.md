# Stage 2 Evidence Read Serialization Characterization

## Status

Issue #92 / PR #93 reviewed the v0.6B-v0.6D evidence read serializers and accepted the decision to keep them domain-local. PR #93 was squash-merged as `e97762eba916e64299965a33b574870b1dad46e0`.

- Released version remains `0.2.0`.
- Merged capability stage remains v0.6D.
- Accepted application/consolidation implementation baseline remains `782b2362e1252aa87b21f7aa58f764837f5adb71` because this characterization is docs-only.
- Migration decision: no migration.
- No serializer implementation Issue follows from this report.

## Reviewed scope

The review compared the private evidence payload builders in:

- `stage2_expectations_query.py`;
- `stage2_assessments_query.py`;
- `stage2_judgments_query.py`.

Public query contracts, revision payloads and repository row containers were inspected only to determine ownership.

## Shared mechanics

All three serializers currently:

1. index claim revisions, claim identities, source evidence links and evidence items by ID;
2. select owner claim/evidence links visible at the requested cutoff;
3. sort frozen claim links by stringified claim revision ID;
4. collect evidence rows by claim revision;
5. emit the same evidence-item fields: link ID, evidence ID, grade, relation, source title, information date and recorded UTC;
6. count grades A-D;
7. project `contradicts` links into the same conflict fields;
8. sort evidence by relation, grade and evidence ID;
9. sort claims, conflicts and missing-evidence rows deterministically;
10. return tuple collections plus an ordered A-D grade-count mapping.

These similarities are real, but they do not define a safe shared domain contract.

## Material differences

### v0.6B claim contract

The v0.6B nested claim payload contains identity/revision IDs, revision number, statement, status, information cutoff date and evidence. It does not emit `claim_kind`, inference fields or claim `recorded_at_utc`.

Its missing-evidence reason is the domain-specific text:

`no evidence was frozen at this v0.6B snapshot boundary`

### v0.6C and v0.6D claim contract

The v0.6C and v0.6D nested claim payloads additionally contain `claim_kind`, `inference_confidence`, `inference_basis` and claim `recorded_at_utc`. They currently share the missing-evidence reason `尚未获得可靠公开证据`.

That matching shape is an implementation observation, not an independently versioned neutral contract.

### Link ownership and row containers

- v0.6B and v0.6C derive an owner revision field from a domain `kind`.
- v0.6D uses `judgment_revision_id` directly.
- v0.6B exposes source links as `claim_evidence_links`.
- v0.6C and v0.6D expose them as `source_evidence_links`.

A whole serializer would require reflection, field-name parameters, callbacks or adapter objects.

### Timestamp error boundary

v0.6B and v0.6C use the accepted nullable required-UTC helper contract. v0.6D retains a non-null local timestamp policy with different malformed-input behavior.

A shared serializer must not route v0.6D timestamps through `stage2_query_values` and silently change that behavior.

## Options evaluated

### Generic ORM-aware serializer

Rejected. It would centralize reflection and policy switches rather than domain meaning and would couple neutral code to three row-container shapes.

### Neutral projection DTOs plus a pure serializer

Technically possible but not ready. Domain adapters would retain most selection and mapping logic, while the shared layer would own only sorting, grade counting and conflict/missing assembly. This adds types and conversion code without an accepted neutral claim projection or demonstrated benefit.

### Lower-level evidence-item/finalization helpers

Not justified. These operations are short and readable in place; extraction would increase indirection while leaving domain selection and claim projection duplicated.

### Share only v0.6C and v0.6D

Not ready. Owner-link selection and timestamp error policy still differ, and current output equality is not a reviewed neutral contract.

## Accepted decision

Keep the v0.6B-v0.6D evidence read serializers local.

The candidate does not meet Definition of Ready because:

- no neutral claim projection is accepted;
- domain-specific missing-evidence text must remain visible;
- v0.6D timestamp error behavior must remain independent;
- a shared helper would require reflection, callbacks or projection adapters;
- no concrete defect or new domain demonstrates that the abstraction pays for itself.

The current duplication is explicit and safer than a generic serializer with hidden policy switches.

## Re-evaluation triggers

Reconsider only if:

1. a new reviewed domain requires the exact v0.6C/v0.6D claim/evidence contract;
2. the nested evidence payload becomes an explicit versioned neutral public contract;
3. a cross-domain defect demonstrates that local implementations cannot be kept compatible safely;
4. accepted projection DTOs already exist for another independent reason;
5. v0.6D timestamp-null/error semantics are deliberately unified through a separate reviewed decision.

Any re-evaluation requires a new Architecture Preflight, Issue, tests and migration decision.

## Preserved responsibilities

Each domain query module continues to own:

- owner-link selection and cutoff filtering;
- row-container attribute names;
- claim projection fields;
- missing-evidence wording;
- timestamp/error policy;
- conflict and aggregate placement in public contracts;
- collection types and deterministic ordering.

## Explicit exclusions

No serializer extraction, projection DTO, public payload change, evidence text change, v0.6D query-value change, repository, command, model, schema, fixture, API, provider, dependency, migration, v0.6E, v0.7, release, UI, deployment or PR #38 work.

## Final conclusion

Evidence read serialization has been reviewed and intentionally remains local. The next independent consolidation gate is command conflict/integrity characterization; this report does not authorize that implementation.
# Stage 2 Evidence Read Serialization Characterization

## Status

Issue #92 reviews the v0.6B-v0.6D evidence read serializers at accepted `main` commit `9ed4c3528c9500e7afbf64627a1f9df92c4761f9`.

This is characterization only. Released version remains `0.2.0`, capability stage remains v0.6D, and no migration is required.

## Reviewed scope

The review compared the private evidence payload builders in:

- `stage2_expectations_query.py`;
- `stage2_assessments_query.py`;
- `stage2_judgments_query.py`.

Public query contracts, revision payloads and repository row containers were inspected only to determine ownership. No implementation is authorized by this report.

## Shared mechanics

All three serializers currently:

1. index claim revisions, claim identities, source evidence links and evidence items by ID;
2. select owner claim/evidence links visible at the requested cutoff;
3. sort frozen claim links by stringified claim revision ID;
4. collect evidence rows by claim revision;
5. emit the same evidence-item fields:
   - `claim_evidence_link_id`;
   - `evidence_id`;
   - `evidence_grade`;
   - `relation`;
   - `source_title`;
   - `information_date`;
   - `recorded_at_utc`;
6. count grades A-D;
7. project `contradicts` links into the same conflict fields;
8. sort evidence by relation, grade and evidence ID;
9. sort claims, conflicts and missing-evidence rows deterministically;
10. return tuple collections plus an ordered A-D grade-count mapping.

These similarities are real, but they do not by themselves define a safe shared domain contract.

## Material differences

### v0.6B claim contract

The v0.6B claim payload contains:

- claim identity and revision IDs;
- revision number;
- statement;
- claim status;
- information cutoff date;
- evidence.

It does not emit `claim_kind`, inference fields or claim `recorded_at_utc` in this nested payload.

Its missing-evidence reason is the domain-specific English text:

`no evidence was frozen at this v0.6B snapshot boundary`

### v0.6C and v0.6D claim contract

The v0.6C and v0.6D nested claim payloads additionally contain:

- `claim_kind`;
- `inference_confidence`;
- `inference_basis`;
- claim `recorded_at_utc`.

They currently share the missing-evidence reason `尚未获得可靠公开证据`.

The matching output shape is an implementation observation, not an independently versioned public neutral contract.

### Link ownership and row-container differences

- v0.6B and v0.6C derive an owner revision field from a domain `kind`.
- v0.6D uses `judgment_revision_id` directly.
- v0.6B exposes source links as `claim_evidence_links`.
- v0.6C and v0.6D expose them as `source_evidence_links`.

A whole-serializer helper would therefore require reflection, field-name parameters, callbacks or adapter objects.

### Timestamp error boundary

v0.6B and v0.6C use the accepted nullable required-UTC helper contract. v0.6D retains a non-null local timestamp policy with different malformed-input behavior.

A shared serializer must not route v0.6D timestamps through `stage2_query_values` and silently change that behavior.

## Options evaluated

### Option A: one generic ORM-aware serializer

Rejected.

A helper accepting row containers, owner-field names, source-link attribute names and claim-field switches would centralize reflection rather than domain meaning. It would make field compatibility less visible and couple the neutral module to three ORM container shapes.

### Option B: neutral projection DTOs plus one pure serializer

Technically possible, but not ready.

Each domain would need an adapter that maps ORM rows into neutral claim, evidence and boundary DTOs. The adapters would retain most selection and mapping logic, while the shared serializer would own only sorting, grade counting and conflict/missing assembly. This adds types and conversion code without a demonstrated behavioral or maintenance benefit.

It would also force a premature decision about whether the v0.6B reduced claim shape or the v0.6C/v0.6D extended shape is the neutral contract.

### Option C: lower-level evidence-item/finalization helpers

Not justified now.

Small helpers could format one evidence item, finalize grade counts or sort result collections. Those operations are short, stable and currently readable in place. Extracting them would increase call indirection while leaving domain selection and claim projection duplicated.

### Option D: share only v0.6C and v0.6D

Not ready.

Their current claim and missing-evidence outputs match, but owner-link selection and timestamp error policy differ. A two-domain abstraction would still need callbacks or preformatted values and would create a new contract based only on coincidental current equality.

## Decision

Keep the v0.6B-v0.6D evidence read serializers local.

No implementation Issue should be opened from this characterization. The candidate does not meet Definition of Ready because:

- no neutral claim projection is accepted;
- domain-specific missing-evidence text must remain visible;
- v0.6D timestamp error behavior must remain independent;
- a shared helper would require reflection, callbacks or projection adapters;
- no concrete bug, inconsistent output or new domain slice demonstrates that the extra abstraction pays for itself.

The current duplication is explicit and safer than a generic serializer with hidden policy switches.

## Re-evaluation triggers

Reconsider only if at least one of the following occurs:

1. a new reviewed domain requires the exact v0.6C/v0.6D claim/evidence contract;
2. the nested evidence payload becomes an explicit versioned neutral public contract;
3. a cross-domain defect demonstrates that local implementations cannot be kept compatible safely;
4. accepted projection DTOs already exist for another independent reason;
5. v0.6D timestamp-null/error semantics are deliberately unified through a separate reviewed decision.

Any re-evaluation still requires a new Architecture Preflight, Issue, tests and no-migration decision.

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

## Definition of Ready conclusion

Evidence read serialization does not reach Definition of Ready for implementation. The accepted outcome of Issue #92 should be a documented decision to keep serializers local and move the next independent consolidation preflight to command conflict/integrity behavior.
# Industry Thesis Reviewed-Plan Owner Acceptance and Exact Output Links v1

## 1. Decision status

- Authoritative Issue: #234.
- Product Roadmap: #137.
- Required base: `ada017848c01d0bf4af64951f9215f97cf10e04b`.
- Risk tier: **Strict Architecture Preflight**.
- This document authorizes architecture only.
- It authorizes no production code, migration execution, API/UI implementation, fixture, executable test, dependency, Provider access, AI call, release, tag or version change.

## 2. Product decision

AQuantAI will add one explicit offline acceptance boundary after the existing deterministic reviewed plan:

```text
reviewed_plan_ready
  -> explicit owner-acceptance input
  -> deterministic owner-acceptance preview
  -> explicit user confirmation
  -> one atomic existing-owner transaction
  -> accepted_outputs_linked
  -> exact complete-universe and readiness reads
```

The acceptance transaction converts only explicitly supplied, evidence-bound owner inputs into accepted owner revisions. It does not promote thesis prose, draft graph content, candidate labels, AI output or inferred classifications.

The v1 boundary is intentionally narrow:

```text
map_mode = reuse_exact_existing_map_revision
```

A useful v1 result therefore requires one exact accepted Research Case and one exact existing Industry Map revision. Creating a new map, node, relationship, observation, claim or evidence item from thesis draft content is outside this slice.

## 3. Why the prior placeholder contract is insufficient

The original orchestration architecture reserved `accepted_outputs_linked` and output-link tables, but the implemented reviewed plan does not contain every field required by accepted owners.

### 3.1 Reviewed-plan fields currently available

The stored `acceptance_plan_preview` freezes:

- exact reviewed session revision;
- exact reviewed candidate revisions;
- selected, rejected and unresolved decisions;
- selected `stock_basic` or `listed_instrument` identity reference;
- final proposed typed exposure;
- source kind and source-reference fingerprint;
- coverage state;
- information and recorded-time boundaries;
- deterministic reviewed-plan fingerprint.

Those fields prove what the user reviewed. They are not sufficient to create evidence-backed Stage 1 state.

### 3.2 Stage 1 fields currently required

A new or appended Stage 1 beneficiary revision requires:

- exact Research Case;
- exact existing Industry Map identity and revision;
- exact successful `stock_basic` record;
- explicit legacy beneficiary kind: `direct`, `secondary` or `potential`;
- explicit assessment status: `draft`, `supported`, `disputed` or `rejected`;
- at least one exact map assertion revision already frozen by the selected map revision;
- at least one exact claim revision from the same Research Case;
- explicit rationale;
- information cutoff and recorded UTC.

A `ListedInstrument` identity alone cannot satisfy this contract.

### 3.3 Classification contracts are intentionally different

The reviewed proposal exposure vocabulary is:

```text
direct / conditional / indirect / conceptual / unknown
```

The legacy Stage 1 beneficiary-kind vocabulary is:

```text
direct / secondary / potential
```

The typed-semantics owner requires a complete profile containing explicit assertion fields, state codes, evidence states, claim links, optional map-observation links and verification items.

No deterministic universal mapping exists among these contracts. The acceptance plan must therefore carry explicit owner values rather than infer them.

### 3.4 Complete universe differs from supported handoff

The accepted complete beneficiary universe may contain Stage 1 revisions with status:

```text
draft / supported / disputed
```

The existing Stage 1 candidate-pool owner accepts only `supported` beneficiary revisions and requires a non-empty membership list.

The architecture therefore separates:

```text
complete accepted beneficiary universe
supported-only Stage 2 handoff pool
```

A complete accepted universe may legitimately have zero supported members. This must not be represented by an empty or fabricated candidate pool.

### 3.5 Existing owner commands cannot compose atomically

Current Industry Map, Stage 1 and typed-semantics public command services each open and commit their own transaction. Calling them sequentially cannot provide the required all-or-nothing cross-owner acceptance boundary.

The implementation must refactor owner internals into session-bound write ports without moving validation or table ownership into the orchestrator.

## 4. Core invariants

1. The reviewed plan remains immutable and non-accepted.
2. Acceptance begins from one exact `reviewed_plan_ready` revision and its verified stored fingerprint.
3. V1 reuses one exact accepted existing Industry Map revision; draft graph content is never promoted.
4. Every new or appended Stage 1 revision uses one exact successful `stock_basic` record.
5. Listed-instrument-only candidates remain visible but cannot commit without an explicitly accepted exact bridge and selected `stock_basic` record.
6. Legacy Stage 1 kind, Stage 1 status and typed semantics are separate explicit contracts.
7. All selected candidates remain represented in the accepted complete universe.
8. Only supported beneficiary revisions enter the optional Stage 2 handoff pool.
9. Missing typed semantics or Company Research remains visible and does not remove a beneficiary.
10. The orchestrator owns coordination and thesis output links only; it never becomes the owner of map, beneficiary, semantic, Company Research or Investment Candidate state.
11. All owner revisions and output links commit or roll back together.
12. Exact accepted revisions are frozen; no later compatible-looking record is selected.
13. Dry-run and commit use the same normalized plan and fingerprint.
14. Repeating the same accepted request is idempotent; a conflicting request fails closed.
15. Ordinary reads perform no external network or AI call.
16. No result is a buy/sell/hold recommendation, target price, expected return, position size, portfolio action or trading action.

## 5. Authoritative ownership

| Field or behavior | Authoritative owner | Acceptance rule |
| --- | --- | --- |
| Exact reviewed thesis, candidate decisions and reviewed-plan fingerprint | `industry_alpha.industry_thesis_*` | Read exact frozen revision only |
| Research Case | Evidence Ledger / Research Case owner | Exact existing identity required |
| Accepted Industry Map and map revision | Industry Map owner | Reuse exact existing revision in v1 |
| Stage 1 beneficiary identity/revision and candidate-pool revision | Stage 1 owner | Created/reused only through Stage 1 write port |
| Legacy beneficiary kind and assessment status | Stage 1 owner | Explicit user-confirmed values |
| Typed exposure/execution profile | Typed Beneficiary Semantics owner | None, reuse exact compatible revision, or append complete explicit payload |
| Company Research | Company Research owner | Readiness link only; no acceptance write |
| Investment Candidate components/rule/snapshot | Investment Candidate owner | No automatic write; later explicit command only |
| Accepted session transition and output-link rows | Industry Thesis owner | Written by coordinator inside outer transaction |
| Complete-universe presentation order | Industry Thesis output-link contract | Exact ordered owner bindings |

## 6. Owner-acceptance plan v1

### 6.1 Version

```text
OWNER_ACCEPTANCE_PLAN_VERSION = aquantai.industry-thesis-owner-acceptance-plan.v1
```

### 6.2 Top-level input

The normalized input freezes:

- `reviewed_session_revision_id`;
- `expected_session_latest_revision_number`;
- `reviewed_plan_fingerprint_sha256`;
- `research_case_id`;
- `map_mode = reuse_exact_existing_map_revision`;
- `industry_map_id`;
- `industry_map_revision_id`;
- ordered `candidate_owner_bindings`;
- `candidate_pool_mode`;
- optional existing candidate-pool identity selector;
- output title and scope;
- `information_cutoff_date`;
- `revision_note`;
- `owner_acceptance_plan_version`;
- `preview_fingerprint_sha256` on commit.

Unknown fields fail closed.

### 6.3 Candidate-owner binding

Exactly one binding is required for every selected candidate revision in the reviewed plan. Rejected and unresolved reviewed candidates remain visible in the reviewed-plan history but do not enter accepted Stage 1 state.

Each selected binding freezes:

- `reviewed_candidate_revision_id`;
- `sequence`;
- `stage1_operation`;
- exact target or new Stage 1 identity information;
- exact resulting Stage 1 input contract;
- optional typed-semantics operation;
- explicit readiness note.

Accepted Stage 1 operations:

```text
reuse_exact_beneficiary_revision
create_beneficiary_identity_and_revision
append_beneficiary_revision
```

#### Reuse exact beneficiary revision

Required:

- exact `beneficiary_id`;
- exact `beneficiary_revision_id`;
- proof that the revision belongs to the selected Research Case, map and exact selected map revision;
- proof that its `stock_basic` identity equals the reviewed candidate's explicitly selected accepted owner identity;
- proof that its information/recorded boundaries do not exceed the acceptance boundaries.

The reviewed proposed exposure may disagree with accepted legacy or typed state. The disagreement remains visible and does not rewrite the existing revision.

#### Create or append beneficiary revision

Required:

- exact `stock_basic_record_id`;
- exact `source` and `stock_code` owned by that record;
- explicit `legacy_beneficiary_kind`;
- explicit `assessment_status`;
- explicit `rationale_summary`;
- ordered exact `map_assertion_revisions`, each containing kind and revision ID;
- ordered exact `claim_revision_ids`;
- exact target `beneficiary_id` for append;
- exact expected latest beneficiary revision ID for append;
- null expected target for create.

The Stage 1 owner validates evidence grade, contradiction, map membership, Research Case, chronology and snapshot provenance. The coordinator does not duplicate those rules.

### 6.4 Typed-semantics operation

Accepted modes:

```text
none
reuse_exact_semantic_revision
append_complete_semantic_profile
```

#### None

No semantic revision is written or linked. Readiness reports `typed_semantics_missing` unless another exact visible revision is explicitly linked later through a separately authorized operation.

#### Reuse exact semantic revision

Required:

- exact semantic profile ID;
- exact semantic profile revision ID;
- exact beneficiary and beneficiary revision compatibility;
- exact map revision compatibility;
- dual-as-of visibility.

#### Append complete semantic profile

The input is the existing typed-semantics owner payload, including:

- exact beneficiary and resulting beneficiary revision;
- selected map revision;
- expected latest semantic revision;
- overall status, summary and recorded-by value;
- complete ordered semantic assertions;
- exact claim links and relations;
- optional exact map-observation revision bindings;
- complete verification items;
- information cutoff.

No exposure label is expanded into this payload.

### 6.5 Complete-universe and handoff modes

`candidate_pool_mode` is one of:

```text
create_supported_handoff
append_supported_handoff
reuse_exact_supported_handoff
none_no_supported_members
```

Rules:

1. The complete-universe bindings include every successfully accepted selected candidate.
2. Handoff membership is derived only from exact resulting beneficiary revisions whose Stage 1 assessment status is `supported`.
3. A user cannot manually omit a supported accepted member from the handoff within this v1 transaction.
4. Draft or disputed members cannot enter the handoff.
5. `none_no_supported_members` is valid only when the exact accepted complete universe contains zero supported revisions.
6. A non-empty supported set requires create, append or reuse mode and exact pool validation.
7. The architecture does not weaken the existing Stage 1 candidate-pool contract.

## 7. Plan normalization, fingerprint and stable reasons

### 7.1 Canonicalization

- strict JSON objects reject unknown keys;
- ordered owner bindings sort by explicit `sequence`, then reviewed candidate revision ID;
- assertion and claim IDs use deterministic explicit ordering;
- decimal or numeric inference is not present;
- UUIDs use lowercase canonical text;
- UTC values use explicit ISO-8601 UTC representation;
- the plan fingerprint is SHA-256 over canonical UTF-8 JSON excluding the fingerprint field itself.

### 7.2 Stable blocked-reason codes

At minimum:

```text
INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_NOT_READY
INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_STALE
INDUSTRY_THESIS_ACCEPTANCE_REVIEWED_PLAN_FINGERPRINT_MISMATCH
INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED
INDUSTRY_THESIS_ACCEPTANCE_MAP_REVISION_MISMATCH
INDUSTRY_THESIS_ACCEPTANCE_BINDINGS_INCOMPLETE
INDUSTRY_THESIS_ACCEPTANCE_STOCK_IDENTITY_REQUIRED
INDUSTRY_THESIS_ACCEPTANCE_LISTED_INSTRUMENT_ONLY
INDUSTRY_THESIS_ACCEPTANCE_STAGE1_BINDINGS_REQUIRED
INDUSTRY_THESIS_ACCEPTANCE_DUPLICATE_OWNER_IDENTITY
INDUSTRY_THESIS_ACCEPTANCE_LEGACY_KIND_REQUIRED
INDUSTRY_THESIS_ACCEPTANCE_STATUS_REQUIRED
INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_PAYLOAD_INCOMPLETE
INDUSTRY_THESIS_ACCEPTANCE_SEMANTIC_REVISION_MISMATCH
INDUSTRY_THESIS_ACCEPTANCE_SUPPORTED_HANDOFF_MISMATCH
INDUSTRY_THESIS_ACCEPTANCE_OWNER_REVISION_CONFLICT
INDUSTRY_THESIS_ACCEPTANCE_CHRONOLOGY_INVALID
INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_ALREADY_EXISTS
INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_CONFLICT
INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE
```

Every reason has one stable ordinary-Chinese message. Technical exceptions are not exposed as the ordinary-user message.

## 8. Session-bound owner write ports

### 8.1 Required layering

Each accepted owner module exposes an internal application port that accepts an existing SQLAlchemy `Session` and never calls commit, rollback or `session_factory.begin()`.

Candidate shape:

```python
class Stage1OwnerWritePort:
    def validate_beneficiary_operation(self, session, operation): ...
    def apply_beneficiary_operation(self, session, operation): ...
    def validate_candidate_pool_operation(self, session, operation): ...
    def apply_candidate_pool_operation(self, session, operation): ...

class BeneficiarySemanticOwnerWritePort:
    def validate_operation(self, session, operation): ...
    def apply_operation(self, session, operation): ...
```

The names are illustrative; the ownership rule is mandatory.

### 8.2 Existing public commands

Existing public Stage 1 and semantic command services remain authoritative user-facing commands. They open their existing transactions and invoke the same owner ports.

This refactor prevents two implementations of owner validation.

### 8.3 Coordinator transaction

The thesis acceptance coordinator opens exactly one outer transaction:

```text
with session_factory.begin() as session:
  lock exact thesis session identity and reviewed revision
  verify reviewed plan and expected latest
  validate exact Research Case and map revision
  normalize and validate every owner binding through owner ports
  apply/reuse Stage 1 revisions through Stage 1 owner port
  apply/reuse optional semantic revisions through semantic owner port
  apply/reuse optional supported candidate-pool revision through Stage 1 owner port
  append accepted session revision
  append exact output-link identity/revision
  flush and return exact committed result
```

The coordinator may directly create only Industry Thesis session/output-link rows. It cannot create Industry Map, Stage 1 or semantic ORM rows itself.

Any owner error rolls back all rows.

## 9. Dry-run contract

### 9.1 Validation parity

Dry-run opens a non-committing Session and executes the same normalization, owner-port validation, current-history checks and deterministic operation ordering used by commit.

### 9.2 Preview output

The preview returns:

- plan version and fingerprint;
- exact reviewed-plan revision and fingerprint;
- exact Research Case and map revision;
- ordered candidate operation summaries;
- exact reused owner revision IDs;
- deterministic operation keys for create/append actions;
- complete-universe count and ordering;
- supported-handoff count and mode;
- explicit blocked reasons and readiness gaps;
- migration/schema readiness state;
- no generated accepted database IDs for uncommitted create operations.

### 9.3 Commit binding

Commit must include the exact preview fingerprint. A changed owner boundary, latest revision, reviewed plan or normalized input invalidates the preview.

Dry-run and commit are not required to share newly generated UUIDs. They must share plan fingerprint, operation keys, selectors, ordering and semantic meaning.

## 10. Accepted session revision

A successful commit appends one new Industry Thesis session revision:

```text
workflow_state = accepted_outputs_linked
supersedes_revision_id = exact reviewed_plan_ready revision
```

The accepted revision preserves strict canonical JSON inside the thesis-owned `draft_graph_json` envelope:

```json
{
  "base_draft_graph": {},
  "reviewed_acceptance_plan": {},
  "owner_acceptance_plan": {},
  "owner_acceptance_result": {},
  "output_link_revision_id": "..."
}
```

The original reviewed revision remains immutable and independently readable.

The accepted session input fingerprint is recomputed from the complete accepted revision payload under the existing Industry Thesis fingerprint contract.

## 11. Exact output-link contract

### 11.1 Output identity

One deterministic output identity represents one exact reviewed session revision plus one owner-plan fingerprint.

```text
output_key = SHA256(
  output_contract_version
  + reviewed_session_revision_id
  + owner_acceptance_plan_fingerprint
)
```

### 11.2 Output revision

The output-link revision freezes:

- output contract version;
- exact output-link identity;
- exact accepted session revision ID;
- exact reviewed session revision ID;
- exact Research Case ID;
- exact Industry Map identity and revision;
- optional exact supported candidate-pool revision;
- ordered complete beneficiary revision IDs;
- strict ordered per-candidate owner-output bindings;
- coverage state;
- reviewed-plan fingerprint;
- owner-plan fingerprint;
- deterministic owner transaction key;
- information cutoff;
- recorded UTC;
- supersedes output revision only for a future separately reviewed correction path.

### 11.3 Per-candidate owner-output binding

Each strict binding contains:

- `sequence`;
- `reviewed_candidate_revision_id`;
- `stage1_operation`;
- exact `beneficiary_id`;
- exact `beneficiary_revision_id`;
- exact `stock_basic_record_id`;
- exact legacy kind and status as frozen by that revision;
- optional exact semantic profile ID/revision ID;
- explicit semantic mode;
- supported-handoff inclusion boolean and reason;
- explicit readiness reason codes.

The JSON is an exact-link index, not a second copy of owner business fields. Kind/status are included only as frozen integrity assertions and must be verified against the owner revision on every exact read.

### 11.4 Idempotency

- Repeating the same exact commit request resolves to the existing output revision and accepted session revision.
- The returned result declares `idempotent_replay=true`.
- The same reviewed revision with a different owner-plan fingerprint fails with `INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_CONFLICT`.
- A reviewed revision that is no longer latest fails as stale unless the exact accepted output already exists and matches the request.
- No duplicate owner revisions are created during replay.

## 12. Persistence and migration decision

### 12.1 Migration required

Migration candidate:

```text
20260725_0017_industry_thesis_owner_acceptance
```

### 12.2 Minimal schema changes

1. Make `industry_thesis_output_link_revisions.accepted_candidate_pool_revision_id` nullable.
2. Add `accepted_session_revision_id` as a non-null exact foreign key to `industry_thesis_session_revisions`.
3. Add `reviewed_session_revision_id` as a non-null exact foreign key.
4. Add `research_case_id` as a non-null exact foreign key.
5. Add `output_contract_version` as bounded non-null text.
6. Add `reviewed_plan_fingerprint_sha256` as non-null 64-character text.
7. Add `ordered_owner_output_bindings_json` as non-null strict canonical JSON text.
8. Add uniqueness for one output revision per accepted session revision.
9. Preserve the existing ordered beneficiary IDs, coverage, owner-plan fingerprint, transaction ID and chronology fields.

No existing owner table is changed.

### 12.3 Upgrade behavior

Current production runtime has no output-link writer. Nevertheless, upgrade must inspect existing output-link rows.

- If no rows exist, add non-null columns using a safe empty-table path.
- If rows exist and exact new fields cannot be derived without guessing, abort before mutation with a clear migration error.
- Never invent accepted session revisions, Research Case links or per-candidate bindings.

### 12.4 Downgrade behavior

Downgrade refuses before dropping or making fields lossy when any v1 output-link row exists.

Empty-schema downgrade may restore the prior non-null candidate-pool column only when no rows exist.

PostgreSQL and supported SQLite behavior must be tested explicitly.

## 13. Read contracts

All reads require exact IDs, explicit information cutoff and explicit recorded-UTC boundary. They never fall back to latest compatible rows.

Candidate API/service contracts:

```text
POST /industry-analysis/api/session-revisions/{reviewed_revision_id}/owner-acceptance/preview
POST /industry-analysis/api/session-revisions/{reviewed_revision_id}/owner-acceptance/commit
GET  /industry-analysis/api/output-links/{output_link_revision_id}
GET  /industry-analysis/api/output-links/{output_link_revision_id}/result
GET  /industry-analysis/api/output-links/{output_link_revision_id}/readiness
```

### 13.1 Exact output read

Verifies:

- output identity/revision chronology;
- reviewed and accepted session state;
- map and Research Case compatibility;
- every per-candidate binding against exact owner rows;
- ordered beneficiary IDs equal ordered bindings;
- optional pool membership equals exactly the supported binding subset;
- every linked record is visible under both as-of boundaries.

Corruption fails closed with `INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE`.

### 13.2 Result read

Returns the complete accepted universe in frozen order. Every member includes:

- exact reviewed candidate source and rationale;
- exact Stage 1 identity/revision and legacy state;
- optional exact typed-semantic revision;
- supported-handoff inclusion and reason;
- coverage notice;
- exact navigation links;
- no hidden ranking.

### 13.3 Readiness read

For every complete-universe member, reports exact visible state for:

- typed semantics;
- Company Research;
- required Investment Candidate component inputs;
- Canonical Price and purpose-specific Comparison Eligibility;
- structured financial/valuation inputs;
- catalyst, risk and verification states;
- missing, stale, disputed, pending or failed reasons.

Readiness creates no owner state and computes no second score.

## 14. Chinese-first product flow

The existing reviewed-plan result page gains one explicit action only when the exact state is `reviewed_plan_ready`:

```text
检查并接受研究成果
```

Sequence:

1. **选择既有研究案例和产业地图**
   - exact existing Research Case;
   - exact map identity/revision;
   - no fuzzy map creation.
2. **补齐每家公司接受字段**
   - exact `stock_basic` identity;
   - reuse/create/append Stage 1 choice;
   - legacy kind/status;
   - exact map assertion and claim revisions;
   - rationale;
   - optional complete typed-semantics action.
3. **查看变更预览**
   - complete universe;
   - supported handoff subset;
   - blocked reasons;
   - plan fingerprint.
4. **明确确认提交**
   - no automatic acceptance;
   - exact preview fingerprint required.
5. **查看已接受成果**
   - exact output-link revision;
   - complete universe always visible;
   - readiness and missing reasons;
   - later explicit Investment Candidate handoff action when eligible.

Ordinary users see labels and missing reasons first. Technical IDs and fingerprints remain progressive details, but the system owns and submits exact IDs selected through deterministic local option reads.

## 15. Production-realistic offline golden path

### 15.1 Shared inputs

- one exact local Research Case;
- one exact existing Industry Map revision containing evidence-backed assertion revisions;
- one exact reviewed thesis revision in `reviewed_plan_ready`;
- three selected reviewed candidates, each explicitly bound to exact successful `stock_basic` records;
- explicit claim and assertion bindings;
- no external network, Provider, news, announcement or AI.

### 15.2 Company A

- create or append Stage 1 revision;
- legacy kind `direct`;
- status `supported` with valid A/B/C-backed non-conflicted claim path;
- optional exact reusable or complete new typed-semantic revision;
- included in supported handoff.

### 15.3 Company B

- create or append Stage 1 revision;
- explicit legacy kind;
- status `draft` or `disputed` with contract-valid evidence state;
- preserved in complete universe;
- excluded from supported handoff with exact reason.

### 15.4 Company C

- create or append Stage 1 revision;
- status `supported`;
- typed semantics absent or incomplete Company Research;
- included in supported handoff;
- readiness remains incomplete with explicit reasons.

### 15.5 Success sequence

1. verify exact reviewed-plan fingerprint and latest state;
2. normalize owner-acceptance input;
3. validate all owner operations through session-bound owner ports;
4. dry-run returns one stable fingerprint and complete operation list;
5. commit with the exact fingerprint;
6. apply/reuse three Stage 1 revisions;
7. apply/reuse optional semantic revision for A only;
8. create/revise one supported candidate pool containing A and C;
9. append one accepted session revision;
10. append one exact output-link revision with all three bindings;
11. reopen under both as-of boundaries and reproduce A, B and C;
12. readiness shows B outside supported handoff and C missing downstream inputs;
13. no Investment Candidate snapshot or score is created.

### 15.6 Zero-supported path

A second fixture accepts two contract-valid draft/disputed Stage 1 revisions.

- complete universe count is two;
- candidate-pool mode is `none_no_supported_members`;
- output-link pool revision is null;
- result shows both members and explicit `no_supported_handoff_members` notice;
- acceptance succeeds without fabricating supported state.

## 16. Primary failure path

A reviewed selected candidate is bound only to a `ListedInstrument`, or the user has not selected exact Stage 1 assertion and claim revisions.

Required result:

1. preview returns `INDUSTRY_THESIS_ACCEPTANCE_LISTED_INSTRUMENT_ONLY` or `INDUSTRY_THESIS_ACCEPTANCE_STAGE1_BINDINGS_REQUIRED`;
2. preview contains no commit-ready fingerprint;
3. commit payload is rejected before owner writes;
4. no Stage 1, semantic, candidate-pool, accepted session or output-link row is created;
5. the exact reviewed plan remains visible and unchanged;
6. the UI asks the user to select an exact local owner identity/evidence binding and never suggests a guessed company.

## 17. Additional failure paths

### 17.1 Stale reviewed revision

Expected-latest session revision does not match. Fail before owner validation and do not select a newer reviewed revision.

### 17.2 Reviewed-plan fingerprint mismatch

Stored plan verification or submitted fingerprint fails. Treat as graph corruption or stale input; no writes.

### 17.3 Map mismatch

Research Case, map identity, map revision, assertion revisions or Stage 1 target do not share the exact accepted boundary. Roll back all operations.

### 17.4 Duplicate owner identity

Two selected reviewed candidates resolve to the same exact Stage 1 beneficiary or exact `stock_basic` identity. Fail before writes; do not silently merge them.

### 17.5 Unsupported legacy mapping attempt

A request supplies only typed proposal exposure and omits legacy Stage 1 kind. Fail with `INDUSTRY_THESIS_ACCEPTANCE_LEGACY_KIND_REQUIRED`.

### 17.6 Incomplete semantic payload

Append mode omits required semantic assertions, evidence links or verification fields. Fail the whole transaction.

### 17.7 Handoff mismatch

The requested/reused candidate pool does not contain exactly the supported accepted subset. Fail; never omit supported members or include draft/disputed members.

### 17.8 Owner concurrency conflict

Any expected latest owner revision has moved. Roll back every owner output and thesis row.

### 17.9 Replay conflict

The reviewed revision already has an accepted output with a different owner-plan fingerprint. Return conflict; never append a competing accepted result.

### 17.10 Later-information leakage

Any linked owner revision exceeds the acceptance information cutoff or recorded boundary. Fail before writes or fail exact read as not visible.

## 18. Test architecture

The future Strict implementation must include:

### 18.1 Plan tests

- strict unknown-field rejection;
- stable ordering and fingerprint;
- complete selected-binding coverage;
- explicit legacy/typed separation;
- listed-instrument-only blocked result;
- dry-run/commit normalized-plan parity;
- no runtime-clock field inside the plan fingerprint.

### 18.2 Owner-port tests

- existing public Stage 1 commands retain behavior after refactor;
- existing typed-semantic commands retain behavior after refactor;
- ports never commit or roll back;
- validation remains owned by the original modules;
- direct orchestrator ORM writes to owner tables are statically prohibited.

### 18.3 Atomicity tests

- fail on second or third candidate and verify zero rows across all owners;
- fail semantic append after Stage 1 insert and verify rollback;
- fail output-link insert and verify rollback;
- PostgreSQL lock conflict and supported SQLite deterministic behavior;
- idempotent replay creates no duplicate rows.

### 18.4 Complete-universe tests

- three-company golden path;
- draft/disputed member remains visible;
- supported subset equals candidate-pool membership;
- zero-supported accepted output with null pool;
- valuation, missing semantics or missing Company Research never removes a member.

### 18.5 Exact read tests

- dual-as-of visibility;
- no latest fallback;
- output binding integrity verification;
- pool subset integrity;
- corrupted JSON/foreign key/state fails closed;
- bounded query count independent of universe size where required.

### 18.6 Runtime safety

- imports, tests, demos and ordinary reads make no network or AI call;
- no credential path;
- no recommendation, portfolio or trading fields.

## 19. Implementation sequence candidate

Architecture approval should lead to separate owner-authorized implementation Issues.

### Slice 1 — Core owner acceptance and exact links

Strict implementation scope:

- migration `20260725_0017`;
- normalized owner-acceptance contracts and stable reasons;
- session-bound Stage 1 and semantic owner ports;
- atomic coordinator;
- accepted session transition;
- output-link writer and exact queries;
- local JSON-only preview/commit/read commands;
- SQLite/PostgreSQL golden, failure and rollback tests;
- fully offline demo.

No HTTP/UI is required for Slice 1.

### Slice 2 — Ordinary-user completion

After Slice 1 is accepted:

- bounded API adapters;
- result-page `检查并接受研究成果` flow;
- deterministic local selectors for Research Case, map, assertions, claims and existing owner revisions;
- dry-run preview and explicit commit confirmation;
- accepted-output result/readiness page;
- conflict preservation and no silent retry.

No new ownership, migration, AI, Provider or Investment Candidate scoring logic.

### Later explicit handoff

An existing Investment Candidate snapshot may be created only by a later explicit action using the exact supported candidate-pool revision and existing rule contract. It is not part of owner acceptance.

## 20. Alternatives rejected

### 20.1 Promote the thesis draft graph into Industry Map

Rejected because draft text lacks exact evidence-qualified claim/assertion inputs and would make orchestration a second evidence/map owner.

### 20.2 Automatically map typed exposure to legacy Stage 1 kind

Rejected because the vocabularies express different contracts and no accepted universal mapping exists.

### 20.3 Automatically generate typed semantics from one exposure label

Rejected because typed semantics requires a complete explicit evidence and verification profile.

### 20.4 Put every accepted member in the Stage 1 candidate pool

Rejected because the candidate-pool owner correctly requires `supported` revisions.

### 20.5 Reject acceptance when no member is supported

Rejected because a reviewed complete universe can be useful and honest before evidence reaches supported status.

### 20.6 Sequentially call existing public commands

Rejected because independent transactions can leave partial accepted history.

### 20.7 Copy owner validation into the coordinator

Rejected because it duplicates ownership and will drift from accepted contracts.

### 20.8 Automatically create Company Research or Investment Candidate state

Rejected because those require separate explicit owner inputs and would broaden the transaction into scoring/research judgment.

## 21. Migration, rollback and operational safety

- Migration is additive/relaxing and touches only thesis output-link schema.
- No existing owner table is modified.
- Upgrade refuses before guessing legacy output-link fields.
- Populated v1 output-link state blocks downgrade before any destructive action.
- Code rollback before accepted data exists is a normal code/migration revert.
- After accepted data exists, downgrade remains prohibited; forward correction appends new reviewed state under a separately authorized correction contract.
- No background worker, scheduler, webhook, retry loop or remote dependency is introduced.

## 22. Stop conditions

Do not authorize implementation if:

- a useful success path requires free-text or draft-graph promotion into accepted Industry Map facts;
- exact Research Case, map, `stock_basic`, assertion or claim bindings are unavailable;
- the coordinator must duplicate owner validation or directly write another owner's ORM rows;
- existing owner behavior cannot be preserved through session-bound ports;
- complete accepted universe and supported handoff cannot be represented separately;
- a zero-supported accepted universe cannot be represented without fake state;
- idempotency depends on hidden latest selection or mutable history;
- exact output links cannot be verified under both as-of boundaries;
- ordinary reads require network, Provider, AI or hidden retrieval;
- acceptance automatically creates Company Research, component scores or Investment Candidate snapshots;
- recommendation, target price, expected return, position size, portfolio or trading behavior appears.

## 23. Locked exclusions

No production code, migration file, API/UI implementation, fixture, executable test, dependency, Provider, THS, CNINFO, news, webpage acquisition, credentials, AI call, automatic evidence acceptance, free-text map promotion, automatic identity bridge, automatic legacy/typed mapping, automatic Company Research, automatic component scoring, automatic Investment Candidate snapshot, recommendation, target price, expected return, position sizing, portfolio, broker, order, trading, release, tag or version change.

## 24. Validation and review gate

Before architecture merge:

1. branch base is exactly `ada017848c01d0bf4af64951f9215f97cf10e04b`;
2. complete diff contains only the three authorized documentation files;
3. repository CI succeeds on the exact final HEAD;
4. a fresh process-independent reviewer re-reads Issue #234, workflow, baseline, this document, diff and validation evidence;
5. zero unresolved review threads;
6. review records:

```text
AUTHORIZED INDUSTRY THESIS OWNER ACCEPTANCE AND OUTPUT LINKS PREFLIGHT APPROVED at fixed head <FULL_HEAD_SHA>
```

7. separate explicit project-owner authorization is required before merge.

Any new commit invalidates exact-head CI and fixed-head review evidence.

## 25. Closure decision

The preflight is implementation-ready only when fixed-head review confirms:

1. v1 reuses one exact existing map revision and never promotes draft graph content;
2. every selected candidate can supply explicit Stage 1 owner fields;
3. session-bound owner ports preserve one authoritative validation implementation;
4. complete universe and supported handoff remain separate;
5. zero-supported accepted output is honest and reproducible;
6. output links freeze exact per-candidate owner revisions;
7. dry-run, commit, idempotency and rollback contracts are deterministic;
8. Company Research and Investment Candidate writes remain outside acceptance;
9. the implementation can be delivered in bounded core and UI slices.

Architecture merge will not itself authorize production implementation.
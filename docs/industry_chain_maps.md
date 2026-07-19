# Evidence-Backed Industry Chain Maps

## Scope

v0.5B adds a local, append-only industry-chain-map ledger attached to one v0.5A `research_case`. It records reviewed nodes, directed relationships, drivers, bottlenecks, and value-pool-shift observations. It does not score industries, identify company beneficiaries, perform Stage 2 stock research, call an LLM/provider, recommend securities, or trade.

## Append-Only Model

Stable identities and immutable revisions are separate:

- `industry_maps` and `industry_map_revisions`;
- `industry_map_nodes` and `industry_map_node_revisions`;
- `industry_map_relationships` and `industry_map_relationship_revisions`;
- `industry_map_observations` and `industry_map_observation_revisions`;
- `industry_map_assertion_claim_links` for exact v0.5A claim-revision binding;
- `industry_map_revision_memberships` for exact frozen map snapshots.

Corrections append a revision and point to the immediately superseded revision. Accepted identities, revisions, links, and memberships cannot be updated or deleted through an ORM session. Each multi-row command is one transaction and rolls back completely on validation, chronology, uniqueness, or boundary failure.

## Reviewed Values

Node kinds are `upstream_input`, `equipment`, `component`, `manufacturing`, `distribution`, `service`, `customer_end_market`, `regulation_infrastructure`, and `other`.

Relationship kinds are `supplies`, `enables`, `depends_on`, `substitutes`, `competes_with`, `distributes_to`, `regulates`, and `other`.

Observation kinds are `driver`, `bottleneck`, and `value_pool_shift`. Assertion status is always one of `draft`, `supported`, `disputed`, or `rejected`.

## Evidence Boundary

Every node, relationship, or observation revision references at least one exact v0.5A `claim_revision` from the same research case. Map text describes the bounded structure but cannot create an unlinked factual claim.

- `supported` requires a linked `supported` claim revision with visible A/B/C supporting evidence and no visible contradiction.
- D-only support cannot promote a map assertion to `supported`.
- `disputed` requires a linked disputed claim revision or visible contradictory evidence.
- Map-revision creation revalidates every frozen assertion at the map revision timestamp, so a later conflict cannot be silently hidden.
- Read contracts expose exact claim versions, evidence grades, conflicts, and claims with no evidence visible in the frozen snapshot.

## UTC Chronology And Cutoff

Recording chronology uses exact timezone-aware UTC timestamps. Identities cannot predate their case or map; revisions cannot predate their identity or previous revision; relationship identities cannot predate either endpoint; assertion links cannot predate either endpoint or an earlier accepted link; and map memberships cannot freeze later assertion revisions, links, claims, or qualifying evidence.

For `as_of_cutoff=D`, a revision is visible only when both its information cutoff and its UTC recorded calendar date are on or before `D`. Identity, link, membership, claim, and evidence recording dates are also checked. A frozen snapshot uses only assertion links and evidence available at that map revision's exact recorded timestamp, preventing later records from rewriting an earlier view.

## Read-Only API

```text
GET /industry-alpha/maps
GET /industry-alpha/maps?as_of_cutoff=YYYY-MM-DD
GET /industry-alpha/maps/{map_id}
GET /industry-alpha/maps/{map_id}?as_of_cutoff=YYYY-MM-DD
```

No POST, PUT, PATCH, or DELETE map route exists. Missing or cutoff-invisible maps return 404, malformed dates return 422, and unavailable database configuration or schema returns 503.

## Offline Demo

```bash
python -m scripts.demo_industry_chain_map
```

The in-memory fixture contains two supported nodes, a directed relationship, a supported driver, a D-grade value-pool lead that remains draft, and a later disputed bottleneck with visible contradictory evidence. The earlier cutoff excludes the later bottleneck and conflict. The demo performs no network call and does not write the configured PostgreSQL database.

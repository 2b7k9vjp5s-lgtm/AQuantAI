# Scripts

Run the deterministic v0.4D liquidity-distribution demonstration without network access:

```bash
python -m scripts.demo_liquidity_context
```

The command uses a temporary SQLite database, the existing fixture persistence path, one selected-equity snapshot per cutoff, and the normal Market Cockpit service. It removes the temporary database after producing current and historical read-only output.

- `python -m scripts.demo_research_flow`: run the existing local research fixture flow.
- `python -m scripts.persist_fixture_market_data`: persist the deterministic normalized market-data fixture after an explicit Alembic migration. This command never calls a live provider or external network service.
- `python -m scripts.ingest_akshare_market_data`: manually normalize and optionally persist one explicitly bounded AKShare snapshot. Real network access requires `--allow-network`; `--offline-fixture --dry-run` validates the same adapter path without network or database writes.
- `python -m scripts.demo_market_cockpit`: persist deterministic long-history current/historical revisions, then calculate two read-only Market Cockpit views from one explicit series. It requires an already migrated database and never accesses the network.
- `python -m scripts.ingest_akshare_benchmark_data`: manually normalize and optionally persist at most 20 explicit benchmark codes from the reviewed `index_zh_a_hist` endpoint. Network use requires `--allow-network`; offline dry-run creates no engine or rows.
- `python -m scripts.ingest_akshare_sector_data`: manually normalize and optionally persist at most 30 exact Eastmoney `BK` industry-board codes using the reviewed taxonomy and bounded history endpoints. Network use requires `--allow-network`; offline dry-run creates no engine or rows.
- `python -m scripts.demo_sector_context`: persist deterministic current/historical equity and selected-sector snapshots and print their read-only alignment, provenance, exact-window metrics, and cross-sectional context without network access.
- `python -m scripts.demo_benchmark_context`: persist deterministic equity and benchmark current/historical revisions and render aligned read-only context without network access.
- `python -m scripts.demo_stage1_beneficiaries`: build an isolated deterministic v0.5C fixture with exact company/map/claim bindings, current and historical beneficiary views, and an unranked supported-only candidate pool. It never accesses the network or configured PostgreSQL database.
- `python -m scripts.demo_stage2_company_research`: build an isolated deterministic v0.6A fixture from exact candidate-pool memberships, freeze company/map/claim/evidence boundaries, and compare current/historical financial-transmission hypotheses and verification checklists. It never accesses the network or configured PostgreSQL database.
- `python -m scripts.demo_stage2_expectations_valuation`: build an isolated deterministic v0.6B fixture with append-only expectation and valuation-context observations bound to exact Stage 2 research, hypothesis, claim, evidence, and optional local price provenance. It never outputs target prices, fair values, expected returns, scores, rankings, recommendations, or trading actions.
- `python -m scripts.demo_stage2_catalyst_risk_assessments`: build an isolated deterministic v0.6C fixture with append-only catalyst and company-risk judgments bound to exact v0.6A/v0.6B and claim/evidence boundaries. It is not a monitor, alert, score, recommendation, timing model, or trading system.

## Record typed beneficiary evidence semantics

After configuring `DATABASE_URL` and running `alembic upgrade head`, validate one explicit local JSON file without writing:

```bash
python -m scripts.record_beneficiary_semantics --input path/to/semantic-input.json --dry-run
```

Record the validated append-only revision:

```bash
python -m scripts.record_beneficiary_semantics --input path/to/semantic-input.json
```

The JSON object must explicitly provide:

- one existing `beneficiary_id`, its exact `beneficiary_revision_id`, and the same frozen `selected_map_revision_id`;
- `taxonomy_version` equal to `aquantai.typed-beneficiary-evidence-semantics.v1`;
- `expected_latest_revision_id` (`null` for the first revision);
- `overall_status`, summary, local responsibility label `recorded_by`, information cutoff, and recorded UTC;
- exactly one exposure, customer, certification, capacity, production, and order assertion;
- at least one driver and offering assertion;
- exact driver observation revisions and claim revisions already frozen by the selected Stage 1 beneficiary revision;
- one linked verification item for every assertion whose evidence state is `missing`.

The command is local-only: it performs no browsing, Provider access, model call, automatic extraction, ranking, valuation, recommendation, monitoring, portfolio action, or trading action. The browser and API remain read-only; all accepted writes pass through this explicit CLI transaction.
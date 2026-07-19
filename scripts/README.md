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

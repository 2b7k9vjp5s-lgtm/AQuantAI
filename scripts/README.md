# Scripts

- `python -m scripts.demo_research_flow`: run the existing local research fixture flow.
- `python -m scripts.persist_fixture_market_data`: persist the deterministic normalized market-data fixture after an explicit Alembic migration. This command never calls a live provider or external network service.
- `python -m scripts.ingest_akshare_market_data`: manually normalize and optionally persist one explicitly bounded AKShare snapshot. Real network access requires `--allow-network`; `--offline-fixture --dry-run` validates the same adapter path without network or database writes.

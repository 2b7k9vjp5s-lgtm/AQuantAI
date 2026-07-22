# Scripts

## Investment Candidate Intelligence v1

The two commands below accept one bounded local UTF-8 JSON file, perform no
network or AI call, reject unknown fields, emit deterministic strict JSON, and
support `--dry-run` validation without database writes:

```text
python -m scripts.record_investment_candidate_component --input local/component.json --dry-run
python -m scripts.record_investment_candidate_snapshot --input local/snapshot.json --dry-run
```

Remove `--dry-run` only after reviewing the manifest. Component inputs must
provide explicit analyst-owned scores and exact upstream revision IDs. The
verification contract is closed and explicit:

- `verified` and `not_applicable` require `verification_material=false` and
  forbid `verification_item_code` / `verification_question`;
- `pending` and `failed` require `verification_material=true`, one closed
  `verification_item_code` (`certification`, `order`, `capacity`, `production`,
  `financial_confirmation`, `customer_confirmation`, or `other_explicit`) and a
  bounded `verification_question`;
- pending or failed verification prohibits numeric aggregation and priority
  ordinal; it is never silently treated as a neutral score.

Snapshot inputs must enumerate the complete exact membership set of one
persisted Stage 1 candidate-pool revision; omission, duplication, substitution,
or silent relinking fails closed. The commands do not infer scores or
verification state from text, company names, stock codes, Provider metadata,
evidence counts, price movement, or AI output. Candidate states are
research-priority context only and never generate buy/sell/hold instructions,
target prices, expected returns, positions, or trades.

## Normalized Valuation and Expectation Metrics v1

The four commands below accept one bounded local UTF-8 JSON object, reject
unknown fields, use explicit revision IDs and dual as-of boundaries, support
`--dry-run`, and perform no network or AI call:

```text
python -m scripts.record_structured_financial_observation --input local/financial-observation.json --dry-run
python -m scripts.record_normalized_valuation_metric --input local/valuation-metric.json --dry-run
python -m scripts.record_valuation_comparison_set --input local/comparison-set.json --dry-run
python -m scripts.record_normalized_expectation_gap --input local/expectation-gap.json --dry-run
```

Structured observations support only the reviewed metric, source, period,
accounting-scope, currency and unit vocabularies. Supported sourced values must
freeze exact Claim and Evidence links; explicit research assumptions require a
rationale and falsification condition. Existing v0.6B text is never parsed or
promoted into a numeric input.

Normalized valuation requires one exact accepted unadjusted official-close
Canonical Price revision and one exact eligible Comparison Eligibility revision
for purpose `normalized_valuation_metric_v1`. PE, PS, EV/EBITDA and FCF yield
use deterministic Decimal arithmetic with `ROUND_HALF_EVEN`; missing values are
never imputed and nonpositive denominators remain explicit non-meaningful states.
Historical and peer comparison commands preserve every explicit member, including
excluded members and their reason codes. Expectation-gap commands compare one
exact expected observation with one exact actual observation and do not change
Investment Candidate scores or snapshots.

These commands produce research context only. They do not calculate fair value,
target price, expected return, position size, buy/sell/hold output or a trade.

## Canonical Price and Comparison Eligibility v1

The four commands below accept one bounded local UTF-8 JSON file, perform no
network access, and support `--dry-run` validation without database writes:

```text
python -m scripts.record_listed_instrument --input local/instrument.json --dry-run
python -m scripts.record_canonical_price_series --input local/series.json --dry-run
python -m scripts.record_canonical_price --input local/price.json --dry-run
python -m scripts.record_price_comparison_eligibility --input local/eligibility.json --dry-run
```

Remove `--dry-run` only after reviewing the manifest. Inputs require explicit
identity, source, cutoff, UTC recording time, `recorded_by`, and expected-latest
revision values. The commands never infer exchange, currency, adjustment basis,
or a replacement source row. Canonical price is research context only; it does
not authorize cross-company arithmetic, ranking, target prices, or advice.

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

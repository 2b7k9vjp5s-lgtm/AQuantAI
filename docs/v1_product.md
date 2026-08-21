# AQuantAI V1.0 Release Candidate

## Product boundary

AQuantAI V1.0 RC is a local-first, research-only workspace. It records attributable evidence and human-authored research revisions. It does not provide investment advice, broker connectivity, orders, portfolio automation or automatic Evidence acceptance.

## Start and initialize

Docker Desktop users can run `start-aquantai.bat` on Windows or `./start-aquantai.sh` on macOS/Linux. The scripts preserve an existing `.env`, start the existing Compose services and wait for `http://127.0.0.1:8000/health`. Compose waits for PostgreSQL to become healthy and applies the checked-in Alembic migrations before Uvicorn starts.

For an existing Python environment:

```bash
pip install -e ".[dev]"
python -m scripts.init_v1_product
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/research-workspace`.

## Ordinary-user workflow

1. Create an Industry Research or Company Research Case in Research Cases.
2. Open Import / Review Queue and select a local official PDF.
3. Verify SHA256, page count and extracted page text. A scanned PDF without embedded text fails with `No extractable text / OCR required`.
4. Enter the exact Case ID, source metadata, reviewer identity and a selected page quotation.
5. Preview acceptance, then explicitly accept. AI cannot perform this action.
6. Return to Research Cases, save a new Revision and select the Accepted Evidence.
7. A completed or supported Revision is rejected unless it binds Accepted Evidence from the same Case.
8. Review Revision history and Change Feed, then export Markdown or HTML.

The report citation includes Source, Document, Page and Evidence ID. Rejected or merely pending candidates cannot be selected for an authoritative revision.

## AI Research Assistant

AI is optional. With no provider configured, every deterministic workflow remains available. To enable one explicit OpenAI-compatible HTTPS endpoint, set:

```text
AQUANTAI_GUARDED_AI_ENABLED=true
AQUANTAI_GUARDED_AI_PROVIDER_ID=<provider-id>
AQUANTAI_GUARDED_AI_ENDPOINT_URL=https://<host>/<chat-endpoint>
AQUANTAI_GUARDED_AI_MODEL_ID=<model-id>
AQUANTAI_GUARDED_AI_API_KEY=<local-secret>
AQUANTAI_GUARDED_AI_DATA_USE_NOTICE=<provider-data-use-note>
```

The user must preview the exact evidence-only manifest and confirm each remote transmission. Citations are validated against the manifest. Provider errors do not write research data. AI output is ephemeral D3 draft material: it cannot alter Evidence, provenance, review state or authoritative Revision state.

## Database changes

Migration `20260821_0020` adds three compatibility tables over the existing immutable Evidence Ledger:

- `product_research_case_profiles` for explicit Industry/Company product identity;
- `product_research_revision_contents` for canonical structured content and its SHA256;
- `product_research_revision_evidence_references` for ordered exact Evidence binding.

It also adds nullable `reviewer_identity` to old document review revisions so historical records remain readable while the V1 UI records explicit reviewers. Product rows are append-only. Empty downgrade is supported; populated downgrade fails before dropping data.

## Validation

Run the offline product path with `python -m scripts.demo_v1_product`. Run all tests with `python -m pytest -q`. PostgreSQL tests require an explicit reachable test database and must be reported as skipped when unavailable.

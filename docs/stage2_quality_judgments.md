# Stage 2 Quality Judgments

v0.6D stores local, append-only manual research judgments for industry quality and company quality. The records are research snapshots, not formal conclusions, scores, recommendations, price/timing decisions, watchlist states, verification tasks, or trading actions.

## Frozen Boundary

Each revision freezes:

- one exact v0.6A company-research revision and its selected accepted hypotheses;
- exact relevant v0.6B expectation and valuation revisions;
- exact relevant v0.6C catalyst and risk revisions;
- exact claim revisions and claim/evidence links already accepted by those boundaries.

Industry judgments remain traceable to the v0.6A identity's exact Stage 1 beneficiary, map revision, and stock snapshot. Company judgments use the same company-research identity. Cross-company, later, invisible, incomplete, or incompatible boundaries fail closed.

## Reviewed Fields

Outcome is one of `affirmed`, `not_affirmed`, `uncertain`, or `not_assessed`. Evidence state is independently one of `supported`, `disputed`, or `insufficient_evidence`.

- `affirmed` requires supported A/B/C evidence and no visible contradiction.
- `disputed` requires a disputed claim or contradiction.
- `uncertain` requires disputed or insufficient evidence.
- `not_assessed` requires insufficient evidence and explicit `尚未获得可靠公开证据` wording.
- `not_affirmed` is an explicit manual judgment and is never inferred automatically from missing data.

Reads retain claim fact/inference kind, inference confidence and basis, evidence grade/relation, conflicts, missing evidence, uncertainty, cutoff, and UTC record time. `后续验证清单` is bounded research text only; it has no owner, due date, reminder, completion state, or background processing.

## Read-Only API

- `GET /industry-alpha/industry-judgments`
- `GET /industry-alpha/industry-judgments/{judgment_id}`
- `GET /industry-alpha/company-judgments`
- `GET /industry-alpha/company-judgments/{judgment_id}`

List routes accept optional `company_research_id`. All routes accept optional `as_of_cutoff=YYYY-MM-DD`. Historical visibility checks both information cutoff and the UTC recorded date. There are no HTTP mutation routes or browser editor.

## Offline Demo

```powershell
python -m scripts.demo_stage2_quality_judgments
```

The fixture is deterministic and network-free. It includes affirmed A/B/C-backed snapshots, later disputed/uncertain snapshots, strict JSON output, and historical views that exclude later additions.

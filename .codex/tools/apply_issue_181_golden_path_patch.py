"""One-time deterministic patch for an append-only three-member golden path."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "tests/test_investment_candidate_commands.py"
text = TARGET.read_text(encoding="utf-8")

text = text.replace(
    "    Stage1BeneficiaryRevision,\n    Stage1CandidatePoolMembership,\n",
    "    Stage1BeneficiaryRevision,\n    Stage1CandidatePool,\n    Stage1CandidatePoolMembership,\n",
)

start = text.index("def _add_third_membership(")
end = text.index("\ndef _canonical_pair(", start)
replacement = '''def _build_three_member_pool(
    session: Session, source_pool_revision: Stage1CandidatePoolRevision
):
    source_pool = session.get(Stage1CandidatePool, source_pool_revision.candidate_pool_id)
    source_memberships = list(
        session.scalars(
            select(Stage1CandidatePoolMembership).where(
                Stage1CandidatePoolMembership.candidate_pool_revision_id
                == source_pool_revision.id
            )
        )
    )
    existing = {row.beneficiary_id for row in source_memberships}
    third = session.scalar(
        select(Stage1Beneficiary)
        .where(Stage1Beneficiary.id.not_in(existing))
        .order_by(Stage1Beneficiary.stock_code)
    )
    third_revision = session.scalars(
        select(Stage1BeneficiaryRevision)
        .where(Stage1BeneficiaryRevision.beneficiary_id == third.id)
        .order_by(Stage1BeneficiaryRevision.revision_no.desc())
    ).first()

    pool = Stage1CandidatePool(
        case_id=source_pool.case_id,
        map_id=source_pool.map_id,
        pool_key="fixture-investment-candidate-three-member",
        created_at_utc=RECORDED,
    )
    session.add(pool)
    session.flush()
    pool_revision = Stage1CandidatePoolRevision(
        candidate_pool_id=pool.id,
        revision_no=1,
        selected_map_revision_id=source_pool_revision.selected_map_revision_id,
        title="Three-member investment-candidate golden path",
        scope="Append-only fixture pool with two researched companies and one preserved missing member.",
        information_cutoff_date=CUTOFF,
        recorded_at_utc=RECORDED,
        supersedes_revision_id=None,
    )
    session.add(pool_revision)
    session.flush()

    source_research_by_beneficiary = {
        row.beneficiary_id: row
        for row in session.scalars(
            select(Stage2CompanyResearch).where(
                Stage2CompanyResearch.candidate_pool_revision_id
                == source_pool_revision.id
            )
        )
    }
    beneficiary_pairs = [
        (row.beneficiary_id, row.beneficiary_revision_id)
        for row in source_memberships
    ] + [(third.id, third_revision.id)]
    memberships = []
    research_by_membership = {}
    source_research_ids = {}
    for beneficiary_id, beneficiary_revision_id in beneficiary_pairs:
        membership = Stage1CandidatePoolMembership(
            candidate_pool_revision_id=pool_revision.id,
            beneficiary_id=beneficiary_id,
            beneficiary_revision_id=beneficiary_revision_id,
            recorded_at_utc=RECORDED,
        )
        session.add(membership)
        session.flush()
        memberships.append(membership)
        source_research = source_research_by_beneficiary.get(beneficiary_id)
        if source_research is None:
            continue
        source_revision = _latest_research_revision(session, source_research.id)
        research = Stage2CompanyResearch(
            case_id=source_research.case_id,
            map_id=source_research.map_id,
            candidate_pool_id=pool.id,
            candidate_pool_revision_id=pool_revision.id,
            candidate_pool_membership_id=membership.id,
            beneficiary_id=beneficiary_id,
            beneficiary_revision_id=beneficiary_revision_id,
            selected_map_revision_id=source_research.selected_map_revision_id,
            stock_basic_record_id=source_research.stock_basic_record_id,
            source=f"investment-candidate-{source_research.source}"[:64],
            stock_code=source_research.stock_code,
            created_at_utc=RECORDED,
        )
        session.add(research)
        session.flush()
        revision = Stage2CompanyResearchRevision(
            company_research_id=research.id,
            revision_no=1,
            workflow_state=source_revision.workflow_state,
            conclusion_status=source_revision.conclusion_status,
            research_question=source_revision.research_question,
            summary=source_revision.summary,
            information_cutoff_date=CUTOFF,
            recorded_at_utc=RECORDED,
            supersedes_revision_id=None,
        )
        session.add(revision)
        session.flush()
        research_by_membership[membership.id] = research
        source_research_ids[membership.id] = source_research.id
    return pool, pool_revision, memberships, research_by_membership, source_research_ids

'''
text = text[:start] + replacement + text[end + 1 :]

text = text.replace(
    "    research_revision: Stage2CompanyResearchRevision,\n    scores: dict[str, Decimal],\n",
    "    research_revision: Stage2CompanyResearchRevision,\n    source_research_id: UUID,\n    scores: dict[str, Decimal],\n",
)
text = text.replace(
    "Stage2HandoffClaimLink.company_research_id == research.id",
    "Stage2HandoffClaimLink.company_research_id == source_research_id",
)
text = text.replace(
    "Stage2HandoffEvidenceLink.company_research_id == research.id,",
    "Stage2HandoffEvidenceLink.company_research_id == source_research_id,",
)

old_seed = '''        pool_revision = session.get(
            Stage1CandidatePoolRevision, fixture.stage2.candidate_pool_revision_id
        )
        _add_third_membership(session, pool_revision)
        session.flush()
        memberships = list(
            session.scalars(
                select(Stage1CandidatePoolMembership)
                .where(
                    Stage1CandidatePoolMembership.candidate_pool_revision_id
                    == pool_revision.id
                )
                .order_by(Stage1CandidatePoolMembership.id)
            )
        )
        research_by_membership = {
            row.candidate_pool_membership_id: row
            for row in session.scalars(
                select(Stage2CompanyResearch).where(
                    Stage2CompanyResearch.candidate_pool_revision_id == pool_revision.id
                )
            )
        }
'''
new_seed = '''        source_pool_revision = session.get(
            Stage1CandidatePoolRevision, fixture.stage2.candidate_pool_revision_id
        )
        (
            pool,
            pool_revision,
            memberships,
            research_by_membership,
            source_research_ids,
        ) = _build_three_member_pool(session, source_pool_revision)
'''
if old_seed not in text:
    raise RuntimeError("golden-path seed anchor is missing")
text = text.replace(old_seed, new_seed)
text = text.replace(
    "                research_revision=research_revision,\n                scores=scores,\n",
    "                research_revision=research_revision,\n                source_research_id=source_research_ids[membership.id],\n                scores=scores,\n",
)
text = text.replace(
    "        return fixture.stage2.candidate_pool_id, pool_revision.id, members\n",
    "        return pool.id, pool_revision.id, members\n",
)

for forbidden in ("_add_third_membership", "fixture.stage2.candidate_pool_id, pool_revision.id"):
    if forbidden in text:
        raise RuntimeError(f"golden-path patch left forbidden text: {forbidden}")
TARGET.write_text(text, encoding="utf-8")
compile(text, str(TARGET), "exec")

from __future__ import annotations

from pathlib import Path


def apply_patch() -> bool:
    path = Path("industry_alpha/industry_thesis_owner_acceptance_workbench.py")
    lines = path.read_text(encoding="utf-8").splitlines()
    changed = False

    if any("best_size = max" in line for line in lines):
        start = next(i for i, line in enumerate(lines) if "best_size = max" in line)
        end = next(
            i
            for i in range(start, len(lines))
            if "case_id, map_id, map_revision_id = best_contexts[0]" in lines[i]
        )
        lines[start : end + 1] = [
            "        if len(context_coverage) != 1:",
            "            raise IndustryThesisOwnerAcceptanceError(",
            '                "INDUSTRY_THESIS_ACCEPTANCE_EXACT_MAP_REQUIRED",',
            '                "multiple exact case/map contexts are reachable for the frozen identities",',
            "            )",
            "        selected_context, compatible_stock_ids = next(iter(context_coverage.items()))",
            "        case_id, map_id, map_revision_id = selected_context",
        ]
        lines = [
            line.replace("== best_contexts[0]", "== selected_context").replace(
                '"compatible_frozen_stock_count": best_size,',
                '"compatible_frozen_stock_count": len(compatible_stock_ids),',
            )
            for line in lines
        ]
        changed = True
    elif not any("selected_context, compatible_stock_ids" in line for line in lines):
        raise RuntimeError("owner-context source did not match")

    research_start = next(
        (i for i, line in enumerate(lines) if line == "        research_rows = list("),
        None,
    )
    if research_start is not None:
        research_end = next(
            i
            for i in range(research_start, len(lines))
            if lines[i].startswith("        latest_research:")
        )
        replacement = '''        research_rows: list[
            tuple[Stage2CompanyResearch, Stage2CompanyResearchRevision]
        ] = []
        if pool is not None and pool_revision is not None:
            research_rows = list(
                self._session.execute(
                    select(Stage2CompanyResearch, Stage2CompanyResearchRevision)
                    .join(
                        Stage2CompanyResearchRevision,
                        Stage2CompanyResearchRevision.company_research_id
                        == Stage2CompanyResearch.id,
                    )
                    .join(
                        Stage1CandidatePoolMembership,
                        Stage1CandidatePoolMembership.id
                        == Stage2CompanyResearch.candidate_pool_membership_id,
                    )
                    .where(
                        Stage2CompanyResearch.candidate_pool_id == pool.id,
                        Stage2CompanyResearch.candidate_pool_revision_id
                        == pool_revision.id,
                        Stage1CandidatePoolMembership.candidate_pool_revision_id
                        == pool_revision.id,
                        Stage1CandidatePoolMembership.beneficiary_id
                        == Stage2CompanyResearch.beneficiary_id,
                        Stage1CandidatePoolMembership.beneficiary_revision_id
                        == Stage2CompanyResearch.beneficiary_revision_id,
                        Stage2CompanyResearch.case_id == research_case.id,
                        Stage2CompanyResearch.map_id == industry_map.id,
                        Stage2CompanyResearch.selected_map_revision_id
                        == map_revision.id,
                        Stage2CompanyResearch.beneficiary_revision_id.in_(revision_ids),
                        Stage2CompanyResearchRevision.information_cutoff_date
                        <= as_of_cutoff,
                        Stage2CompanyResearchRevision.recorded_at_utc
                        <= recorded_boundary,
                    )
                    .order_by(
                        Stage2CompanyResearch.id,
                        Stage2CompanyResearchRevision.revision_no,
                    )
                )
            )'''.splitlines()
        lines[research_start:research_end] = replacement
        changed = True
    elif not any(
        "Stage2CompanyResearch.candidate_pool_membership_id" in line for line in lines
    ):
        raise RuntimeError("Company Research source did not match")

    marker = "            company_pair = latest_research.get(revision.id)"
    guard_marker = "                company_pair[0].beneficiary_revision_id != revision.id"
    if marker in lines and guard_marker not in lines:
        index = lines.index(marker) + 1
        lines[index:index] = '''            if company_pair is not None and (
                company_pair[0].beneficiary_id != beneficiary.id
                or company_pair[0].beneficiary_revision_id != revision.id
                or company_pair[0].stock_basic_record_id
                != revision.stock_basic_record_id
                or company_pair[0].case_id != research_case.id
                or company_pair[0].map_id != industry_map.id
                or company_pair[0].selected_map_revision_id != map_revision.id
            ):
                raise IndustryThesisOwnerAcceptanceError(
                    "INDUSTRY_THESIS_ACCEPTANCE_OUTPUT_GRAPH_INCOMPLETE"
                )'''.splitlines()
        changed = True
    elif guard_marker not in lines:
        raise RuntimeError("Company Research member guard did not match")

    if changed:
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed


if __name__ == "__main__":
    apply_patch()

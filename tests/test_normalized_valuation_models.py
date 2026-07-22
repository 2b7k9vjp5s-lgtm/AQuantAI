from industry_alpha.normalized_valuation_models import (
    ACCOUNTING_SCOPES,
    FINANCIAL_METRIC_CODES,
    NORMALIZED_LINK_ROLES,
    NORMALIZED_VALUATION_MODELS,
    SOURCE_KINDS,
    VALUATION_INPUT_ROLES,
    VALUATION_METRIC_CODES,
)


EXPECTED_TABLES = {
    "structured_financial_observations",
    "structured_financial_observation_revisions",
    "structured_financial_observation_claim_links",
    "structured_financial_observation_evidence_links",
    "normalized_valuation_metrics",
    "normalized_valuation_metric_revisions",
    "normalized_valuation_metric_input_links",
    "valuation_comparison_sets",
    "valuation_comparison_set_revisions",
    "valuation_comparison_members",
    "normalized_expectation_gaps",
    "normalized_expectation_gap_revisions",
    "investment_candidate_normalized_metric_links",
}


def test_exact_thirteen_table_contract_and_closed_vocabularies() -> None:
    assert {model.__tablename__ for model in NORMALIZED_VALUATION_MODELS} == EXPECTED_TABLES
    assert len(NORMALIZED_VALUATION_MODELS) == 13
    assert FINANCIAL_METRIC_CODES == (
        "diluted_shares_outstanding",
        "revenue",
        "net_profit_attributable",
        "ebitda",
        "free_cash_flow",
        "net_debt",
    )
    assert VALUATION_METRIC_CODES == ("pe", "ps", "ev_ebitda", "fcf_yield")
    assert SOURCE_KINDS == ("actual", "guidance", "consensus", "research_assumption")
    assert ACCOUNTING_SCOPES == ("consolidated", "consolidated_attributable")
    assert VALUATION_INPUT_ROLES == (
        "canonical_price",
        "price_eligibility",
        "diluted_shares",
        "financial_denominator",
        "net_debt",
    )
    assert NORMALIZED_LINK_ROLES == (
        "valuation_metric",
        "historical_context",
        "peer_context",
        "expectation_gap",
    )


def test_schema_contains_only_typed_targets_for_cross_domain_links() -> None:
    input_columns = {
        column.name
        for column in next(
            model for model in NORMALIZED_VALUATION_MODELS
            if model.__tablename__ == "normalized_valuation_metric_input_links"
        ).__table__.columns
    }
    bridge_columns = {
        column.name
        for column in next(
            model for model in NORMALIZED_VALUATION_MODELS
            if model.__tablename__ == "investment_candidate_normalized_metric_links"
        ).__table__.columns
    }
    assert "target_type" not in input_columns
    assert "target_id" not in input_columns
    assert {
        "canonical_price_revision_id",
        "comparison_eligibility_revision_id",
        "financial_observation_revision_id",
    }.issubset(input_columns)
    assert "target_type" not in bridge_columns
    assert "target_id" not in bridge_columns
    assert {
        "valuation_metric_revision_id",
        "comparison_set_revision_id",
        "expectation_gap_revision_id",
    }.issubset(bridge_columns)

from decimal import Decimal

from equity_research_crewai.build_worksheet_calculations import calculate


INPUTS = {
    "reported_after_tax_earnings": "655",
    "one_time_cost": "492",
    "operating_tax_rate": "0.259",
    "depreciation": "449",
    "capital_expenditures": "379",
    "post_spin_quarterly_interest_expense": "55",
    "interest_annualization_periods": "4",
    "diluted_shares_millions": "149.9",
    "official_close": "126.58",
    "low_multiple": "14.00",
    "mid_multiple": "18.75",
    "high_multiple": "28.00",
    "stress_multiple": "10.00",
    "intended_purchase_size": "500000",
    "maximum_purchase_fraction": "0.05",
}


def test_calculation_keeps_missing_volume_not_computed() -> None:
    result = calculate(INPUTS, {"records": [{"close": "126.58"}]})

    assert Decimal(result["course_owner_cash_flow_usd_millions"]) == Decimal("725")
    assert Decimal(result["adjusted_owner_cash_flow_before_new_debt_interest_usd_millions"]) == Decimal("1089.572")
    assert Decimal(result["after_tax_annualized_post_spin_interest_expense_usd_millions"]) == Decimal("163.020")
    assert Decimal(result["valuation_owner_cash_flow_usd_millions"]) == Decimal("926.552")
    assert result["liquidity_status"] == "not computed"
    assert result["conviction"] == "not computed"


def test_calculation_applies_frozen_valuation_and_liquidity_rules() -> None:
    reader = {
        "records": [
            {"close": "100", "volume": "200000"},
            {"close": "120", "volume": "100000"},
            {"close": "110", "volume": "150000"},
        ]
    }
    result = calculate(INPUTS, reader)

    assert Decimal(result["median_daily_dollar_volume_usd"]) == Decimal("16500000")
    assert Decimal(result["required_median_daily_dollar_volume_usd"]) == Decimal("10000000")
    assert Decimal(result["median_daily_dollar_volume_to_purchase_ratio"]) == Decimal("33")
    assert Decimal(result["purchase_fraction_of_median_daily_dollar_volume"]) == Decimal("1") / Decimal("33")
    assert result["liquidity_status"] == "passes"
    assert Decimal(result["valuation_gap_usd_per_share"]) < 0
    assert result["conviction"] == "low"


def test_calculation_accepts_derived_market_summary_without_raw_records() -> None:
    result = calculate(INPUTS, {"median_daily_dollar_volume": "149976756.72"})

    assert Decimal(result["median_daily_dollar_volume_usd"]) == Decimal("149976756.72")
    assert result["liquidity_status"] == "passes"

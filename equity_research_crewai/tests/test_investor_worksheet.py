from __future__ import annotations

from decimal import Decimal

import pytest

from equity_research_crewai.investor_worksheet import (
    FactLine,
    liquidity_check,
    liquidity_check_from_median,
    owner_cash_flow,
    render_fact,
    render_owner_cash_flow,
    spin_sections_for_ticker,
    value_range,
)


def test_owner_cash_flow_prints_inputs_arithmetic_period_units_and_source() -> None:
    result = owner_cash_flow(Decimal("80"), Decimal("15"), Decimal("20"))
    assert result.value == Decimal("75")
    text = render_owner_cash_flow(result, unit="USD millions", period="FY 2026", citation="Form 10 accession X, p. 50")
    assert "80 + 15 - 20 = 75 USD millions" in text
    assert "FY 2026" in text
    assert "Form 10 accession X" in text


def test_fact_line_uses_not_known_and_full_provenance() -> None:
    fact = FactLine("debt", "Debt sent to child", None, "USD millions", "pro forma at 2026-09-30", "10-12B", "0001", "Unaudited Pro Forma, p. 4", "https://example.test", "pro forma")
    text = render_fact(fact)
    assert "not known USD millions" in text
    assert "10-12B 0001" in text
    assert "pro forma at 2026-09-30" in text


def test_value_range_uses_human_inputs_and_compares_price_to_low() -> None:
    result = value_range(Decimal("10"), method="multiple", low_input=Decimal("5"), mid_input=Decimal("8"), price=Decimal("40"))
    assert result.low_value == Decimal("50")
    assert result.mid_value == Decimal("80")
    assert result.price_vs_low == "more"


def test_value_range_without_close_is_not_computed() -> None:
    result = value_range(Decimal("10"), method="multiple", low_input=Decimal("5"), mid_input=Decimal("8"), price=None)
    assert result.price_vs_low == "not computed"


def test_negative_owner_cash_flow_uses_human_approved_zero_floor() -> None:
    result = value_range(
        Decimal("-8.438312"),
        method="negative owner-cash-flow floor",
        low_input=Decimal("0"),
        mid_input=Decimal("0"),
        price=Decimal("1.71"),
    )

    assert result.low_value == Decimal("0")
    assert result.mid_value == Decimal("0")
    assert result.price_vs_low == "less"


def test_invalid_low_mid_order_is_rejected() -> None:
    with pytest.raises(ValueError, match="low value above"):
        value_range(Decimal("10"), method="capitalization rate", low_input=Decimal("0.05"), mid_input=Decimal("0.10"), price=None)


def test_liquidity_is_added_by_code() -> None:
    result = liquidity_check(
        [(Decimal("10"), Decimal("1000")), (Decimal("12"), Decimal("1000")), (Decimal("20"), Decimal("1000"))],
        intended_purchase_size=Decimal("1000"),
        minimum_ratio=Decimal("10"),
    )
    assert result.median_daily_dollar_volume == Decimal("12000")
    assert result.ratio == Decimal("12")
    assert result.status == "passes"


def test_liquidity_can_use_derived_summary_without_raw_closes() -> None:
    result = liquidity_check_from_median(
        Decimal("12000"),
        intended_purchase_size=Decimal("1000"),
        minimum_ratio=Decimal("10"),
    )
    assert result.ratio == Decimal("12")
    assert result.status == "passes"


def test_non_registry_ticker_marks_only_spin_sections_not_applicable() -> None:
    registry = {
        "included_distributions": [
            {
                "child_ticker": "SPIN",
                "parent": "Parent Inc.",
                "ratio": "1 for 2",
                "record_date": "2026-01-01",
                "distribution_date": "2026-01-15",
                "form10_accession": "0001",
                "form10_url": "https://example.test/form10",
                "section": "The Spin-Off",
            }
        ]
    }

    result = spin_sections_for_ticker(registry, "OTHER")

    assert result["applicable"] is False
    assert set(result.values()) == {False, "not applicable"}
    assert owner_cash_flow(Decimal("80"), Decimal("15"), Decimal("20")).value == Decimal("75")


def test_registry_ticker_returns_filing_provenance() -> None:
    registry = {
        "included_distributions": [
            {
                "child_ticker": "SPIN",
                "parent": "Parent Inc.",
                "ratio": "1 for 2",
                "record_date": "2026-01-01",
                "distribution_date": "2026-01-15",
                "form10_accession": "0001",
                "form10_url": "https://example.test/form10",
                "section": "The Spin-Off",
            }
        ]
    }

    result = spin_sections_for_ticker(registry, "spin")

    assert result["applicable"] is True
    assert result["parent"] == "Parent Inc."
    assert result["form10_accession"] == "0001"

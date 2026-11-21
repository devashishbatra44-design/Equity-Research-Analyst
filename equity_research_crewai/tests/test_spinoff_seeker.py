from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

from equity_research_crewai.closes_reader import CloseRecord
from equity_research_crewai.spinoff_seeker import (
    FINAL_LINE,
    FactorSpec,
    FilingReference,
    Form4Transaction,
    RegistryEntry,
    Stage,
    child_market_cap_is_small,
    child_parent_market_cap_ratio_from_distribution,
    classify_stage,
    first_regular_close_after_distribution,
    has_qualifying_insider_purchase,
    no_debt_funded_cash_payment,
    parse_human_factors,
    render_report,
    score_entry,
)


FORM10 = FilingReference("10-12B", "0000000000-26-000001", "https://example.test/filing", "Item 1")
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def entry(**changes: object) -> RegistryEntry:
    values: dict[str, object] = {
        "name": "Synthetic Child",
        "parent": "Synthetic Parent",
        "child_cik": "0000000001",
        "parent_cik": "0000000002",
        "ratio": "1:4",
        "record_date": date(2026, 11, 5),
        "distribution_date": date(2026, 11, 9),
        "form10": FORM10,
        "distribution_8k": FilingReference("8-K", "0000000000-26-000002", "https://example.test/8k", "Item 8.01"),
        "regular_trading": True,
        "facts": {"F1": True, "F2": True},
    }
    values.update(changes)
    return RegistryEntry(**values)  # type: ignore[arg-type]


def test_stage_truth_table() -> None:
    assert classify_stage(entry(regular_trading=False), run_date=date(2026, 11, 10), window_start=date(2026, 11, 9), window_end=date(2026, 11, 15)) is Stage.REGISTERED
    assert classify_stage(entry(regular_trading=False, listing_approved=True), run_date=date(2026, 11, 10), window_start=date(2026, 11, 9), window_end=date(2026, 11, 15)) is Stage.LISTING_APPROVED
    assert classify_stage(entry(distribution_date=date(2026, 11, 20)), run_date=date(2026, 11, 10), window_start=date(2026, 11, 9), window_end=date(2026, 11, 15)) is Stage.TRADING
    assert classify_stage(entry(), run_date=date(2026, 11, 10), window_start=date(2026, 11, 9), window_end=date(2026, 11, 15)) is Stage.IN_WINDOW
    assert classify_stage(entry(distribution_date=date(2026, 10, 30)), run_date=date(2026, 11, 10), window_start=date(2026, 11, 9), window_end=date(2026, 11, 15)) is Stage.PAST


def test_first_regular_close_on_distribution_date_is_eligible() -> None:
    closes = [
        CloseRecord(date(2026, 11, 9), "TEST", Decimal("9"), "USD", "test"),
        CloseRecord(date(2026, 11, 10), "TEST", Decimal("10"), "USD", "test"),
    ]
    assert first_regular_close_after_distribution(date(2026, 11, 9), closes) == closes[0]


def test_zero_weight_changes_only_its_factor_contribution() -> None:
    factors = [FactorSpec("F1", "yes", Decimal("3"), "zero"), FactorSpec("F2", "yes", Decimal("0"), "zero")]
    result = score_entry(entry(), factors, run_date=date(2026, 11, 10), window_start=date(2026, 11, 9), window_end=date(2026, 11, 15))
    assert result.total_points == Decimal("3")
    assert [point.points for point in result.factor_points] == [Decimal("3"), Decimal("0")]


def test_frozen_human_factor_file_loads_exact_window_and_specs() -> None:
    config = parse_human_factors(REPOSITORY_ROOT / "week04" / "HUMAN_FACTORS.md")
    assert config.window_start == date(2025, 11, 19)
    assert config.window_end == date(2026, 11, 19)
    assert config.index_date == date(2026, 11, 19)
    assert config.post_distribution_window_days == 365
    assert [factor.factor_id for factor in config.factors] == ["F1", "F2", "F3"]
    assert [factor.direction for factor in config.factors] == ["lower", "no", "yes"]
    assert [factor.weight for factor in config.factors] == [Decimal("1")] * 3
    assert [factor.missing_rule for factor in config.factors] == ["unranked"] * 3


def test_f1_uses_inclusive_ten_percent_threshold_and_missing_is_unknown() -> None:
    assert child_market_cap_is_small(Decimal("100"), Decimal("1000")) is True
    assert child_market_cap_is_small(Decimal("100.01"), Decimal("1000")) is False
    assert child_market_cap_is_small(None, Decimal("1000")) is None


def test_f1_ratio_can_be_derived_from_distribution_terms_and_same_date_closes() -> None:
    ratio = child_parent_market_cap_ratio_from_distribution(
        Decimal("0.50"),
        Decimal("0.801"),
        Decimal("149.53"),
        Decimal("338.49"),
    )
    assert ratio == Decimal("0.2757528303069123653337549753")
    assert child_market_cap_is_small(ratio, Decimal("1")) is False
    assert child_parent_market_cap_ratio_from_distribution(None, Decimal("0.801"), Decimal("149.53"), Decimal("338.49")) is None


def test_f2_requires_zero_debt_funded_parent_payment() -> None:
    assert no_debt_funded_cash_payment(Decimal("0")) is True
    assert no_debt_funded_cash_payment(Decimal("0.01")) is False
    assert no_debt_funded_cash_payment(None) is None


def test_f3_uses_code_p_role_and_no_later_than_ninety_days_or_index() -> None:
    distribution = date(2026, 1, 1)
    transactions = [
        Form4Transaction(date(2026, 1, 2), "A", is_officer=True),
        Form4Transaction(date(2026, 4, 1), "P", is_director=True),
    ]
    assert has_qualifying_insider_purchase(
        transactions,
        distribution_date=distribution,
        index_date=date(2026, 11, 19),
    ) is True
    assert has_qualifying_insider_purchase(
        [Form4Transaction(date(2026, 4, 2), "P", is_director=True)],
        distribution_date=distribution,
        index_date=date(2026, 11, 19),
    ) is False
    assert has_qualifying_insider_purchase(
        [Form4Transaction(date(2026, 1, 10), "P")],
        distribution_date=distribution,
        index_date=date(2026, 11, 19),
    ) is False
    assert has_qualifying_insider_purchase(
        [Form4Transaction(date(2026, 1, 10), "P", is_officer=True)],
        distribution_date=distribution,
        index_date=date(2026, 1, 5),
    ) is False
    assert has_qualifying_insider_purchase(
        None,
        distribution_date=distribution,
        index_date=date(2026, 11, 19),
    ) is None


def test_frozen_factor_scoring_has_equal_points_and_missing_is_unranked() -> None:
    factors = parse_human_factors(REPOSITORY_ROOT / "week04" / "HUMAN_FACTORS.md").factors
    ranked = score_entry(
        entry(facts={"F1": True, "F2": False, "F3": True}),
        factors,
        run_date=date(2026, 11, 19),
        window_start=date(2025, 11, 19),
        window_end=date(2026, 11, 19),
    )
    assert ranked.total_points == Decimal("2")
    assert [point.points for point in ranked.factor_points] == [Decimal("1"), Decimal("0"), Decimal("1")]

    unranked = score_entry(
        entry(facts={"F1": True, "F2": True}),
        factors,
        run_date=date(2026, 11, 19),
        window_start=date(2025, 11, 19),
        window_end=date(2026, 11, 19),
    )
    assert unranked.total_points is None
    assert unranked.unranked_reason == "factor F3 missing"
    report = render_report(
        [unranked],
        run_date=date(2026, 11, 19),
        price_date=None,
        index_date=date(2026, 11, 19),
    )
    assert "  - F1: true; 1 point" in report
    assert "  - F2: true; 1 point" in report
    assert "  - F3: missing; 0 points" in report
    assert "parent: Synthetic Parent" in report
    assert "distributed: 2026-11-09" in report
    assert "window ends: 2027-11-09" in report
    assert "price not available" in report


def test_missing_required_date_is_unranked_and_not_estimated() -> None:
    result = score_entry(entry(record_date=None), [], run_date=date(2026, 11, 10), window_start=date(2026, 11, 9), window_end=date(2026, 11, 15))
    assert result.total_points is None
    assert result.unranked_reason == "required date missing"


def test_non_spin_is_dropped_with_filing_reason() -> None:
    result = score_entry(entry(record_date=None, distribution_date=None, is_spinoff=False, drop_reason="registrant was already public"), [], run_date=date(2026, 11, 10), window_start=date(2026, 11, 9), window_end=date(2026, 11, 15))
    report = render_report([result], run_date=date(2026, 11, 14), price_date=None, index_date=date(2026, 11, 13))
    assert "registrant was already public" in report
    assert FORM10.accession in report


def test_report_has_required_sections_and_exact_last_line() -> None:
    close = CloseRecord(date(2026, 11, 9), "TEST", Decimal("12.34"), "USD", "exchange")
    result = score_entry(entry(), [FactorSpec("F1", "yes", Decimal("1"), "zero")], run_date=date(2026, 11, 10), window_start=date(2026, 11, 9), window_end=date(2026, 11, 15), closes=[close])
    report = render_report([result], run_date=date(2026, 11, 14), price_date=date(2026, 11, 13), index_date=date(2026, 11, 13))
    assert report.splitlines()[0] == "Run date: 2026-11-14 | Price date: 2026-11-13 | Index date: 2026-11-13"
    assert all(section in report for section in ("## Ranked", "## Watch", "## Dropped", "## Data limits"))
    assert "12.34 USD on 2026-11-09" in report
    assert report.splitlines()[-1] == FINAL_LINE

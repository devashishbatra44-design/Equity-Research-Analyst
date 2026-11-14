from __future__ import annotations

from datetime import date
from decimal import Decimal

from equity_research_crewai.closes_reader import CloseRecord
from equity_research_crewai.spinoff_seeker import (
    FINAL_LINE,
    FactorSpec,
    FilingReference,
    RegistryEntry,
    Stage,
    classify_stage,
    first_regular_close_after_distribution,
    render_report,
    score_entry,
)


FORM10 = FilingReference("10-12B", "0000000000-26-000001", "https://example.test/filing", "Item 1")


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


def test_first_close_is_strictly_after_distribution() -> None:
    closes = [
        CloseRecord(date(2026, 11, 9), "TEST", Decimal("9"), "USD", "test"),
        CloseRecord(date(2026, 11, 10), "TEST", Decimal("10"), "USD", "test"),
    ]
    assert first_regular_close_after_distribution(date(2026, 11, 9), closes) == closes[1]


def test_zero_weight_changes_only_its_factor_contribution() -> None:
    factors = [FactorSpec("F1", "yes", Decimal("3"), "zero"), FactorSpec("F2", "yes", Decimal("0"), "zero")]
    result = score_entry(entry(), factors, run_date=date(2026, 11, 10), window_start=date(2026, 11, 9), window_end=date(2026, 11, 15))
    assert result.total_points == Decimal("3")
    assert [point.points for point in result.factor_points] == [Decimal("3"), Decimal("0")]


def test_missing_required_date_is_unranked_and_not_estimated() -> None:
    result = score_entry(entry(record_date=None), [], run_date=date(2026, 11, 10), window_start=date(2026, 11, 9), window_end=date(2026, 11, 15))
    assert result.total_points is None
    assert result.unranked_reason == "required date missing"


def test_non_spin_is_dropped_with_filing_reason() -> None:
    result = score_entry(entry(is_spinoff=False, drop_reason="registrant was already public"), [], run_date=date(2026, 11, 10), window_start=date(2026, 11, 9), window_end=date(2026, 11, 15))
    report = render_report([result], run_date=date(2026, 11, 14), price_date=None, index_date=date(2026, 11, 13))
    assert "registrant was already public" in report
    assert FORM10.accession in report


def test_report_has_required_sections_and_exact_last_line() -> None:
    result = score_entry(entry(), [FactorSpec("F1", "yes", Decimal("1"), "zero")], run_date=date(2026, 11, 10), window_start=date(2026, 11, 9), window_end=date(2026, 11, 15))
    report = render_report([result], run_date=date(2026, 11, 14), price_date=date(2026, 11, 13), index_date=date(2026, 11, 13))
    assert report.splitlines()[0] == "Run date: 2026-11-14 | Price date: 2026-11-13 | Index date: 2026-11-13"
    assert all(section in report for section in ("## Ranked", "## Watch", "## Dropped", "## Data limits"))
    assert report.splitlines()[-1] == FINAL_LINE

from __future__ import annotations

from datetime import date
from decimal import Decimal

from equity_research_crewai.closes_reader import CloseRecord
from equity_research_crewai.hit_rate import HitRateRow, first_close_after_filing, reaction_percent, summarize


def close(day: int, value: str) -> CloseRecord:
    return CloseRecord(date(2026, 11, day), "TEST", Decimal(value), "USD", "licensed test")


def test_reaction_uses_last_close_before_and_first_close_after() -> None:
    assert reaction_percent(close(10, "100"), close(11, "105")) == Decimal("5.00")


def test_first_close_after_pre_market_filing_is_same_day_close() -> None:
    result = first_close_after_filing("2026-11-10T08:00:00-05:00", [close(10, "100"), close(11, "105")])
    assert result == close(10, "100")


def test_first_close_after_after_market_filing_is_next_day_close() -> None:
    result = first_close_after_filing("2026-11-10T16:05:00-05:00", [close(10, "100"), close(11, "105")])
    assert result == close(11, "105")


def test_summary_excludes_after_and_not_computed_rows() -> None:
    rows = [
        HitRateRow("A", "t", "t", "up", Decimal("2"), "agree", False),
        HitRateRow("B", "t", "t", "down", Decimal("1"), "disagree", True),
        HitRateRow("C", "t", "t", "not computed", None, "not computed", False),
    ]
    assert summarize(rows) == {"scored": 1, "agreed": 1, "disagreed": 0, "hit_rate": "1.0000"}

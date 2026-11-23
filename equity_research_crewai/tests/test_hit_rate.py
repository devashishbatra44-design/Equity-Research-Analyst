from __future__ import annotations

from datetime import date
from decimal import Decimal

from equity_research_crewai.closes_reader import CloseRecord
import json

from equity_research_crewai.hit_rate import (
    HitRateRow,
    first_close_after_filing,
    last_close_before_filing,
    reaction_percent,
    render_table,
    row_from_saved_run,
    summarize,
)


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


def test_last_close_before_after_market_filing_is_same_day_close() -> None:
    result = last_close_before_filing("2026-11-10T16:05:00-05:00", [close(10, "100"), close(11, "105")])
    assert result == close(10, "100")


def test_saved_run_table_preserves_not_computed_view(tmp_path) -> None:
    run = tmp_path / "TEST_run"
    run.mkdir()
    (run / "hit_rate_view.json").write_text(
        json.dumps(
            {
                "ticker": "TEST",
                "filing_time": "2026-11-10T16:05:00-05:00",
                "view_time": "2026-11-10T18:00:00-05:00",
                "direction": "not computed",
            }
        ),
        encoding="utf-8",
    )
    (run / "hit_rate_closes.json").write_text(
        json.dumps(
            {
                "records": [
                    close(10, "100").to_dict(),
                    close(11, "105").to_dict(),
                ]
            }
        ),
        encoding="utf-8",
    )

    row = row_from_saved_run(run)

    assert row.reaction == Decimal("5.00")
    assert row.direction == "not computed"
    assert row.agreement == "not computed"
    assert row.after is False
    assert "hit rate: not computed" in render_table([row])


def test_saved_run_can_use_derived_summary_without_raw_close_list(tmp_path) -> None:
    run = tmp_path / "TEST_run"
    run.mkdir()
    (run / "hit_rate_view.json").write_text(
        json.dumps(
            {
                "ticker": "TEST",
                "filing_time": "2026-11-10T16:05:00-05:00",
                "view_time": "2026-11-10T18:00:00-05:00",
                "direction": "not computed",
                "market_data_summary": {
                    "source": "licensed test",
                    "currency": "USD",
                    "pre_filing_close": {"pricing_date": "2026-11-10", "close": "100"},
                    "first_post_filing_close": {"pricing_date": "2026-11-11", "close": "105"},
                },
            }
        ),
        encoding="utf-8",
    )
    row = row_from_saved_run(run)
    assert row.reaction == Decimal("5.00")
    assert row.agreement == "not computed"


def test_summary_excludes_after_and_not_computed_rows() -> None:
    rows = [
        HitRateRow("A", "t", "t", "up", Decimal("2"), "agree", False),
        HitRateRow("B", "t", "t", "down", Decimal("1"), "disagree", True),
        HitRateRow("C", "t", "t", "not computed", None, "not computed", False),
    ]
    assert summarize(rows) == {"scored": 1, "agreed": 1, "disagreed": 0, "hit_rate": "1.0000"}

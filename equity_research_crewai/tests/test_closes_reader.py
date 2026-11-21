from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from equity_research_crewai.closes_reader import (
    last_close_before,
    official_daily_closes,
    parse_filed_datetime,
)


CSV_TEXT = """Instrument,Date,TR.PriceClose,Currency
TEST.O,2026-11-06,99.50,USD
OTHER.O,2026-11-09,500.00,USD
TEST.O,2026-11-09,101.25,USD
TEST.O,2026-11-10,102.75,USD
"""

CSV_WITH_VOLUME = """Instrument,Date,TR.PriceClose,TR.Volume,Currency
TEST.O,2026-11-09,101.25,125000,USD
TEST.O,2026-11-10,102.75,140000,USD
"""


@pytest.fixture()
def close_export(tmp_path: Path) -> Path:
    path = tmp_path / "licensed-closes.csv"
    path.write_text(CSV_TEXT, encoding="utf-8")
    return path


def test_official_daily_closes_filters_instrument_and_inclusive_dates(close_export: Path) -> None:
    result = official_daily_closes("test.o", "2026-11-09", "2026-11-10", export_path=close_export)

    assert result.status == "available"
    assert [record.pricing_date for record in result.records] == [date(2026, 11, 9), date(2026, 11, 10)]
    assert [record.close for record in result.records] == [Decimal("101.25"), Decimal("102.75")]
    assert all(record.currency == "USD" for record in result.records)
    assert all(record.volume is None for record in result.records)


def test_official_daily_closes_retains_optional_volume(tmp_path: Path) -> None:
    path = tmp_path / "licensed-close-and-volume.csv"
    path.write_text(CSV_WITH_VOLUME, encoding="utf-8")

    result = official_daily_closes("TEST.O", "2026-11-09", "2026-11-10", export_path=path)

    assert result.status == "available"
    assert [record.volume for record in result.records] == [Decimal("125000"), Decimal("140000")]
    assert result.to_dict()["records"][0]["volume"] == "125000"


def test_local_export_preserves_exact_source_label(close_export: Path) -> None:
    result = official_daily_closes(
        "TEST.O",
        "2026-11-09",
        "2026-11-10",
        export_path=close_export,
        export_source="Nasdaq official historical endpoint",
    )

    assert result.status == "available"
    assert all(record.source == "Nasdaq official historical endpoint" for record in result.records)


def test_last_close_before_pre_market_filing_uses_prior_trading_day(close_export: Path) -> None:
    result = last_close_before("TEST.O", "2026-11-10T08:30:00-05:00", export_path=close_export)

    assert result.status == "available"
    assert result.records[0].pricing_date == date(2026, 11, 9)
    assert result.records[0].close == Decimal("101.25")


def test_last_close_before_after_market_filing_uses_same_day(close_export: Path) -> None:
    result = last_close_before("TEST.O", "2026-11-10T16:05:00-05:00", export_path=close_export)

    assert result.status == "available"
    assert result.records[0].pricing_date == date(2026, 11, 10)


def test_exact_market_close_time_is_not_strictly_before(close_export: Path) -> None:
    result = last_close_before("TEST.O", "2026-11-10T16:00:00-05:00", export_path=close_export)

    assert result.status == "available"
    assert result.records[0].pricing_date == date(2026, 11, 9)


def test_utc_filing_time_is_converted_to_eastern(close_export: Path) -> None:
    parsed = parse_filed_datetime("2026-11-10T21:05:00Z")
    result = last_close_before("TEST.O", "2026-11-10T21:05:00Z", export_path=close_export)

    assert parsed.isoformat() == "2026-11-10T16:05:00-05:00"
    assert result.records[0].pricing_date == date(2026, 11, 10)


def test_missing_export_finishes_as_not_available(tmp_path: Path) -> None:
    result = official_daily_closes(
        "TEST.O",
        "2026-11-09",
        "2026-11-10",
        export_path=tmp_path / "missing.csv",
    )

    assert result.status == "not available"
    assert result.records == ()
    assert "not found" in result.message


def test_empty_date_window_finishes_as_not_available(close_export: Path) -> None:
    result = official_daily_closes("TEST.O", "2026-11-07", "2026-11-08", export_path=close_export)

    assert result.status == "not available"
    assert result.records == ()


def test_conflicting_same_day_closes_are_not_silently_selected(tmp_path: Path) -> None:
    path = tmp_path / "conflict.csv"
    path.write_text(
        "Instrument,Date,Close\nTEST.O,2026-11-09,100\nTEST.O,2026-11-09,101\n",
        encoding="utf-8",
    )

    result = official_daily_closes("TEST.O", "2026-11-09", "2026-11-09", export_path=path)

    assert result.status == "not available"
    assert "Conflicting closes" in result.message


def test_invalid_range_is_a_user_error(close_export: Path) -> None:
    with pytest.raises(ValueError, match="End date"):
        official_daily_closes("TEST.O", "2026-11-10", "2026-11-09", export_path=close_export)

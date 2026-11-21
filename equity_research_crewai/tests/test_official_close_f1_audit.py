from datetime import date
from decimal import Decimal

from equity_research_crewai.official_close_f1_audit import (
    first_on_or_after,
    on_date,
    parse_historical_rows,
)


def test_nasdaq_rows_parse_and_sort_regular_closes() -> None:
    payload = {
        "data": {
            "tradesTable": {
                "rows": [
                    {"date": "06/02/2026", "close": "$12.40"},
                    {"date": "06/01/2026", "close": "12.30"},
                ]
            }
        }
    }
    rows = parse_historical_rows(payload, "TEST")
    assert rows[0]["pricing_date"] == date(2026, 6, 1)
    assert rows[0]["close_usd"] == Decimal("12.30")
    assert first_on_or_after(rows, date(2026, 6, 1)) == rows[0]
    assert on_date(rows, date(2026, 6, 2)) == rows[1]

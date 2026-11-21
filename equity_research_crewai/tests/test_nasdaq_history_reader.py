from equity_research_crewai.nasdaq_history_reader import normalize


def test_normalizes_close_and_volume_in_date_order() -> None:
    payload = {
        "data": {
            "tradesTable": {
                "rows": [
                    {"date": "11/19/2026", "close": "$126.58", "volume": "1,415,231"},
                    {"date": "11/18/2026", "close": "$130.00", "volume": "900,000"},
                ]
            }
        }
    }

    result = normalize(payload, "fdxf", "https://api.nasdaq.test/history")

    assert result["status"] == "available"
    assert result["records"][0]["pricing_date"] == "2026-11-18"
    assert result["records"][1]["close"] == "126.58"
    assert result["records"][1]["volume"] == "1415231"


def test_missing_volume_is_not_silently_used() -> None:
    payload = {"data": {"tradesTable": {"rows": [{"date": "11/19/2026", "close": "$126.58"}]}}}

    result = normalize(payload, "FDXF", "https://api.nasdaq.test/history")

    assert result["status"] == "not available"
    assert result["records"] == []

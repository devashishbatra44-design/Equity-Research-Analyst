from equity_research_crewai.nasdaq_history_reader import normalize, summarize


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


def test_summary_keeps_only_derived_market_metrics() -> None:
    payload = {
        "data": {
            "tradesTable": {
                "rows": [
                    {"date": "11/10/2026", "close": "$10", "volume": "10,000"},
                    {"date": "11/09/2026", "close": "$11", "volume": "10,000"},
                ]
            }
        }
    }

    summary = summarize(normalize(payload, "test", "https://api.nasdaq.test/history"))

    assert summary["observation_count"] == 2
    assert summary["start_date"] == "2026-11-09"
    assert summary["end_date"] == "2026-11-10"
    assert summary["median_daily_dollar_volume"] == "105000"
    assert "records" not in summary

from equity_research_crewai.sec_form10_text_screen import (
    evidence_snippets,
    filing_text,
    select_latest_form10_rows,
)


def test_filing_text_normalizes_html_and_entities() -> None:
    assert filing_text("<p>Spin-off&nbsp; text</p>\n<p>next</p>") == "Spin-off text next"


def test_snippets_are_bounded_and_find_spinoff_language() -> None:
    text = "A" * 300 + " spin-off distribution of shares to stockholders " + "B" * 300
    snippets = evidence_snippets(text, limit=1, radius=20)
    assert len(snippets) == 1
    assert "spin-off" in snippets[0]
    assert len(snippets[0]) < len(text)


def test_latest_form10_row_is_selected_per_cik() -> None:
    rows = [
        {"cik": "1", "form": "10-12B", "filed_date": "2026-01-01", "accession": "a"},
        {"cik": "1", "form": "10-12B/A", "filed_date": "2026-02-01", "accession": "b"},
        {"cik": "2", "form": "8-K", "filed_date": "2026-03-01", "accession": "c"},
    ]
    selected = select_latest_form10_rows(rows)
    assert len(selected) == 1
    assert selected[0]["accession"] == "b"

from __future__ import annotations

from pathlib import Path

from equity_research_crewai.extract_worksheet_inputs import extract


def test_extracts_filing_human_market_and_constant_inputs(tmp_path: Path) -> None:
    (tmp_path / "filing.txt").write_text("Revenue\n$\n1,234\n", encoding="utf-8")
    spec = {
        "facts": [
            {
                "id": "revenue",
                "source_file": "filing.txt",
                "line_start": 1,
                "line_end": 3,
                "pattern": r"Revenue\s+\$\s+([0-9,]+)",
                "unit": "USD millions",
                "period": "FY 2026",
                "form": "10-K",
                "accession": "0001",
                "section": "Statements of Income",
            }
        ],
        "human_inputs": {"low_multiple": "low_multiple"},
        "market_inputs": {"official_close": "end_date_close"},
        "constants": {"periods": "4"},
    }

    inputs, evidence = extract(
        tmp_path,
        spec,
        {"low_multiple": "14.00"},
        {"end_date_close": "126.58"},
    )

    assert inputs == {
        "revenue": "1234",
        "low_multiple": "14.00",
        "official_close": "126.58",
        "periods": "4",
    }
    assert evidence["facts"][0]["saved_lines"] == "1-3"


def test_extracts_text_and_date_facts(tmp_path: Path) -> None:
    (tmp_path / "filing.txt").write_text(
        "Parent: Example Holdings\nRecord date: May 15, 2026\n",
        encoding="utf-8",
    )
    spec = {
        "facts": [
            {
                "id": "parent",
                "source_file": "filing.txt",
                "line_start": 1,
                "line_end": 1,
                "pattern": r"Parent: (.+)",
                "value_type": "text",
                "unit": "name",
                "period": "transaction",
                "form": "10",
                "accession": "0000000000-00-000001",
                "section": "Transaction",
            },
            {
                "id": "record_date",
                "source_file": "filing.txt",
                "line_start": 2,
                "line_end": 2,
                "pattern": r"Record date: (.+)",
                "value_type": "date",
                "unit": "date",
                "period": "transaction",
                "form": "10",
                "accession": "0000000000-00-000001",
                "section": "Transaction",
            },
        ]
    }
    inputs, evidence = extract(tmp_path, spec, {}, {})
    assert inputs == {"parent": "Example Holdings", "record_date": "May 15, 2026"}
    assert evidence["facts"][0]["value_type"] == "text"
    assert evidence["facts"][1]["value_type"] == "date"

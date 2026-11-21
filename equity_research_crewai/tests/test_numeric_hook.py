from __future__ import annotations

import json
from pathlib import Path

import pytest

from equity_research_crewai.numeric_hook import REFUSAL, verify_document, verify_file


BASE = {
    "id": "ocf",
    "kind": "arithmetic",
    "value": "75",
    "unit": "USD millions",
    "period": "FY 2026",
    "source": "Form 10 accession X, p. 50",
    "inputs": ["80", "15", "20"],
    "operation": "a_plus_b_minus_c",
}

SCORE = {
    "id": "score_owner_cash_flow",
    "kind": "analytical_score",
    "value": "4",
    "unit": "ordinal score",
    "period": "worksheet judgment date",
    "source": "HUMAN_INVESTOR_PERSONA.md and cited worksheet evidence",
    "criterion": "Standalone earning power and owner cash flow",
    "persona_file": "HUMAN_INVESTOR_PERSONA.md",
    "scale_min": "1",
    "scale_max": "5",
    "evidence_claim_ids": ["ocf"],
    "used_in_composite": False,
}


def test_clean_document_is_silent_eligible() -> None:
    result = verify_document({"numeric_claims": [BASE]})
    assert result.ok
    assert result.errors == ()


def test_seeded_error_by_one_is_refused() -> None:
    result = verify_document({"numeric_claims": [{**BASE, "value": "76"}]})
    assert not result.ok
    assert "printed arithmetic does not recompute" in result.errors[0]
    assert REFUSAL.startswith("REFUSE")


@pytest.mark.parametrize(
    ("operation", "inputs", "value", "round_places"),
    [
        ("identity", ["1"], "1", None),
        ("multiply", ["3.7", "1000"], "3700", None),
        ("multiply_one_minus", ["492", "0.259"], "364.572", None),
        ("multiply_divide", ["1089.572", "14", "149.9"], "101.76", 2),
        ("percentage", ["500000", "149976756.72"], "0.3334", 4),
        ("absolute_difference", ["101.76", "126.58"], "24.82", 2),
    ],
)
def test_supported_worksheet_arithmetic(
    operation: str, inputs: list[str], value: str, round_places: int | None
) -> None:
    claim = {**BASE, "operation": operation, "inputs": inputs, "value": value}
    if round_places is not None:
        claim["round_places"] = round_places
    assert verify_document({"numeric_claims": [claim]}).ok


def test_unknown_numeric_kind_fails() -> None:
    result = verify_document({"numeric_claims": [{**BASE, "kind": "model_guess"}]})
    assert not result.ok
    assert "unknown numeric kind" in result.errors[0]


def test_analytical_score_accepts_frozen_scale_and_source_evidence() -> None:
    result = verify_document({"numeric_claims": [BASE, SCORE]})
    assert result.ok
    assert result.errors == ()


@pytest.mark.parametrize("value", ["0", "6", "3.5"])
def test_analytical_score_rejects_out_of_range_or_noninteger_value(value: str) -> None:
    result = verify_document({"numeric_claims": [BASE, {**SCORE, "value": value}]})
    assert not result.ok
    assert any("integer from 1 through 5" in error for error in result.errors)


def test_analytical_score_requires_existing_source_evidence() -> None:
    result = verify_document(
        {"numeric_claims": [BASE, {**SCORE, "evidence_claim_ids": ["missing_fact"]}]}
    )
    assert not result.ok
    assert any("does not exist" in error for error in result.errors)


def test_analytical_score_cannot_feed_a_composite() -> None:
    result = verify_document(
        {"numeric_claims": [BASE, {**SCORE, "used_in_composite": True}]}
    )
    assert not result.ok
    assert any("must not be used in a composite" in error for error in result.errors)


def test_only_dates_accessions_and_line_numbers_are_ignored() -> None:
    claims = [
        {"id": "d", "kind": "date", "value": 2026},
        {"id": "a", "kind": "accession", "value": 1},
        {"id": "l", "kind": "line_number", "value": 99},
    ]
    assert verify_document({"numeric_claims": claims}).ok


def test_human_rate_must_match_frozen_config() -> None:
    claim = {**BASE, "kind": "human_rate", "value": "0.10", "frozen_value": "0.09"}
    result = verify_document({"numeric_claims": [claim]})
    assert not result.ok
    assert any("frozen human configuration" in error for error in result.errors)


def test_saved_worksheet_requires_classification_for_every_number(tmp_path: Path) -> None:
    (tmp_path / "worksheet.md").write_text("Owner cash flow: 80 + 15 - 20 = 75 USD millions\n", encoding="utf-8")
    document = {
        "worksheet_file": "worksheet.md",
        "numeric_claims": [
            {**BASE, "worksheet_line": 1, "token": token, "id": f"n{index}", "kind": "arithmetic" if token == "75" else "line_number"}
            for index, token in enumerate(("80", "15", "20", "75"), start=1)
        ],
    }
    path = tmp_path / "worksheet.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    assert verify_file(path).ok

    document["numeric_claims"] = document["numeric_claims"][:-1]
    path.write_text(json.dumps(document), encoding="utf-8")
    result = verify_file(path)
    assert not result.ok
    assert "unclassified numeric token '75'" in result.errors[-1]


def test_filing_fact_matches_exact_saved_line(tmp_path: Path) -> None:
    (tmp_path / "form10.txt").write_text("Revenue was 123 USD millions.\n", encoding="utf-8")
    claim = {
        "id": "revenue",
        "kind": "filing_fact",
        "value": "123",
        "token": "123",
        "unit": "USD millions",
        "period": "FY 2026",
        "source": "Form 10",
        "tag": "Revenue",
        "filing": "10-12B",
        "accession": "0001",
        "section": "Financial statements",
        "saved_line": 1,
        "source_file": "form10.txt",
        "source_line": 1,
    }
    path = tmp_path / "worksheet.json"
    path.write_text(json.dumps({"numeric_claims": [claim]}), encoding="utf-8")
    assert verify_file(path).ok
    claim["token"] = "124"
    claim["value"] = "124"
    path.write_text(json.dumps({"numeric_claims": [claim]}), encoding="utf-8")
    assert "absent from the cited saved filing line" in verify_file(path).errors[-1]


def test_price_matches_saved_closes_reader_record(tmp_path: Path) -> None:
    (tmp_path / "close.json").write_text(
        json.dumps({"records": [{"instrument": "TEST.O", "pricing_date": "2026-11-10", "close": "101.25"}]}),
        encoding="utf-8",
    )
    claim = {
        "id": "price",
        "kind": "licensed_price",
        "value": "101.25",
        "unit": "USD/share",
        "period": "2026-11-10 close",
        "source": "LSEG",
        "instrument": "TEST.O",
        "price_date": "2026-11-10",
        "reader_source": "LSEG Workspace export",
        "reader_file": "close.json",
    }
    path = tmp_path / "worksheet.json"
    path.write_text(json.dumps({"numeric_claims": [claim]}), encoding="utf-8")
    assert verify_file(path).ok


def test_official_exchange_price_matches_saved_reader_record(tmp_path: Path) -> None:
    (tmp_path / "close.json").write_text(
        json.dumps({"records": [{"instrument": "TEST", "pricing_date": "2026-11-19", "close": "126.58"}]}),
        encoding="utf-8",
    )
    claim = {
        "id": "official_close",
        "kind": "official_exchange_price",
        "value": "126.58",
        "unit": "USD/share",
        "period": "2026-11-19 close",
        "source": "Nasdaq official historical endpoint",
        "instrument": "TEST",
        "price_date": "2026-11-19",
        "reader_source": "Nasdaq official historical endpoint",
        "reader_file": "close.json",
    }
    path = tmp_path / "worksheet.json"
    path.write_text(json.dumps({"numeric_claims": [claim]}), encoding="utf-8")

    assert verify_file(path).ok


@pytest.mark.parametrize(
    ("metric", "value", "unit"),
    [
        ("observation_count", "2", "regular trading sessions"),
        ("median_daily_dollar_volume", "250", "USD per day"),
    ],
)
def test_market_metric_matches_saved_reader_records(
    tmp_path: Path, metric: str, value: str, unit: str
) -> None:
    (tmp_path / "close.json").write_text(
        json.dumps(
            {
                "records": [
                    {"instrument": "TEST", "pricing_date": "2026-11-18", "close": "10", "volume": "20"},
                    {"instrument": "TEST", "pricing_date": "2026-11-19", "close": "10", "volume": "30"},
                ]
            }
        ),
        encoding="utf-8",
    )
    claim = {
        "id": metric,
        "kind": "market_metric",
        "value": value,
        "unit": unit,
        "period": "2026-11-18 through 2026-11-19",
        "source": "Nasdaq official historical endpoint",
        "instrument": "TEST",
        "metric": metric,
        "reader_source": "Nasdaq official historical endpoint",
        "reader_file": "close.json",
    }
    path = tmp_path / "worksheet.json"
    path.write_text(json.dumps({"numeric_claims": [claim]}), encoding="utf-8")

    assert verify_file(path).ok


def test_analytical_score_criterion_must_exist_in_frozen_persona(tmp_path: Path) -> None:
    (tmp_path / "HUMAN_INVESTOR_PERSONA.md").write_text(
        "## Criteria I score\n\nStandalone earning power and owner cash flow\n",
        encoding="utf-8",
    )
    path = tmp_path / "worksheet.json"
    path.write_text(json.dumps({"numeric_claims": [BASE, SCORE]}), encoding="utf-8")
    assert verify_file(path).ok

    bad_score = {**SCORE, "criterion": "Unsupported criterion"}
    path.write_text(json.dumps({"numeric_claims": [BASE, bad_score]}), encoding="utf-8")
    result = verify_file(path)
    assert not result.ok
    assert any("criterion is absent" in error for error in result.errors)

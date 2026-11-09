from __future__ import annotations

import json
from pathlib import Path

from equity_research_crewai.faskills_extension import calculate_metrics, crosscheck_with_sec
from equity_research_crewai.verifier import verify_insight_claims


def statement_payload() -> dict:
    return {
        "financials": {
            "income_statements": [
                {
                    "ticker": "TEST", "period": "annual", "report_period": "2025-12-31",
                    "accession_number": "acc-current", "currency": "USD", "revenue": 200,
                    "gross_profit": 80, "selling_general_and_administrative_expenses": 20,
                    "net_income": 20, "ebit": 30, "operating_income": 30,
                    "income_tax_expense": 5, "earnings_per_share_diluted": 2,
                },
                {
                    "ticker": "TEST", "period": "annual", "report_period": "2024-12-31",
                    "accession_number": "acc-prior", "currency": "USD", "revenue": 180,
                    "gross_profit": 72, "selling_general_and_administrative_expenses": 18,
                    "net_income": 18, "ebit": 27, "operating_income": 27,
                    "income_tax_expense": 4, "earnings_per_share_diluted": 1.8,
                },
            ],
            "balance_sheets": [
                {
                    "period": "annual", "report_period": "2025-12-31", "accession_number": "acc-current",
                    "current_assets": 100, "current_liabilities": 50, "retained_earnings": 40,
                    "total_assets": 300, "total_liabilities": 150, "outstanding_shares": 10,
                    "non_current_debt": 60, "trade_and_non_trade_receivables": 30,
                    "property_plant_and_equipment": 100, "total_debt": 70,
                    "shareholders_equity": 150,
                },
                {
                    "period": "annual", "report_period": "2024-12-31", "accession_number": "acc-prior",
                    "current_assets": 80, "current_liabilities": 45, "retained_earnings": 30,
                    "total_assets": 270, "total_liabilities": 140, "outstanding_shares": 11,
                    "non_current_debt": 65, "trade_and_non_trade_receivables": 25,
                    "property_plant_and_equipment": 90, "total_debt": 75,
                    "shareholders_equity": 130,
                },
            ],
            "cash_flow_statements": [
                {
                    "period": "annual", "report_period": "2025-12-31", "accession_number": "acc-current",
                    "net_cash_flow_from_operations": 30, "depreciation_and_amortization": 10,
                    "capital_expenditure": -15, "free_cash_flow": 15,
                },
                {
                    "period": "annual", "report_period": "2024-12-31", "accession_number": "acc-prior",
                    "net_cash_flow_from_operations": 25, "depreciation_and_amortization": 9,
                    "capital_expenditure": -14, "free_cash_flow": 11,
                },
            ],
        }
    }


def test_course_safe_metrics_are_deterministic_and_use_prior_period_assets() -> None:
    result = calculate_metrics(statement_payload(), price=25)
    metrics = result["metrics"]
    assert metrics["piotroski_f_score"]["validation_status"] == "available"
    assert metrics["owner_earnings"]["value"] == 0
    assert metrics["owner_earnings"]["inputs"]["working_capital_change"] == 15
    assert round(metrics["beneish_m_score"]["components"]["aqi"], 6) == 0.9
    assert metrics["altman_z_manufacturing"]["note"].startswith("Use only")
    assert metrics["altman_z_nonmanufacturing"]["note"].startswith("Use only")


def test_missing_beneish_input_stays_unavailable() -> None:
    payload = statement_payload()
    payload["financials"]["balance_sheets"][0]["trade_and_non_trade_receivables"] = None
    metric = calculate_metrics(payload, price=25)["metrics"]["beneish_m_score"]
    assert metric["validation_status"] == "unavailable"
    assert metric["value"] is None
    assert "balance.trade_and_non_trade_receivables" in metric["missing_fields"]


def test_financialdatasets_values_must_match_saved_sec_facts() -> None:
    facts = {
        "concepts": {
            "total_revenue": {"current": {"value": 200, "period_end": "2025-12-31"}},
            "operating_income": {"current": {"value": 30, "period_end": "2025-12-31"}},
            "net_income": {"current": {"value": 20, "period_end": "2025-12-31"}},
            "diluted_eps": {"current": {"value": 2, "period_end": "2025-12-31"}},
        }
    }
    manifest = {"filings": {"10-k": {"accession_number": "acc-current", "reporting_period": "2025-12-31"}}}
    check = crosscheck_with_sec(statement_payload(), facts, manifest)
    assert check["status"] == "approved"
    payload = statement_payload()
    payload["financials"]["income_statements"][0]["revenue"] = 201
    assert crosscheck_with_sec(payload, facts, manifest)["status"] == "failed"


def test_insight_rejects_vendor_faskills_metric_until_all_inputs_are_sec_derived(tmp_path: Path) -> None:
    (tmp_path / "10-k.txt").write_text("Revenue and cash-flow evidence.\n", encoding="utf-8")
    (tmp_path / "calculations.json").write_text('{"calculations": {}}\n', encoding="utf-8")
    sidecar = {
        "sec_crosscheck": {"status": "approved"},
        "course_boundary": {"report_use_allowed": True},
        "source_periods": {"current_period": "2025-12-31", "current_accession": "acc-current"},
        "metrics": {
            "piotroski_f_score": {
                "validation_status": "available", "value": 7,
                "formula": "Sum of nine binary signals", "inputs": {},
            }
        },
    }
    (tmp_path / "faskills_metrics.json").write_text(json.dumps(sidecar), encoding="utf-8")
    report = "Insight: The Piotroski F-Score was 7 (faskills_metrics.json:piotroski_f_score), supported by the filing evidence. (10-k.txt:1)"
    marks = verify_insight_claims(tmp_path, report)
    assert marks[0].mark == "Unsupported"
    report_without_filing = "Insight: The Piotroski F-Score was 7 (faskills_metrics.json:piotroski_f_score)."
    assert verify_insight_claims(tmp_path, report_without_filing)[0].mark == "Unsupported"

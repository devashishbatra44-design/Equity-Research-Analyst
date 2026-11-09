from __future__ import annotations

import json
import shutil
from pathlib import Path

import equity_research_crewai.main as main


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CLEAN_RUN = REPOSITORY_ROOT / "week02" / "runs" / "COSTCO_WHOLESALE_CORP_NEW_COST_20261102_234708"


def test_full_flow_has_fixed_order_and_required_verifier(monkeypatch, tmp_path: Path) -> None:
    run = tmp_path / "flow_run"
    shutil.copytree(CLEAN_RUN, run)
    saved_outputs = json.loads((run / "role_outputs.json").read_text(encoding="utf-8"))

    def fake_call_role(role: str, handoff: str) -> str:
        if role in saved_outputs:
            return saved_outputs[role]
        if role == "Strategy Manager":
            return json.dumps({"status": "pass", "issues": [], "sections_to_retry": []})
        if role == "Verifier":
            return json.dumps({"assessments": []})
        raise AssertionError(role)

    monkeypatch.setattr(main, "call_role", fake_call_role)
    monkeypatch.setattr(main, "create_week03_run", lambda source: run)
    monkeypatch.setattr(main, "lab05_personas_ready", lambda: False)
    flow = main.EquityResearchTeamFlow()
    flow.kickoff(
        inputs={
            "ticker": "COST",
            "peers": ["WMT", "TGT", "BJ"],
            "saved_run": str(run),
        }
    )
    assert flow.state.node_order == [
        "Steps",
        "Research Analyst",
        "Financial Analyst",
        "Investment Advisor",
        "Strategy Manager",
        "Verifier",
    ]
    assert Path(flow.state.verified_report_path).exists()


def test_cli_has_no_verifier_disable_flag() -> None:
    destinations = {action.dest for action in main.build_parser()._actions}
    assert "verify_only" in destinations
    assert not any("disable" in name or "skip" in name for name in destinations)


def test_report_section_keeps_lower_level_subheadings() -> None:
    output = "## Valuation Insights\n\n### Revenue\nText\n\n## Investment Recommendation\nHold"
    section = main.desk_app.extract_markdown_section(output, "Valuation Insights")
    assert section is not None
    assert "### Revenue" in section
    assert "Investment Recommendation" not in section


def test_insight_check_requires_last_line_and_rejects_release_first_paragraph(tmp_path: Path) -> None:
    release = tmp_path / "exhibit-99-1.txt"
    release.write_text(
        "Header\nCompany today announced its quarterly results for the period.\nA later supported claim.\n",
        encoding="utf-8",
    )
    outputs = {
        "Research Analyst": "Section\n\nInsight: A later supported claim. (exhibit-99-1.txt:3)",
        "Financial Analyst": "Section\n\nInsight: Quarterly results. (exhibit-99-1.txt:2)",
        "Investment Advisor": "Section without an insight",
    }
    issues = main.insight_issues(outputs, tmp_path)
    assert {issue["role"] for issue in issues} == {"Financial Analyst", "Investment Advisor"}


def test_three_lab05_personas_have_all_six_required_parts() -> None:
    assert main.lab05_personas_ready()


def test_report_assembly_does_not_duplicate_financial_section() -> None:
    research = (
        "# Overview\nOne\n\n"
        "# Market Positioning and Growth Outlook\nTwo\n\n"
        "# Future Developments and Strategic Recommendations\nThree\n\n"
        "Insight: Research insight. (10-k.txt:1)"
    )
    financial = "## Valuation Insights\nFour\n\nInsight: Financial insight. (10-k.txt:2)"
    advisor = "# Investment Recommendation\nFive\n\nInsight: Advisor insight. (10-k.txt:3)"
    report, missing = main.desk_app.assemble_report(research, financial, advisor)
    assert missing == []
    assert report is not None
    assert report.count("Valuation Insights") == 1
    assert report.count("Insight:") == 3


def test_financial_source_notes_keep_existing_insight_as_final_line() -> None:
    state = main.TeamState(
        price=992.13,
        price_date="2026-10-27",
        price_source="Nasdaq",
    )
    context = main._context(CLEAN_RUN, state)
    output = (
        "## Valuation Insights\nBody\n\n"
        "**Annual XBRL source details**\nOld notes\n\n"
        "Insight: Supported fact. (10-k.txt:1044)"
    )
    result = main._attach_quantitative_source_notes(output, context)
    assert result.splitlines()[-1].startswith("Insight:")
    assert "(calculations.json:price_to_earnings)" in result


def test_replay_saves_deterministic_quarter_revenue_growth(tmp_path: Path) -> None:
    run = tmp_path / "quarter_growth"
    shutil.copytree(CLEAN_RUN, run)
    calculations_path = run / "calculations.json"
    calculations = json.loads(calculations_path.read_text(encoding="utf-8"))
    calculations["calculations"].pop("quarter_revenue_growth", None)
    calculations_path.write_text(json.dumps(calculations), encoding="utf-8")

    main._save_quarter_revenue_growth_calculation(run)

    saved = json.loads(calculations_path.read_text(encoding="utf-8"))["calculations"]["quarter_revenue_growth"]
    assert saved["validation_status"] == "available"
    assert saved["result"] == 0.111043
    assert saved["inputs"] == {
        "current_quarter_revenue_thousands": 95723,
        "prior_year_same_quarter_revenue_thousands": 86156,
    }

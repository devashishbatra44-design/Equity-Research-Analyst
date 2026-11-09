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
    monkeypatch.setattr(main, "_number_issues", lambda run_folder, output: [])
    monkeypatch.setattr(main, "verify_core_claims", lambda run_folder, report: [])
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


def test_course_run_command_accepts_optional_price_provenance_and_no_price() -> None:
    parser = main.build_parser()
    with_price = parser.parse_args(["COST", "--peers", "WMT,TGT,BJ", "--price", "992.13"])
    without_price = parser.parse_args(["COST", "--peers", "WMT,TGT,BJ"])
    assert with_price.price == 992.13
    assert with_price.price_date == ""
    assert with_price.price_source == ""
    assert without_price.price is None


def test_verify_only_survives_model_failure_and_writes_new_artifact(monkeypatch, tmp_path: Path) -> None:
    run = tmp_path / "verify_only"
    shutil.copytree(CLEAN_RUN, run)
    (run / "verified_report.md").write_text("sentinel original\n", encoding="utf-8")
    original = (run / "verified_report.md").read_text(encoding="utf-8")

    def unavailable(_: str) -> str:
        raise RuntimeError("model unavailable")

    monkeypatch.setattr(main, "_semantic_check", unavailable)
    output = main.verify_only(run)
    assert output.name.startswith("verified_report_rerun_")
    assert output.exists()
    rendered = output.read_text(encoding="utf-8").lower()
    assert "optional model definition review was not run" in rendered
    assert "checkpoint 2 evidence" in rendered
    assert (run / "verified_report.md").read_text(encoding="utf-8") == original


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
    assert "**Annual XBRL source details**" not in result


def test_insight_normalization_removes_narrative_year_but_preserves_citation_line() -> None:
    output = "Insight: In 2026, the filing line supports the claim. (10-k.txt:2025)"
    normalized = main._normalize_insight_prefix(output)
    assert "In 2026" not in normalized
    assert "10-k.txt:2025" in normalized


def test_advisor_normalization_removes_blocked_vendor_citation() -> None:
    output = (
        "# Investment Recommendation\nHold. "
        "Valuation support is limited (faskills_metrics.json:dupont_5_factor).\n\n"
        "Insight: Margin was 3.8%. (calculations.json:operating_margin)"
    )
    normalized = main._normalize_advisor_output(output)
    assert "faskills_metrics.json" not in normalized
    assert "calculations.json:operating_margin" in normalized


def test_required_claim_block_names_net_sales_peer_definition() -> None:
    state = main.TeamState(price=992.13, price_date="2026-10-27", price_source="Nasdaq")
    context = main._context(CLEAN_RUN, state)
    block = main._render_required_course_claims(context)
    assert "TGT labels its issuer-reported top operating-revenue line `Net sales`" in block
    assert "peers.json:TGT:operating_margin" in block


def test_verifier_diagnostic_preserves_desk_output_byte_for_byte(tmp_path: Path) -> None:
    source = tmp_path / "saved_run"
    shutil.copytree(CLEAN_RUN, source)
    (source / "tavily_research.json").write_text("{}\n", encoding="utf-8")
    (source / "tavily_research.md").write_text("historical sidecar\n", encoding="utf-8")
    (source / "faskills_metrics.json").write_text(
        json.dumps({"course_boundary": {"report_use_allowed": True}}) + "\n",
        encoding="utf-8",
    )
    manifest_path = source / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["output_filenames"] = list(manifest.get("output_filenames", [])) + [
        "tavily_research.json",
        "tavily_research.md",
        "faskills_metrics.json",
    ]
    manifest["faskills_extension"] = {"enabled": True}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    original_report = (source / "report.md").read_bytes()
    original_outputs = (source / "role_outputs.json").read_bytes()

    destination = main.reconcile_saved_run(source)

    assert (destination / "report.md").read_bytes() == original_report
    assert (destination / "role_outputs.json").read_bytes() == original_outputs
    assert (destination / "tavily_research.json").exists()
    assert (destination / "tavily_research.md").exists()
    saved_manifest = json.loads((destination / "manifest.json").read_text(encoding="utf-8"))
    diagnostic = saved_manifest["derived_verifier_diagnostic"]
    assert diagnostic["source_run"] == source.name
    assert diagnostic["report_and_role_outputs_unchanged"] is True
    metadata = json.loads((destination / "reconciliation.json").read_text(encoding="utf-8"))
    assert metadata["code_written_insights"] == 0


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

from __future__ import annotations

import json
from pathlib import Path

import equity_research_crewai.main as main
from equity_research_crewai.faskills_methodology import (
    DRIVER_STAGES,
    EXPERT_LENSES,
    build_methodology_plan,
    lens_coverage,
    methodology_context_for_role,
    record_driver_stage,
    render_methodology_report,
    save_methodology_plan,
)


def _run_folder(tmp_path: Path) -> Path:
    for name in ("10-k.txt", "10-q.txt", "8-k.txt", "exhibit-99-1.txt"):
        (tmp_path / name).write_text("Saved filing evidence.\n", encoding="utf-8")
    for name in ("facts.json", "calculations.json", "peers.json"):
        (tmp_path / name).write_text("{}\n", encoding="utf-8")
    sidecar = {
        "sec_crosscheck": {"status": "approved"},
        "course_boundary": {"report_use_allowed": True},
        "metrics": {
            "piotroski_f_score": {"validation_status": "available", "value": 7},
            "owner_earnings": {"validation_status": "available", "value": 100},
            "beneish_m_score": {"validation_status": "unavailable", "value": None},
        },
    }
    (tmp_path / "faskills_metrics.json").write_text(json.dumps(sidecar), encoding="utf-8")
    return tmp_path


def test_all_nine_lenses_are_routed_without_changing_course_roles(tmp_path: Path) -> None:
    plan = build_methodology_plan(_run_folder(tmp_path))
    assert set(plan["expert_lenses"]) == set(EXPERT_LENSES)
    assert len(plan["routing"]["Research Analyst"]) == 4
    assert len(plan["routing"]["Financial Analyst"]) == 5
    assert plan["course_boundaries"]["verifier_is_final_node"] is True
    assert plan["course_boundaries"]["automatic_price_targets_enabled"] is False
    assert plan["course_boundaries"]["confidence_weighted_signal_voting_enabled"] is False
    assert plan["data_inventory"]["thirteen_f_used"] is False
    assert plan["data_inventory"]["news_or_tavily_used"] is False


def test_methodology_records_tavily_as_supplementary_when_present(tmp_path: Path) -> None:
    run = _run_folder(tmp_path)
    (run / "tavily_research.json").write_text(
        json.dumps(
            {
                "provider": "Tavily Search API",
                "result_count": 1,
                "results": [{"url": "https://example.com", "content": "Qualitative context."}],
            }
        ),
        encoding="utf-8",
    )
    plan = build_methodology_plan(run)
    assert plan["data_inventory"]["news_or_tavily_used"] is True
    assert plan["data_inventory"]["tavily_result_count"] == 1
    assert plan["course_boundaries"]["tavily_is_supplementary_context_only"] is True


def test_role_context_contains_only_its_assigned_lenses(tmp_path: Path) -> None:
    plan = build_methodology_plan(_run_folder(tmp_path))
    research = methodology_context_for_role(plan, "Research Analyst")
    financial = methodology_context_for_role(plan, "Financial Analyst")
    assert set(research["required_lenses"]) == {
        "warren_buffett",
        "peter_lynch",
        "cathie_wood",
        "george_soros",
    }
    assert set(financial["required_lenses"]) == {
        "ben_graham",
        "ray_dalio",
        "michael_burry",
        "jim_simons",
        "robert_shiller",
    }
    assert "price target" in research["required_lenses"]["cathie_wood"]["rules"][-1]


def test_driver_trace_and_dual_outputs_are_saved(tmp_path: Path) -> None:
    run = _run_folder(tmp_path)
    save_methodology_plan(run)
    for stage in DRIVER_STAGES:
        record_driver_stage(run, stage, f"{stage} action")
    outputs = {
        "Research Analyst": "Buffett lens\nLynch lens\nWood lens\nSoros lens",
        "Financial Analyst": "Graham lens\nDalio lens\nBurry lens\nSimons lens\nShiller lens",
    }
    markdown = render_methodology_report(run, outputs)
    trace = json.loads((run / "faskills_driver_trace.json").read_text(encoding="utf-8"))
    assert [record["stage"] for record in trace["records"]] == list(DRIVER_STAGES)
    assert markdown.exists()
    assert "All nine lenses visible: `true`" in markdown.read_text(encoding="utf-8")


def test_lens_coverage_reports_missing_labels(tmp_path: Path) -> None:
    plan = build_methodology_plan(_run_folder(tmp_path))
    result = lens_coverage(
        {
            "Research Analyst": "Buffett lens; Lynch lens; Wood lens; Soros lens",
            "Financial Analyst": "Graham lens; Dalio lens; Burry lens; Simons lens",
        },
        plan,
    )
    assert result["all_nine_complete"] is False
    assert result["Financial Analyst"]["missing"] == ["Shiller lens"]


def test_role_handoffs_receive_all_assigned_lenses(tmp_path: Path) -> None:
    plan = build_methodology_plan(_run_folder(tmp_path))
    research_handoff = json.loads(
        main._research_handoff(
            {
                "business_and_mda_source_text": {},
                "company": {},
                "earnings_release_source_text": {},
                "filings": {},
                "faskills_methodology": plan,
            }
        )
    )
    financial_handoff = json.loads(
        main._financial_handoff(
            {
                "company": {},
                "filings": {},
                "annual_facts": {},
                "calculations": {},
                "quarterly_release_claims": {},
                "quarter_period_end": "",
                "earnings_release_period_heading": "",
                "price_provenance": {},
                "release_income_statement_lines": {},
                "annual_statement_source_lines": {},
                "peers": {},
                "faskills_metrics": {},
                "faskills_methodology": plan,
            }
        )
    )
    assert len(research_handoff["context"]["faskills_methodology_lenses"]["required_lenses"]) == 4
    assert len(financial_handoff["context"]["faskills_methodology_lenses"]["required_lenses"]) == 5

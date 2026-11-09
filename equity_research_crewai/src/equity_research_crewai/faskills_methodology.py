"""Course-safe DRIVER and expert-lens orchestration for FAskills.

This module adapts the methodology in CinderZhang/FAskills v2.0.0.
It keeps the FIN 67110 graph, source boundaries, and mandatory Verifier.
The named investor frameworks are analytical lenses. They are not simulated
opinions, holdings claims, endorsements, or statements by those investors.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


METHODOLOGY_SOURCE = "CinderZhang/FAskills financial-researcher v2.0.0"
METHODOLOGY_VERSION = "2.0.0-course-adaptation"
DRIVER_STAGES = (
    "DISCOVER",
    "PROCESS",
    "REPRESENT",
    "IMPLEMENT",
    "VALIDATE",
    "EVOLVE",
    "REFLECT",
)


EXPERT_LENSES: dict[str, dict[str, Any]] = {
    "warren_buffett": {
        "display_name": "Warren Buffett",
        "label": "Buffett lens",
        "course_role": "Research Analyst",
        "focus": "Moat durability, understandable economics, capital allocation, and owner earnings.",
        "criteria": [
            "Explain how the company makes money and what could weaken that model.",
            "Test each claimed moat against filing evidence.",
            "Assess management actions through documented capital allocation.",
            "Use owner earnings and cash conversion only when the code supplied them.",
        ],
        "metric_candidates": ["owner_earnings", "fcf_conversion", "piotroski_f_score", "dupont_5_factor"],
    },
    "ben_graham": {
        "display_name": "Ben Graham",
        "label": "Graham lens",
        "course_role": "Financial Analyst",
        "focus": "Financial condition, earnings stability, valuation discipline, and margin of safety.",
        "criteria": [
            "Test liquidity, leverage, and earnings support before discussing valuation.",
            "Use only supplied valuation calculations and reported balance-sheet values.",
            "Treat an unavailable NCAV, EPV, or historical screen as unavailable.",
            "Separate current filing evidence from any forward assumption.",
        ],
        "metric_candidates": ["piotroski_f_score", "altman_z_manufacturing", "altman_z_nonmanufacturing"],
    },
    "peter_lynch": {
        "display_name": "Peter Lynch",
        "label": "Lynch lens",
        "course_role": "Research Analyst",
        "focus": "The business story, growth classification, earnings trajectory, and growth at a documented price.",
        "criteria": [
            "Explain the business in plain language from the filing.",
            "Classify growth only from the supplied historical periods.",
            "Use PEG only when both P/E and a supported growth input are supplied by code.",
            "Identify the measurable result that would show the growth story changed.",
        ],
        "metric_candidates": ["piotroski_f_score", "sustainable_growth_rate", "revenue_trend", "earnings_trend"],
    },
    "cathie_wood": {
        "display_name": "Cathie Wood",
        "label": "Wood lens",
        "course_role": "Research Analyst",
        "focus": "Documented disruption, innovation investment, adoption evidence, and technology risk.",
        "criteria": [
            "Identify innovation claims only when the supplied filing states them.",
            "Distinguish a documented operating KPI from an unsupported TAM forecast.",
            "Do not create Wright's Law inputs, a five-year model, or a price target.",
            "Name the filing result that would confirm or weaken the disruption thesis.",
        ],
        "metric_candidates": ["gross_profitability", "sustainable_growth_rate", "revenue_trend"],
    },
    "george_soros": {
        "display_name": "George Soros",
        "label": "Soros lens",
        "course_role": "Research Analyst",
        "focus": "Source-supported feedback loops, narrative-to-fundamental gaps, and reversal conditions.",
        "criteria": [
            "Describe a feedback loop only when both sides follow from supplied evidence.",
            "Do not infer market sentiment, macro conditions, or a boom-bust stage without supplied data.",
            "Separate a management narrative from the reported operating result.",
            "Name the next reported result that would reverse the conclusion.",
        ],
        "metric_candidates": ["revenue_trend", "earnings_trend"],
    },
    "ray_dalio": {
        "display_name": "Ray Dalio",
        "label": "Dalio lens",
        "course_role": "Financial Analyst",
        "focus": "Balance-sheet resilience, leverage, cash generation, and explicit stress conditions.",
        "criteria": [
            "Assess resilience from supplied leverage, cash-flow, and profitability evidence.",
            "Do not claim a macro cycle phase without a supplied macro dataset.",
            "State a stress scenario as a condition, not as a forecast.",
            "Use the industry-appropriate Altman model only when the classification is known.",
        ],
        "metric_candidates": ["altman_z_manufacturing", "altman_z_nonmanufacturing", "piotroski_f_score", "fcf_conversion", "dupont_5_factor"],
    },
    "michael_burry": {
        "display_name": "Michael Burry",
        "label": "Burry lens",
        "course_role": "Financial Analyst",
        "focus": "Revenue quality, earnings quality, accounting forensics, and the evidence-based bear case.",
        "criteria": [
            "Compare reported earnings with operating cash flow and accruals.",
            "Treat the Beneish score as a screening signal, not proof of manipulation.",
            "Do not claim a hidden liability or accounting problem without the supplied filing line.",
            "State the strongest filing-supported condition that could break the thesis.",
        ],
        "metric_candidates": ["beneish_m_score", "sloan_accrual_ratio", "owner_earnings", "fcf_conversion", "piotroski_f_score"],
    },
    "jim_simons": {
        "display_name": "Jim Simons",
        "label": "Simons lens",
        "course_role": "Financial Analyst",
        "focus": "Deterministic measurements, factor definitions, data sufficiency, and model risk.",
        "criteria": [
            "Use only code-produced statistics and their stated sample windows.",
            "Do not invent a probability, p-value, z-score, volatility regime, or position size.",
            "Mark price-series analyses unavailable when the required history is absent.",
            "Identify the largest measurement limitation in the supplied data.",
        ],
        "metric_candidates": ["piotroski_f_score", "dupont_5_factor", "sloan_accrual_ratio", "gross_profitability"],
    },
    "robert_shiller": {
        "display_name": "Robert Shiller",
        "label": "Shiller lens",
        "course_role": "Financial Analyst",
        "focus": "Long-horizon valuation, narrative risk, mean-reversion limits, and historical-data sufficiency.",
        "criteria": [
            "Use CAPE only when ten years of inflation-adjusted earnings are supplied by code.",
            "Do not invent a bubble probability or historical analogue.",
            "Use the documented P/E basis when CAPE is unavailable.",
            "Separate business quality from the price paid for that quality.",
        ],
        "metric_candidates": ["price_to_earnings", "revenue_trend", "earnings_trend"],
    },
}


COURSE_BOUNDARIES = {
    "three_course_personas_preserved": True,
    "strategy_manager_remains_checklist": True,
    "verifier_is_final_node": True,
    "named_frameworks_are_lenses_not_investor_opinions": True,
    "automatic_price_targets_enabled": False,
    "confidence_weighted_signal_voting_enabled": False,
    "simulated_holdings_intent_enabled": False,
    "unverified_web_claims_enabled": False,
    "tavily_is_supplementary_context_only": True,
    "missing_values_become_zero": False,
}


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _metric_catalog(run_folder: Path) -> tuple[dict[str, Any], bool]:
    sidecar = _load_json(run_folder / "faskills_metrics.json")
    allowed = (
        sidecar.get("sec_crosscheck", {}).get("status") == "approved"
        and sidecar.get("course_boundary", {}).get("report_use_allowed") is True
    )
    metrics = sidecar.get("metrics", {}) if allowed else {}
    return metrics if isinstance(metrics, dict) else {}, allowed


def build_methodology_plan(run_folder: Path) -> dict[str, Any]:
    """Build the auditable routing plan without making a model call."""
    metrics, report_use_allowed = _metric_catalog(run_folder)
    tavily = _load_json(run_folder / "tavily_research.json")
    tavily_used = tavily.get("provider") == "Tavily Search API" and bool(tavily.get("results"))
    filing_sources = {
        name: (run_folder / name).exists()
        for name in ("10-k.txt", "10-q.txt", "8-k.txt", "exhibit-99-1.txt", "facts.json", "calculations.json", "peers.json")
    }
    lenses: dict[str, Any] = {}
    for lens_id, definition in EXPERT_LENSES.items():
        available = [
            name
            for name in definition["metric_candidates"]
            if metrics.get(name, {}).get("validation_status") == "available"
        ]
        unavailable = [name for name in definition["metric_candidates"] if name not in available]
        lenses[lens_id] = {
            **definition,
            "status": "active_with_metrics" if available else "active_source_limited",
            "available_metrics": available,
            "unavailable_metrics": unavailable,
            "rules": [
                "Apply this framework independently before the course role synthesizes it.",
                "Use only the JSON hand-off and its exact source tokens.",
                "Write unavailable when the required evidence is absent.",
                "Do not impersonate the named investor or claim that investor's current view.",
                "Do not generate a price target, confidence vote, holding, or trade instruction.",
            ],
        }
    return {
        "methodology_version": METHODOLOGY_VERSION,
        "adapted_from": METHODOLOGY_SOURCE,
        "generated_at": datetime.now().astimezone().isoformat(),
        "mode": "full_course_safe",
        "driver_stages": list(DRIVER_STAGES),
        "course_boundaries": COURSE_BOUNDARIES,
        "data_inventory": {
            "filing_sources": filing_sources,
            "faskills_sec_crosscheck_approved": report_use_allowed,
            "available_deterministic_metrics": sorted(
                name for name, metric in metrics.items() if metric.get("validation_status") == "available"
            ),
            "licensed_raw_vendor_response_committed": False,
            "news_or_tavily_used": tavily_used,
            "tavily_result_count": tavily.get("result_count", 0) if tavily_used else 0,
            "tavily_supplementary_only": True,
            "thirteen_f_used": False,
        },
        "expert_lenses": lenses,
        "routing": {
            "Research Analyst": [lens_id for lens_id, item in lenses.items() if item["course_role"] == "Research Analyst"],
            "Financial Analyst": [lens_id for lens_id, item in lenses.items() if item["course_role"] == "Financial Analyst"],
            "Investment Advisor": ["Synthesize only the two source-bounded analyst outputs."],
            "Strategy Manager": ["Check the five report sections and lens coverage. Never add content."],
            "Verifier": ["Check every numeric claim against saved evidence. Remain the final node."],
        },
    }


def save_methodology_plan(run_folder: Path) -> Path:
    path = run_folder / "faskills_methodology.json"
    path.write_text(json.dumps(build_methodology_plan(run_folder), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def methodology_context_for_role(plan: dict[str, Any], role: str) -> dict[str, Any]:
    """Return only the independent lenses assigned to one course role."""
    lens_ids = plan.get("routing", {}).get(role, [])
    lenses = plan.get("expert_lenses", {})
    selected = {lens_id: lenses[lens_id] for lens_id in lens_ids if lens_id in lenses}
    return {
        "methodology": "DRIVER with independent FAskills analytical lenses",
        "role": role,
        "course_boundaries": plan.get("course_boundaries", {}),
        "required_lenses": selected,
        "output_rule": (
            "Apply every assigned lens independently. Add one concise labeled finding for every lens inside the role's existing report sections. "
            "A finding may say unavailable. Do not add a sixth report section."
        ),
    }


def record_driver_stage(
    run_folder: Path,
    stage: str,
    action: str,
    *,
    status: str = "complete",
    details: dict[str, Any] | None = None,
) -> Path:
    if stage not in DRIVER_STAGES:
        raise ValueError(f"Unknown DRIVER stage: {stage}")
    path = run_folder / "faskills_driver_trace.json"
    trace = _load_json(path)
    if not trace:
        trace = {
            "methodology_version": METHODOLOGY_VERSION,
            "adapted_from": METHODOLOGY_SOURCE,
            "records": [],
        }
    trace["records"].append(
        {
            "stage": stage,
            "action": action,
            "status": status,
            "recorded_at": datetime.now().astimezone().isoformat(),
            "details": details or {},
        }
    )
    path.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def lens_coverage(outputs: dict[str, str], plan: dict[str, Any]) -> dict[str, Any]:
    """Check whether each assigned lens label is visible in its course-role output."""
    findings: dict[str, Any] = {}
    for role in ("Research Analyst", "Financial Analyst"):
        text = outputs.get(role, "").lower()
        required_ids = plan.get("routing", {}).get(role, [])
        covered: list[str] = []
        missing: list[str] = []
        for lens_id in required_ids:
            label = str(plan.get("expert_lenses", {}).get(lens_id, {}).get("label", lens_id))
            (covered if label.lower() in text else missing).append(label)
        findings[role] = {"covered": covered, "missing": missing, "complete": not missing}
    findings["all_nine_complete"] = all(item["complete"] for item in findings.values() if isinstance(item, dict))
    return findings


def render_methodology_report(run_folder: Path, outputs: dict[str, str] | None = None) -> Path:
    """Save the human-readable methodology trace beside the JSON artifacts."""
    plan = _load_json(run_folder / "faskills_methodology.json")
    trace = _load_json(run_folder / "faskills_driver_trace.json")
    coverage = lens_coverage(outputs or {}, plan) if outputs is not None else {}
    lines = [
        "# FAskills methodology record",
        "",
        f"Source methodology: {plan.get('adapted_from', METHODOLOGY_SOURCE)}.",
        "",
        "The nine named frameworks are analytical lenses. They are not statements or recommendations by those investors.",
        "The three FIN 67110 personas, five report sections, Strategy Manager, and final Verifier remain unchanged.",
        "",
        "## DRIVER trace",
        "",
        "| Stage | Action | Status |",
        "|---|---|---|",
    ]
    for record in trace.get("records", []):
        lines.append(f"| {record.get('stage')} | {record.get('action')} | {record.get('status')} |")
    lines.extend(["", "## Expert-lens routing", "", "| Lens | Course role | Status | Available metrics |", "|---|---|---|---|"])
    for lens in plan.get("expert_lenses", {}).values():
        metrics = ", ".join(lens.get("available_metrics", [])) or "None; source-limited review only"
        lines.append(f"| {lens.get('label')} | {lens.get('course_role')} | {lens.get('status')} | {metrics} |")
    if coverage:
        lines.extend(["", "## Generated-output coverage", ""])
        for role in ("Research Analyst", "Financial Analyst"):
            item = coverage.get(role, {})
            missing = ", ".join(item.get("missing", [])) or "None"
            lines.append(f"- {role}: complete = `{str(item.get('complete', False)).lower()}`; missing labels = {missing}.")
        lines.append(f"- All nine lenses visible: `{str(coverage.get('all_nine_complete', False)).lower()}`.")
    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- Missing evidence remains unavailable.",
            "- The program does not create automatic price targets.",
            "- The program does not simulate investor holdings or intent.",
            "- The program does not use confidence-weighted voting.",
            "- Tavily results are supplementary web context. SEC filings remain authoritative for audited financial claims.",
            "- The mandatory Verifier remains the final graph node.",
            "",
            "This is a learning exercise, not financial advice.",
            "",
            "AI assistance: OpenAI Codex adapted the professor's FAskills methodology to the course graph. I verified the sources myself; the judgments are mine.",
            "",
            "Any remaining errors are my own.",
        ]
    )
    path = run_folder / "faskills_methodology.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path

"""Fixed-order CrewAI Flow for the FIN 67110 equity-research agent team."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task
from crewai.flow import Flow, listen, start
from dotenv import load_dotenv
from pydantic import BaseModel, Field


PACKAGE_ROOT = Path(__file__).resolve().parent
CREWAI_PROJECT_ROOT = PACKAGE_ROOT.parents[1]
REPOSITORY_ROOT = PACKAGE_ROOT.parents[2]
WEEK02_ROOT = REPOSITORY_ROOT / "week02"
WEEK03_RUNS_ROOT = REPOSITORY_ROOT / "week03" / "runs"
ROLES_ROOT = PACKAGE_ROOT / "roles"
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from week02 import desk_app  # noqa: E402
from week02.desk_steps import RUNS_ROOT, parse_peers, safe_folder_component  # noqa: E402

from equity_research_crewai.verifier import (  # noqa: E402
    _quarter_eps,
    _release_quarter_revenues,
    verify_all_other_numbers,
    verify_core_claims,
    verify_insight_claims,
    verify_saved_run,
)
from equity_research_crewai.faskills_extension import enrich_run_folder  # noqa: E402
from equity_research_crewai.faskills_methodology import (  # noqa: E402
    lens_coverage,
    methodology_context_for_role,
    record_driver_stage,
    render_methodology_report,
    save_methodology_plan,
)
from equity_research_crewai.tavily_research import research_run_folder  # noqa: E402


ROLE_FILES = {
    "Research Analyst": "research_analyst.md",
    "Financial Analyst": "financial_analyst.md",
    "Investment Advisor": "investment_advisor.md",
    "Strategy Manager": "strategy_manager.md",
    "Verifier": "verifier.md",
}

PERSONA_HEADINGS = (
    "Identity",
    "How I read a company",
    "What I am given",
    "Criteria I score",
    "What would change my view",
    "Output",
)
ANALYST_ROLES = ("Research Analyst", "Financial Analyst", "Investment Advisor")


class TeamState(BaseModel):
    ticker: str = ""
    peers: list[str] = Field(default_factory=list)
    price: float | None = None
    price_date: str = ""
    price_source: str = ""
    saved_run: str = ""
    faskills: bool = False
    tavily: bool = False
    tavily_depth: str = "advanced"
    reuse_tavily: bool = False
    run_folder: str = ""
    node_order: list[str] = Field(default_factory=list)
    node_records: dict[str, list[dict[str, Any]]] = Field(default_factory=dict)
    research_output: str = ""
    financial_output: str = ""
    advisor_output: str = ""
    manager_output: str = ""
    report: str = ""
    verified_report_path: str = ""


def load_model_config() -> tuple[str, str, str]:
    load_dotenv(REPOSITORY_ROOT / ".env", override=False)
    api_key = (os.getenv("API_KEY") or os.getenv("GENAI_API_KEY") or "").strip()
    base_url = os.getenv("GENAI_BASE_URL", "").strip()
    model = os.getenv("GENAI_MODEL", "").strip()
    missing = [
        name
        for name, value in (
            ("API_KEY or GENAI_API_KEY", api_key),
            ("GENAI_BASE_URL", base_url),
            ("GENAI_MODEL", model),
        )
        if not value
    ]
    if missing:
        raise RuntimeError("Missing model configuration in .env: " + ", ".join(missing))
    return api_key, base_url, model


def load_role_instruction(role: str) -> str:
    path = ROLES_ROOT / ROLE_FILES[role]
    if not path.exists():
        raise FileNotFoundError(f"Missing role instruction file: {path}")
    return path.read_text(encoding="utf-8").strip()


def load_operating_rules() -> str:
    path = ROLES_ROOT / "operating_rules.md"
    if not path.exists():
        raise FileNotFoundError(f"Missing course operating-rules file: {path}")
    return path.read_text(encoding="utf-8").strip()


def lab05_personas_ready() -> bool:
    return all(
        all(heading.lower() in load_role_instruction(role).lower() for heading in PERSONA_HEADINGS)
        for role in ANALYST_ROLES
    )


def _last_nonblank_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _release_first_paragraph_line(run_folder: Path) -> tuple[int | None, str]:
    path = run_folder / "exhibit-99-1.txt"
    if not path.exists():
        return None, ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    for index, line in enumerate(lines, start=1):
        clean = line.strip()
        if len(clean) >= 40 and re.search(r"\b(?:announced|reports?|reported)\b", clean, flags=re.IGNORECASE):
            return index, clean
    return None, ""


def insight_issues(outputs: dict[str, str], run_folder: Path) -> list[dict[str, str]]:
    first_line_number, first_paragraph = _release_first_paragraph_line(run_folder)
    issues: list[dict[str, str]] = []
    citation_pattern = re.compile(
        r"(10-k\.txt|10-q\.txt|8-k\.txt|exhibit-99-1\.txt):\s*(\d+)(?:-(\d+))?",
        flags=re.IGNORECASE,
    )
    for role in ANALYST_ROLES:
        line = _last_nonblank_line(outputs.get(role, ""))
        if not line.startswith("Insight:"):
            issues.append({"role": role, "reason": "The role output does not end with a line that begins Insight:."})
            continue
        citations = citation_pattern.findall(line)
        if not citations:
            issues.append({"role": role, "reason": "The Insight line has no filing and line citation."})
            continue
        if re.search(r"\b\d[\d,.]*\s+basis\s+points?\b", line, flags=re.IGNORECASE) and not re.search(
            r"calculations\.json:\s*[a-z_]+", line, flags=re.IGNORECASE
        ):
            issues.append(
                {
                    "role": role,
                    "reason": "A derived basis-point gap must cite a supplied calculations.json result; a model role may not calculate it.",
                }
            )
            continue
        insight_without_citations = citation_pattern.sub("", line)
        insight_without_citations = re.sub(r"calculations\.json:\s*[a-z_]+", "", insight_without_citations, flags=re.IGNORECASE)
        insight_numbers = [
            number
            for number in re.findall(r"(?<![A-Za-z])(-?\d[\d,]*(?:\.\d+)?)", insight_without_citations)
        ]
        headline_numbers = [
            float(number.replace(",", ""))
            for number in re.findall(r"(?<![A-Za-z])(-?\d[\d,]*(?:\.\d+)?)", first_paragraph)
        ]
        if insight_numbers and headline_numbers and all(
            any(math.isclose(float(number.replace(",", "")), source, abs_tol=0.005) for source in headline_numbers)
            for number in insight_numbers
        ):
            issues.append(
                {
                    "role": role,
                    "reason": "Every number in the Insight also appears in the earnings release's first paragraph, so it restates the headline.",
                }
            )
            continue
        if first_line_number is not None and citations and all(
            filename.lower() == "exhibit-99-1.txt" and int(line_start) == first_line_number
            for filename, line_start, _ in citations
        ):
            issues.append(
                {
                    "role": role,
                    "reason": (
                        "The Insight line cites only the earnings release's first paragraph, so it only restates the headline. "
                        f"First paragraph: {first_paragraph}"
                    ),
                }
            )
            continue
        verification = verify_insight_claims(run_folder, line)
        if not verification or verification[0].mark != "Correct":
            mark = verification[0] if verification else None
            issues.append(
                {
                    "role": role,
                    "reason": (
                        f"The Insight line failed source verification: {mark.mark}; {mark.evidence}"
                        if mark
                        else "The Insight line could not be verified."
                    ),
                }
            )
    seen_signatures: list[tuple[str, tuple[tuple[str, str], ...]]] = []
    numeric_citation_pattern = re.compile(
        r"(-?\d[\d,]*(?:\.\d+)?\s*(?:%|x|basis\s+points?)?)\s*"
        r"\(((?:(?:10-k|10-q|8-k|exhibit-99-1)\.txt:\d+(?:-\d+)?|"
        r"calculations\.json:[a-z_]+|facts\.json:[a-z_]+))\)",
        flags=re.IGNORECASE,
    )
    for role in ANALYST_ROLES:
        line = _last_nonblank_line(outputs.get(role, ""))
        if not line.startswith("Insight:"):
            continue
        ordered_pairs: list[tuple[str, str]] = []
        for number, citation in numeric_citation_pattern.findall(line):
            pair = (
                re.sub(r"\s+", " ", number.lower().replace(",", "")).strip(),
                citation.lower(),
            )
            if pair not in ordered_pairs:
                ordered_pairs.append(pair)
        signature = tuple(ordered_pairs)
        if not signature:
            continue
        duplicate_role = ""
        current_pairs = set(signature)
        for prior_role, prior_signature in seen_signatures:
            prior_pairs = set(prior_signature)
            shared_pairs = current_pairs & prior_pairs
            if (
                signature == prior_signature
                or (signature and prior_signature and signature[0] == prior_signature[0])
                or len(shared_pairs) >= 2
            ):
                duplicate_role = prior_role
                break
        if duplicate_role:
            issues.append(
                {
                    "role": role,
                    "reason": (
                        f"The Insight repeats the same sourced numerical claim as the {duplicate_role}. "
                        "Each analyst role must contribute a distinct Insight."
                    ),
                }
            )
        else:
            seen_signatures.append((role, signature))
    return issues


def _model_derived_growth_issues(
    role: str,
    output: str,
    run_folder: Path,
) -> list[dict[str, str]]:
    """Reject model-derived growth rates that are not supplied by code or stated by a filing."""
    filing_citation = re.compile(
        r"(-?\d[\d,]*(?:\.\d+)?)%\s*\(((10-k|10-q|8-k|exhibit-99-1)\.txt):(\d+)(?:-(\d+))?\)",
        flags=re.IGNORECASE,
    )
    growth_language = re.compile(
        r"\b(?:growth|grew|increase[ds]?|decrease[ds]?|decline[ds]?|rose|fell|up|down|yoy|year.over.year)\b",
        flags=re.IGNORECASE,
    )
    issues: list[dict[str, str]] = []
    for line_number, line in enumerate(output.splitlines(), start=1):
        if not growth_language.search(line):
            continue
        for match in filing_citation.finditer(line):
            reported = float(match.group(1).replace(",", ""))
            filename = match.group(2).lower()
            start = int(match.group(4))
            end = int(match.group(5) or start)
            path = run_folder / filename
            cited_text = ""
            if path.exists():
                source_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
                cited_text = " ".join(source_lines[start - 1 : end])
            source_percentages = [
                float(value.replace(",", ""))
                for value in re.findall(r"(-?\d[\d,]*(?:\.\d+)?)\s*%", cited_text)
            ]
            if any(math.isclose(reported, source, abs_tol=0.005) for source in source_percentages):
                continue
            issues.append(
                {
                    "claim": f"{role} line {line_number}",
                    "report_said": match.group(0),
                    "mark": "Unsupported",
                    "reason": (
                        "The line states a growth rate that the cited filing line does not state. "
                        "A model role may use a derived growth rate only when supplied by calculations.json."
                    ),
                }
            )
    return issues


def _attach_quantitative_source_notes(financial_output: str, context: dict[str, Any]) -> str:
    """Insert the eleven code-built audit claims and keep the Insight last.

    The model owns the analysis and scoring. The harness owns the required
    facts and arithmetic. This prevents a retry from silently dropping or
    rewriting one of the course's eleven audit claims.
    """
    original_lines = financial_output.splitlines()
    original_insight_index = next(
        (
            index
            for index in range(len(original_lines) - 1, -1, -1)
            if original_lines[index].strip().startswith("Insight:")
        ),
        None,
    )
    original_insight = (
        original_lines[original_insight_index].strip()
        if original_insight_index is not None
        else ""
    )
    clean = desk_app.strip_quantitative_source_notes(financial_output)
    required_leads = (
        "annual total revenue was",
        "annual revenue growth was",
        "annual operating income was",
        "annual operating margin was",
        "annual net income attributable to the company was",
        "annual net income was",
        "annual gaap diluted eps was",
        "return on average equity was",
        "debt to equity was",
        "free cash flow was",
        "quarter total revenue was",
        "quarter revenue growth was",
        "quarter gaap diluted eps was",
    )
    lines = [
        line
        for line in clean.splitlines()
        if "required course claims — code-built audit block" not in line.strip().lower()
        and not any(lead in line.strip().lower() for lead in required_leads)
    ]
    insight_index = next(
        (index for index in range(len(lines) - 1, -1, -1) if lines[index].strip().startswith("Insight:")),
        None,
    )
    insight = lines.pop(insight_index).strip() if insight_index is not None else original_insight
    body = "\n".join(lines).rstrip()
    required_claims = _render_required_course_claims(context)
    result = body + "\n\n" + required_claims
    if insight:
        result += "\n\n" + insight
    return result.strip()


def _report_money(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.3f} billion"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.3f} million"
    return f"${value:,.2f}"


def _render_required_course_claims(context: dict[str, Any]) -> str:
    facts = context["annual_facts"]
    calculations = context["calculations"]
    run_folder = Path(context["run_folder"])
    saved_facts = desk_app.load_json(run_folder / "facts.json")
    quarter_revenue, _, _ = _release_quarter_revenues(run_folder, saved_facts)
    quarter_eps, _ = _quarter_eps(saved_facts)
    release_claims = context["quarterly_release_claims"]

    def fact_value(name: str) -> float:
        return float(facts[name]["current"]["value"])

    def calc_percent(name: str) -> float:
        return float(calculations[name]["result"]) * 100

    lines = [
        "### Required Course Claims — Code-Built Audit Block",
        "",
        f"Annual total revenue was {_report_money(fact_value('total_revenue'))} (facts.json:total_revenue).",
        f"Annual revenue growth was {calc_percent('revenue_growth'):.4f}% (calculations.json:revenue_growth).",
        f"Annual operating income was {_report_money(fact_value('operating_income'))} (facts.json:operating_income).",
        f"Annual operating margin was {calc_percent('operating_margin'):.4f}% (calculations.json:operating_margin).",
        f"Annual net income attributable to the company was {_report_money(fact_value('net_income'))} (facts.json:net_income).",
        f"Annual GAAP diluted EPS was ${fact_value('diluted_eps'):.2f} (facts.json:diluted_eps).",
        f"Return on average equity was {calc_percent('return_on_average_equity'):.4f}% (calculations.json:return_on_average_equity).",
    ]
    debt_to_equity = calculations.get("debt_to_equity", {})
    if debt_to_equity.get("validation_status") == "available" and debt_to_equity.get("result") is not None:
        lines.append(
            f"Debt to equity was {float(debt_to_equity['result']):.4f}x (calculations.json:debt_to_equity)."
        )
    else:
        lines.append("Debt to equity was not stated in the supplied filings because the required inputs were unavailable.")
    free_cash_flow = calculations["free_cash_flow"]
    lines.append(
        f"Free cash flow was {_report_money(float(free_cash_flow['result']))} (calculations.json:free_cash_flow)."
    )
    revenue_line = release_claims.get("total_revenue", {}).get("source_line_start")
    if quarter_revenue is not None and isinstance(revenue_line, int):
        lines.append(
            f"Quarter total revenue was {_report_money(quarter_revenue)} (exhibit-99-1.txt:{revenue_line})."
        )
    quarter_growth = calculations.get("quarter_revenue_growth", {})
    if quarter_growth.get("validation_status") == "available" and quarter_growth.get("result") is not None:
        lines.append(
            f"Quarter revenue growth was {float(quarter_growth['result']) * 100:.4f}% "
            "(calculations.json:quarter_revenue_growth)."
        )
    eps_line = release_claims.get("diluted_eps", {}).get("source_line_start")
    if quarter_eps is not None and isinstance(eps_line, int):
        lines.append(
            f"Quarter GAAP diluted EPS was ${quarter_eps:.2f} (exhibit-99-1.txt:{eps_line})."
        )
    for peer in context.get("peers", {}).get("peers", []):
        if (
            peer.get("status") == "success"
            and str(peer.get("revenue_line_label") or "").strip().lower() == "net sales"
        ):
            ticker = str(peer.get("ticker") or "peer").upper()
            lines.append(
                f"Peer denominator definition: {ticker} labels its issuer-reported top operating-revenue line "
                f"`Net sales`; the desk uses that line as the total operating-revenue denominator "
                f"(peers.json:{ticker}:operating_margin)."
            )
    return "\n".join(lines)


def _join_score_evidence_lines(output: str) -> str:
    """Keep a numerical persona score and its cited evidence on one line."""
    lines = output.splitlines()
    merged: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        next_line = lines[index + 1] if index + 1 < len(lines) else ""
        if re.search(r":\s*[1-5]\s*\*{0,2}\s*$", line.strip()) and (
            re.search(r"\bevidence\s*:", next_line, flags=re.IGNORECASE)
            or re.search(
                r"(?:10-k|10-q|8-k|exhibit-99-1)\.txt:\d+|(?:facts|calculations|peers|manifest)\.json:",
                next_line,
                flags=re.IGNORECASE,
            )
        ):
            evidence = re.sub(r"^\s*[-*]+\s*", "", next_line).strip()
            merged.append(line.rstrip() + " " + evidence)
            index += 2
            continue
        merged.append(line)
        index += 1
    return "\n".join(merged)


def _bind_financial_score_sources(output: str) -> str:
    """Attach deterministic evidence tokens to any otherwise bare score."""
    source_by_label = {
        "revenue-growth quality": "calculations.json:revenue_growth",
        "operating-margin direction": "calculations.json:operating_margin",
        "cash conversion": "calculations.json:free_cash_flow",
        "return on average equity": "calculations.json:return_on_average_equity",
        "debt capacity": "calculations.json:debt_to_equity",
        "financial flexibility": "calculations.json:free_cash_flow",
        "gaap diluted-eps quality": "facts.json:diluted_eps",
        "valuation support": "calculations.json:price_to_earnings",
        "peer-definition consistency": "calculations.json:operating_margin",
    }
    bound: list[str] = []
    for line in output.splitlines():
        lower = line.lower()
        if re.search(r":\s*[1-5]\s*\*{0,2}\s*$", line.strip()) and not any(
            pattern.search(line)
            for pattern in (
                re.compile(r"(?:10-k|10-q|8-k|exhibit-99-1)\.txt:\d+", flags=re.IGNORECASE),
                re.compile(r"(?:facts|calculations|peers|manifest)\.json:", flags=re.IGNORECASE),
            )
        ):
            source = next((token for label, token in source_by_label.items() if label in lower), "")
            if source:
                line = line.rstrip() + f" Evidence source: ({source})."
        bound.append(line)
    return "\n".join(bound)


def _normalize_analyst_output(role: str, output: str, context: dict[str, Any]) -> str:
    normalized = _normalize_insight_prefix(_join_score_evidence_lines(output))
    if role == "Financial Analyst":
        normalized = _attach_quantitative_source_notes(normalized, context)
        normalized = _bind_financial_score_sources(normalized)
    return normalized.strip()


def _normalize_insight_prefix(output: str) -> str:
    lines = output.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^(\s*)\*{0,2}Insight:\*{0,2}\s*(.*)$", line, flags=re.IGNORECASE)
        if match:
            insight_text = re.sub(r"\s{2,}", " ", match.group(2)).strip()
            lines[index] = f"{match.group(1)}Insight: {insight_text}".rstrip()
    return "\n".join(lines)


def _normalize_advisor_output(output: str) -> str:
    """Keep the Advisor within the two analyst outputs and remove blocked sidecar citations."""
    normalized = _normalize_insight_prefix(output)
    normalized = re.sub(
        r"\s*\((?:faskills_financialdatasets|faskills_metrics)\.json:[^)]+\)",
        "",
        normalized,
        flags=re.IGNORECASE,
    )
    return normalized.strip()


def make_llm() -> LLM:
    api_key, base_url, model = load_model_config()
    return LLM(
        model=model,
        provider="openai",
        api_key=api_key,
        base_url=base_url.rstrip("/") + "/",
        temperature=0.1,
        max_tokens=4000,
        timeout=120,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


def expected_output_from_handoff(handoff: str) -> str:
    payload = json.loads(handoff)
    expected = payload.get("expected_output") if isinstance(payload, dict) else None
    return expected if isinstance(expected, str) else json.dumps(expected, ensure_ascii=False)


def call_role(role: str, handoff: str) -> str:
    agent = Agent(
        role=role,
        goal="Complete only the source-bounded task in the supplied JSON hand-off.",
        backstory=load_role_instruction(role),
        llm=make_llm(),
        allow_delegation=False,
        max_iter=1,
        verbose=False,
    )
    task = Task(description=handoff, expected_output=expected_output_from_handoff(handoff), agent=agent)
    result = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
        memory=False,
    ).kickoff()
    output = (result.raw or "").strip()
    if not output:
        raise RuntimeError(f"The {role} returned no output.")
    return output


def run_role(
    role: str,
    instruction: str,
    handoff: str,
    model: str,
    temperature: float = 0.1,
) -> str:
    """Keep the Week 2 desk interface working while CrewAI owns the model call."""
    api_key, base_url, configured_model = load_model_config()
    llm = LLM(
        model=model or configured_model,
        provider="openai",
        api_key=api_key,
        base_url=base_url.rstrip("/") + "/",
        temperature=temperature,
        max_tokens=4000,
        timeout=120,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    agent = Agent(
        role=role,
        goal="Complete only the source-bounded task in the supplied JSON hand-off.",
        backstory=instruction,
        llm=llm,
        allow_delegation=False,
        max_iter=1,
        verbose=False,
    )
    task = Task(description=handoff, expected_output=expected_output_from_handoff(handoff), agent=agent)
    result = Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
        memory=False,
    ).kickoff()
    output = (result.raw or "").strip()
    if not output:
        raise RuntimeError(f"The {role} returned no output.")
    return output


def _save_node_record(state: TeamState, node: str, handoff: Any, output: Any) -> None:
    base_role = next((role for role in ROLE_FILES if node == role or node.startswith(role + " ")), None)
    provenance: dict[str, Any] = {}
    if base_role:
        role_path = ROLES_ROOT / ROLE_FILES[base_role]
        role_bytes = role_path.read_bytes()
        rules_path = ROLES_ROOT / "operating_rules.md"
        provenance = {
            "role": base_role,
            "role_file": str(role_path.relative_to(REPOSITORY_ROOT)),
            "role_file_sha256": hashlib.sha256(role_bytes).hexdigest(),
            "operating_rules_file": str(rules_path.relative_to(REPOSITORY_ROOT)),
            "operating_rules_sha256": hashlib.sha256(rules_path.read_bytes()).hexdigest(),
        }
    state.node_order.append(node)
    state.node_records.setdefault(node, []).append(
        {"input": handoff, "output": output, "instruction_provenance": provenance}
    )
    if state.run_folder:
        run_folder = Path(state.run_folder)
        (run_folder / "node_records.json").write_text(
            json.dumps(state.node_records, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (run_folder / "node_order.json").write_text(
            json.dumps(state.node_order, indent=2) + "\n",
            encoding="utf-8",
        )


def _print_node(name: str) -> None:
    print(f"Node: {name}", flush=True)


def create_week03_run(source: Path) -> Path:
    manifest = desk_app.load_json(source / "manifest.json")
    company = manifest.get("company", {})
    legal_name = safe_folder_component(str(company.get("legal_name") or "COMPANY"))
    ticker = safe_folder_component(str(company.get("ticker") or manifest.get("main_ticker") or "TICKER"))
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    destination = WEEK03_RUNS_ROOT / f"{legal_name}_{ticker}_{stamp}"
    suffix = 1
    while destination.exists():
        destination = WEEK03_RUNS_ROOT / f"{legal_name}_{ticker}_{stamp}_{suffix}"
        suffix += 1
    destination.mkdir(parents=True)
    data_files = {
        "10-k.txt",
        "10-q.txt",
        "8-k.txt",
        "exhibit-99-1.txt",
        "facts.json",
        "facts.csv",
        "calculations.json",
        "filings.json",
        "manifest.json",
        "peers.json",
        "peers.csv",
        "faskills_financialdatasets.json",
        "faskills_metrics.json",
        "faskills_methodology.json",
        "faskills_driver_trace.json",
        "faskills_methodology.md",
        "tavily_research.json",
        "tavily_research.md",
    }
    for filename in data_files:
        source_path = source / filename
        if source_path.exists():
            shutil.copy2(source_path, destination / filename)
    _save_quarter_revenue_growth_calculation(destination)
    _save_insight_calculations(destination)
    trace_path = destination / "faskills_driver_trace.json"
    if trace_path.exists():
        trace_path.write_text(
            json.dumps(
                {
                    "methodology_version": "2.0.0-course-adaptation",
                    "adapted_from": "CinderZhang/FAskills financial-researcher v2.0.0",
                    "records": [],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    copied_manifest_path = destination / "manifest.json"
    copied_manifest = desk_app.load_json(copied_manifest_path)
    copied_manifest["week03_parent_run"] = str(source.relative_to(REPOSITORY_ROOT) if source.is_relative_to(REPOSITORY_ROOT) else source)
    copied_manifest["week03_replay_time"] = datetime.now().astimezone().isoformat()
    copied_manifest["output_filenames"] = sorted(path.name for path in destination.iterdir() if path.is_file())
    copied_manifest_path.write_text(json.dumps(copied_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return destination


def _save_quarter_revenue_growth_calculation(run_folder: Path) -> None:
    """Persist the code-calculated quarter growth used by claim 10 and Lab 05 Insights."""
    calculations_path = run_folder / "calculations.json"
    if not calculations_path.exists():
        return
    calculations = desk_app.load_json(calculations_path)
    entries = calculations.setdefault("calculations", {})
    if entries.get("quarter_revenue_growth", {}).get("validation_status") == "available":
        return
    context = desk_app.read_run_context(run_folder)
    growth = context.get("quarterly_release_claims", {}).get("quarter_revenue_growth", {})
    result_percent = growth.get("result_percent")
    if not isinstance(result_percent, (int, float)):
        return
    current_revenue = growth.get("current_quarter_revenue_thousands")
    prior_revenue = growth.get("prior_year_same_quarter_revenue_thousands")
    calculations["calculations"]["quarter_revenue_growth"] = {
        "measure": "Quarter revenue growth versus the same quarter last year",
        "formula": "(Current-quarter revenue - Same-quarter prior-year revenue) / Same-quarter prior-year revenue",
        "inputs": {
            "current_quarter_revenue_thousands": current_revenue,
            "prior_year_same_quarter_revenue_thousands": prior_revenue,
        },
        "fiscal_periods": {"current_quarter_end": context.get("quarter_period_end")},
        "unit": "ratio",
        "arithmetic": growth.get("formula"),
        "result": float(result_percent) / 100,
        "validation_status": "available",
        "unavailable_reason": None,
        "note": growth.get("source_line"),
    }
    calculations_path.write_text(
        json.dumps(calculations, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _save_insight_calculations(run_folder: Path) -> None:
    """Persist deterministic cross-period comparisons that an Insight may cite."""
    calculations_path = run_folder / "calculations.json"
    release_path = run_folder / "exhibit-99-1.txt"
    if not calculations_path.exists() or not release_path.exists():
        return
    calculations = desk_app.load_json(calculations_path)
    entries = calculations.setdefault("calculations", {})
    annual = entries.get("operating_margin", {})
    annual_ratio = annual.get("result")
    if not isinstance(annual_ratio, (int, float)):
        return
    release_lines = release_path.read_text(encoding="utf-8", errors="replace").splitlines()
    quarter_margin: float | None = None
    source_line: int | None = None
    for index, line in enumerate(release_lines, start=1):
        if not re.search(r"\bQ[1-4]\b|quarter", line, flags=re.IGNORECASE):
            continue
        match = re.search(r"operating\s+margin\s+(?:was|of|reached)?\s*([\d.]+)%", line, flags=re.IGNORECASE)
        if match:
            quarter_margin = float(match.group(1))
            source_line = index
            break
    if quarter_margin is None or source_line is None:
        return
    annual_percent = float(annual_ratio) * 100
    gap_basis_points = (quarter_margin - annual_percent) * 100
    context = desk_app.read_run_context(run_folder)
    quarter_period_end = context.get("quarter_period_end") or "not stated"
    annual_period_end = annual.get("fiscal_periods", {}).get("period_end") or "not stated"
    entries["quarter_vs_annual_operating_margin_gap_basis_points"] = {
        "measure": "Quarter operating margin minus annual operating margin",
        "formula": "(Quarter operating margin percent - Annual operating margin percent) * 100",
        "inputs": {
            "quarter_operating_margin_percent": quarter_margin,
            "annual_operating_margin_percent": annual_percent,
        },
        "fiscal_periods": {
            "current_quarter_end": quarter_period_end,
            "annual_fiscal_year_end": annual_period_end,
        },
        "sources": {
            "quarter_operating_margin": f"exhibit-99-1.txt:{source_line}",
            "annual_operating_margin": "calculations.json:operating_margin",
        },
        "unit": "basis_points",
        "arithmetic": f"({quarter_margin:g} - {annual_percent:.8g}) * 100 = {gap_basis_points:.8g}",
        "result": gap_basis_points,
        "validation_status": "available",
        "unavailable_reason": None,
        "note": (
            f"Quarter period {quarter_period_end}, source exhibit-99-1.txt:{source_line}; "
            f"annual period {annual_period_end}, source calculations.json:operating_margin"
        ),
    }
    calculations_path.write_text(
        json.dumps(calculations, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _context(run_folder: Path, state: TeamState) -> dict[str, Any]:
    context = desk_app.read_run_context(run_folder)
    context["run_folder"] = str(run_folder.resolve())
    manifest_arguments = desk_app.load_json(run_folder / "manifest.json").get("arguments", {})
    saved_price = manifest_arguments.get("price")
    saved_price_date = manifest_arguments.get("price_date")
    saved_price_source = manifest_arguments.get("price_source")
    context["price_provenance"] = {
        "share_price": state.price if state.price is not None else saved_price,
        "date": state.price_date or saved_price_date or "not supplied",
        "source": state.price_source or saved_price_source or "not supplied",
        "arithmetic": context["calculations"].get("price_to_earnings", {}).get("arithmetic"),
        "result": context["calculations"].get("price_to_earnings", {}).get("result"),
        "basis": "latest fiscal-year diluted EPS; not TTM P/E",
    }
    faskills_path = run_folder / "faskills_metrics.json"
    context["faskills_metrics"] = (
        desk_app.load_json(faskills_path)
        if faskills_path.exists()
        else {
            "status": "not requested",
            "course_boundary": {
                "report_use_allowed": False,
                "reason": "Run the optional --faskills extension to create the audited sidecar.",
            },
        }
    )
    methodology_path = run_folder / "faskills_methodology.json"
    context["faskills_methodology"] = (
        desk_app.load_json(methodology_path)
        if methodology_path.exists()
        else {"status": "not requested", "expert_lenses": {}, "routing": {}}
    )
    tavily_path = run_folder / "tavily_research.json"
    context["tavily_research"] = (
        desk_app.load_json(tavily_path)
        if state.tavily and tavily_path.exists()
        else {
            "status": "not requested",
            "course_boundary": {
                "supplementary_context_only": True,
                "sec_remains_authoritative": True,
            },
        }
    )
    return context


def _record_driver_if_enabled(
    run_folder: Path,
    stage: str,
    action: str,
    *,
    status: str = "complete",
    details: dict[str, Any] | None = None,
) -> None:
    if (run_folder / "faskills_methodology.json").exists():
        record_driver_stage(run_folder, stage, action, status=status, details=details)


def _research_handoff(context: dict[str, Any]) -> str:
    source = context["business_and_mda_source_text"] | {
        "company": context["company"],
        "earnings_release_source_lines": context["earnings_release_source_text"],
        "filings": context["filings"],
        "course_operating_rules": load_operating_rules(),
    }
    methodology = context.get("faskills_methodology", {})
    if methodology.get("expert_lenses"):
        source["faskills_methodology_lenses"] = methodology_context_for_role(methodology, "Research Analyst")
    return desk_app.json_handoff(
        (
            "Research the business model, competitive position, catalysts, and recent developments from the supplied filings. "
            "When FAskills methodology lenses are supplied, apply every assigned lens independently and label each concise finding. "
            "Apply the separate course operating rules in the hand-off."
        ),
        source,
        "Markdown sections with exact headings: Overview; Market Positioning and Growth Outlook; Future Developments and Strategic Recommendations.",
    )


def _financial_handoff(context: dict[str, Any]) -> str:
    source = {
        "company": context["company"],
        "filings": context["filings"],
        "annual_facts": context["annual_facts"],
        "calculations": context["calculations"],
        "quarterly_release_claims": context["quarterly_release_claims"],
        "quarter_period_end": context["quarter_period_end"],
        "earnings_release_period_heading": context["earnings_release_period_heading"],
        "price_provenance": context["price_provenance"],
        "release_income_statement_lines": context["release_income_statement_lines"],
        "annual_statement_source_lines": context["annual_statement_source_lines"],
        "peers": context["peers"],
        "course_operating_rules": load_operating_rules(),
        "vendor_metrics": {
            "status": "blocked from report use",
            "reason": "The vendor-derived inputs are not yet fully reproduced from SEC XBRL facts.",
        },
    }
    methodology = context.get("faskills_methodology", {})
    if methodology.get("expert_lenses"):
        source["faskills_methodology_lenses"] = methodology_context_for_role(methodology, "Financial Analyst")
    return desk_app.json_handoff(
        (
            "Analyze the sourced annual statements and calculations, quarter, valuation, and peers. Never calculate in the model. "
            "When FAskills methodology lenses are supplied, apply every assigned lens independently and label each concise finding. "
            "Apply the separate course operating rules in the hand-off."
        ),
        source,
        "One Markdown section with the exact heading Valuation Insights.",
    )


def _advisor_handoff(research_output: str, financial_output: str) -> str:
    return desk_app.json_handoff(
        (
            "Synthesize the two supplied role outputs into a thesis and Buy, Hold, or Sell recommendation. "
            "Choose one deciding number. State any valuation limitation. Apply the separate course operating rules in the hand-off."
        ),
        {
            "Research Analyst": research_output,
            "Financial Analyst": financial_output,
            "course_operating_rules": load_operating_rules(),
        },
        "One Markdown section with the exact heading Investment Recommendation.",
    )


def _manager_handoff(
    outputs: dict[str, str],
    report: str | None,
    missing: list[str],
    methodology_plan: dict[str, Any] | None = None,
) -> str:
    return desk_app.json_handoff(
        "Review the five-part report. Report missing or inconsistent parts. Never add report content.",
        {
            "role_outputs": outputs,
            "compiled_report": report,
            "missing_sections": missing,
            "faskills_methodology_plan": methodology_plan or {"status": "not requested"},
        },
        json.dumps(
            {
                "status": "pass or retry",
                "issues": ["short issue"],
                "sections_to_retry": ["exact heading"],
            }
        ),
    )


def _retry_role_for_sections(
    role: str,
    sections: list[str],
    original_output: str,
    context: dict[str, Any],
) -> str:
    handoff = desk_app.json_handoff(
        "Repair only the named missing sections. Keep supported content. Do not add an unsupported fact.",
        {
            "sections_to_repair": sections,
            "original_output": original_output,
            "source_context": context,
        },
        "Return each repaired Markdown section with its exact required heading. Return no other section.",
    )
    return call_role(role, handoff)


def _retry_financial_core_claims(
    original_output: str,
    context: dict[str, Any],
    issues: list[dict[str, str]],
    number_issues: list[dict[str, str]] | None = None,
) -> tuple[str, str]:
    handoff = desk_app.json_handoff(
        (
            "Rewrite the complete Valuation Insights section once. Repair every listed core-claim issue. "
            "State all eleven course claims explicitly. Use only supplied facts and code calculations. "
            "Do not derive a percentage that the supplied code did not calculate. "
            "Do not relabel the FAskills fcf_conversion metric; its supplied formula is authoritative. "
            "The final Insight must compare only the supplied current-quarter revenue-growth result with the supplied "
            "latest-fiscal-year revenue-growth result. State which is higher without calculating their difference. "
            "Do not state a peer average, a selected-peer average, or a new conversion percentage."
            " Remove or repair every additional numerical statement listed in number_issues."
        ),
        {
            "core_claim_issues": issues,
            "number_issues": number_issues or [],
            "original_output": original_output,
            "source_context": json.loads(_financial_handoff(context))["context"],
        },
        "One complete Markdown section with the exact heading Valuation Insights.",
    )
    return handoff, call_role("Financial Analyst", handoff)


def _number_issues(run_folder: Path, output: str) -> list[dict[str, str]]:
    return [
        {
            "claim": mark.claim,
            "report_said": mark.report_said,
            "mark": mark.mark,
            "reason": mark.evidence,
        }
        for mark in verify_all_other_numbers(run_folder, output)
        if mark.mark != "Correct"
    ]


def _retry_role_numbers(
    role: str,
    original_output: str,
    context: dict[str, Any],
    issues: list[dict[str, str]],
) -> tuple[str, str]:
    handoff = desk_app.json_handoff(
        (
            "Rewrite the complete role output once. Repair every listed numerical-source issue. "
            "Put the exact source token immediately after each number. Remove a number when the supplied context has no exact source. "
            "Do not use a web number or a vendor-derived score. Put the evidence citation on the same line as every numerical criterion score. "
            "Preserve the required report headings and final Insight line. "
            "If the final Insight uses a calculations.json result, include at least one reported input and its exact filing-line citation."
        ),
        {
            "number_issues": issues[:100],
            "original_output": original_output,
            "source_context": context,
        },
        "The role's complete corrected Markdown output.",
    )
    return handoff, call_role(role, handoff)


def _retry_role_insight(
    role: str,
    original_output: str,
    source_context: dict[str, Any],
    issue: str,
) -> tuple[str, str]:
    handoff = desk_app.json_handoff(
        (
            "Rewrite the complete role output once. Preserve every required report section. "
            "End with one line that begins Insight:. "
            "Place an exact supplied citation token immediately after every numeric value in the Insight. "
            "A four-digit year may appear as a period label only when the same claim has an exact supplied citation. "
            "If two numbers come from different sources, cite each number separately. "
            "Do not place one citation at the end of a sentence to support several numbers from different lines. "
            "Remove every number that has no exact supplied citation. "
            "The insight must not restate the earnings release's first paragraph. "
            "Use only filing-line and calculations.json citation tokens that appear in the supplied source context. "
            "Do not invent a calculation citation name or a numerical threshold. "
            "If this is the Investment Advisor and the Insight uses a calculations.json ratio, also include one reported "
            "input from that ratio and copy its exact filing-line citation from the supplied Financial Analyst output."
        ),
        {
            "manager_issue": issue,
            "original_output": original_output,
            "source_context": source_context,
        },
        (
            "The role's complete Markdown output, ending with one Insight: line. "
            "Every number in that line has its own exact filing-line or calculations.json citation token."
        ),
    )
    return handoff, call_role(role, handoff)


def _parse_manager_output(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {
            "status": "retry",
            "issues": ["The Manager did not return valid JSON."],
            "sections_to_retry": [],
        }
    return parsed if isinstance(parsed, dict) else {
        "status": "retry",
        "issues": ["The Manager output was not a JSON object."],
        "sections_to_retry": [],
    }


class EquityResearchTeamFlow(Flow[TeamState]):
    """Run the same six nodes in the same order on every full kickoff."""

    @start()
    def run_steps(self) -> str:
        _print_node("Steps")
        ticker = self.state.ticker.strip().upper()
        if not ticker:
            raise RuntimeError("Ticker is required.")
        if self.state.saved_run:
            source_run = Path(self.state.saved_run).resolve()
            manifest = desk_app.load_json(source_run / "manifest.json")
            if manifest.get("run_status") != "success" or manifest.get("main_ticker") != ticker:
                raise RuntimeError("--saved-run must be a successful run for the requested ticker.")
            run_folder = create_week03_run(source_run)
        else:
            command = [
                sys.executable,
                str(WEEK02_ROOT / "desk_steps.py"),
                ticker,
                "--peers",
                ",".join(self.state.peers),
            ]
            if self.state.price is not None:
                if self.state.price <= 0:
                    raise RuntimeError("--price must be positive when supplied.")
                command.extend(["--price", str(self.state.price)])
            if self.state.price_date:
                command.extend(["--price-date", self.state.price_date])
            if self.state.price_source:
                command.extend(["--price-source", self.state.price_source])
            before = set(RUNS_ROOT.iterdir()) if RUNS_ROOT.exists() else set()
            subprocess.run(command, cwd=REPOSITORY_ROOT, check=True)
            run_folder = desk_app.newest_successful_run(ticker, before)
        tavily_output: str | dict[str, Any] = "not requested"
        if self.state.tavily:
            tavily_path = run_folder / "tavily_research.json"
            if self.state.reuse_tavily:
                if not tavily_path.exists():
                    raise RuntimeError("--reuse-tavily requires tavily_research.json in the saved run.")
            else:
                tavily_path = research_run_folder(
                    run_folder,
                    REPOSITORY_ROOT,
                    search_depth=self.state.tavily_depth,
                )
            tavily_result = desk_app.load_json(tavily_path)
            tavily_output = {
                "json": tavily_path.name,
                "markdown": "tavily_research.md",
                "auth_mode": tavily_result.get("auth_mode"),
                "query_count": 1,
                "result_count": tavily_result.get("result_count"),
                "supplementary_only": True,
                "reused_without_api_request": self.state.reuse_tavily,
            }
        faskills_output: str | dict[str, Any] = "not requested"
        if self.state.faskills:
            if self.state.price is None or self.state.price <= 0:
                manifest_for_price = desk_app.load_json(run_folder / "manifest.json")
                saved_price = manifest_for_price.get("arguments", {}).get("price")
                if saved_price is None or float(saved_price) <= 0:
                    raise RuntimeError("The optional FAskills extension requires a positive documented price.")
                self.state.price = float(saved_price)
            faskills_path = enrich_run_folder(
                run_folder,
                ticker,
                float(self.state.price),
                REPOSITORY_ROOT,
            )
            faskills_result = desk_app.load_json(faskills_path)
            methodology_path = save_methodology_plan(run_folder)
            record_driver_stage(
                run_folder,
                "DISCOVER",
                "Collected the saved SEC run and one Financial Datasets annual-financials response.",
                details={
                    "ticker": ticker,
                    "sec_crosscheck_status": faskills_result.get("sec_crosscheck", {}).get("status"),
                    "news_used": self.state.tavily,
                    "tavily_file": "tavily_research.json" if self.state.tavily else None,
                    "thirteen_f_used": False,
                },
            )
            record_driver_stage(
                run_folder,
                "PROCESS",
                "Calculated deterministic FAskills metrics in Python before any analyst model call.",
                details={
                    "metrics_file": faskills_path.name,
                    "missing_inputs_remain_unavailable": True,
                },
            )
            faskills_output = {
                "metrics_file": faskills_path.name,
                "methodology_file": methodology_path.name,
                "sec_crosscheck_status": faskills_result.get("sec_crosscheck", {}).get("status"),
                "report_use_allowed": faskills_result.get("course_boundary", {}).get("report_use_allowed"),
            }
        elif (run_folder / "faskills_methodology.json").exists():
            record_driver_stage(
                run_folder,
                "DISCOVER",
                "Reused the saved SEC filing set, approved Financial Datasets cross-check, and saved Tavily research without a new external request.",
                details={
                    "ticker": ticker,
                    "saved_run_replay": True,
                    "tavily_reused": self.state.reuse_tavily,
                },
            )
            record_driver_stage(
                run_folder,
                "PROCESS",
                "Reused the saved deterministic FAskills metrics and recalculated quarter growth in Python.",
                details={
                    "metrics_file": "faskills_metrics.json",
                    "quarter_growth_file": "calculations.json",
                    "new_vendor_request": False,
                },
            )
            faskills_output = {
                "metrics_file": "faskills_metrics.json",
                "methodology_file": "faskills_methodology.json",
                "reused_without_vendor_request": True,
            }
        self.state.run_folder = str(run_folder)
        manifest = desk_app.load_json(run_folder / "manifest.json")
        arguments = manifest.get("arguments", {})
        self.state.price = float(arguments.get("price")) if arguments.get("price") is not None else self.state.price
        self.state.price_date = str(arguments.get("price_date") or self.state.price_date)
        self.state.price_source = str(arguments.get("price_source") or self.state.price_source)
        _save_node_record(
            self.state,
            "Steps",
            {
                "ticker": ticker,
                "peers": self.state.peers,
                "tavily_requested": self.state.tavily,
                "tavily_depth": self.state.tavily_depth if self.state.tavily else None,
                "tavily_reused": self.state.reuse_tavily,
            },
            {
                "run_folder": str(run_folder),
                "faskills_extension": faskills_output,
                "tavily_research": tavily_output,
            },
        )
        return str(run_folder)

    @listen(run_steps)
    def run_research_analyst(self, run_folder_value: str) -> str:
        _print_node("Research Analyst")
        run_folder = Path(run_folder_value)
        context = _context(run_folder, self.state)
        handoff = _research_handoff(context)
        _record_driver_if_enabled(
            run_folder,
            "REPRESENT",
            "Routed the filing-bounded Buffett, Lynch, Wood, and Soros lenses to the Research Analyst.",
        )
        output = call_role("Research Analyst", handoff)
        output = _normalize_analyst_output("Research Analyst", output, context)
        self.state.research_output = output
        _save_node_record(self.state, "Research Analyst", json.loads(handoff), output)
        _record_driver_if_enabled(
            run_folder,
            "IMPLEMENT",
            "Completed the Research Analyst call with four independently labeled FAskills lenses.",
        )
        return output

    @listen(run_research_analyst)
    def run_financial_analyst(self, _: str) -> str:
        _print_node("Financial Analyst")
        run_folder = Path(self.state.run_folder)
        context = _context(run_folder, self.state)
        handoff = _financial_handoff(context)
        _record_driver_if_enabled(
            run_folder,
            "REPRESENT",
            "Routed the Graham, Dalio, Burry, Simons, and Shiller lenses plus approved deterministic metrics to the Financial Analyst.",
        )
        output = call_role("Financial Analyst", handoff)
        output = _normalize_analyst_output("Financial Analyst", output, context)
        self.state.financial_output = output
        _save_node_record(self.state, "Financial Analyst", json.loads(handoff), output)
        _record_driver_if_enabled(
            run_folder,
            "IMPLEMENT",
            "Completed the Financial Analyst call with five independently labeled FAskills lenses.",
        )
        return output

    @listen(run_financial_analyst)
    def run_investment_advisor(self, _: str) -> str:
        _print_node("Investment Advisor")
        handoff = _advisor_handoff(self.state.research_output, self.state.financial_output)
        output = _normalize_advisor_output(call_role("Investment Advisor", handoff))
        self.state.advisor_output = output
        _save_node_record(self.state, "Investment Advisor", json.loads(handoff), output)
        _record_driver_if_enabled(
            Path(self.state.run_folder),
            "IMPLEMENT",
            "Synthesized only the two source-bounded analyst outputs into the Investment Advisor section.",
        )
        return output

    @listen(run_investment_advisor)
    def run_strategy_manager(self, _: str) -> str:
        _print_node("Strategy Manager")
        outputs = desk_app.normalize_role_outputs(
            {
                "Research Analyst": self.state.research_output,
                "Financial Analyst": self.state.financial_output,
                "Investment Advisor": self.state.advisor_output,
            }
        )
        report, missing = desk_app.assemble_report(
            outputs["Research Analyst"],
            outputs["Financial Analyst"],
            outputs["Investment Advisor"],
        )
        methodology_path = Path(self.state.run_folder) / "faskills_methodology.json"
        methodology_plan = desk_app.load_json(methodology_path) if methodology_path.exists() else None
        handoff = _manager_handoff(outputs, report, missing, methodology_plan)
        manager_raw = call_role("Strategy Manager", handoff)
        manager_review = _parse_manager_output(manager_raw)
        self.state.manager_output = manager_raw
        _save_node_record(self.state, "Strategy Manager", json.loads(handoff), manager_review)
        context = _context(Path(self.state.run_folder), self.state)
        retried_roles: set[str] = set()
        analyst_inputs_changed = False
        if missing:
            sections_by_role: dict[str, list[str]] = {}
            for section in missing:
                sections_by_role.setdefault(desk_app.role_for_section(section), []).append(section)
            source_context = {
                "Research Analyst": json.loads(_research_handoff(context))["context"],
                "Financial Analyst": json.loads(_financial_handoff(context))["context"],
                "Investment Advisor": {
                    "Research Analyst": outputs["Research Analyst"],
                    "Financial Analyst": outputs["Financial Analyst"],
                },
            }
            for role, sections in sections_by_role.items():
                retried_roles.add(role)
                _print_node(f"{role} retry")
                retry_output = _retry_role_for_sections(
                    role,
                    sections,
                    outputs[role],
                    source_context[role],
                )
                if role in {"Research Analyst", "Financial Analyst"}:
                    retry_output = _normalize_analyst_output(role, retry_output, context)
                if role == "Financial Analyst":
                    analyst_inputs_changed = True
                elif role == "Research Analyst":
                    analyst_inputs_changed = True
                for section in sections:
                    repaired = desk_app.extract_markdown_section(retry_output, section)
                    if repaired:
                        existing = desk_app.extract_markdown_section(outputs[role], section)
                        outputs[role] = outputs[role].replace(existing, repaired) if existing else outputs[role] + "\n\n" + repaired
                _save_node_record(
                    self.state,
                    f"{role} retry",
                    {"sections": sections, "source_context": source_context[role]},
                    retry_output,
                )
            outputs = desk_app.normalize_role_outputs(outputs)
            report, missing = desk_app.assemble_report(
                outputs["Research Analyst"],
                outputs["Financial Analyst"],
                outputs["Investment Advisor"],
            )
        if report is None or missing:
            raise RuntimeError("The fixed Manager checklist found unresolved missing sections: " + ", ".join(missing))
        core_marks = verify_core_claims(Path(self.state.run_folder), report)
        core_issues = [
            {
                "claim": mark.claim,
                "mark": mark.mark,
                "report_said": mark.report_said,
                "filing_says": mark.filing_says,
                "reason": mark.evidence,
            }
            for mark in core_marks
            if mark.mark not in {"Correct", "Not in filings"}
        ]
        role_source_context = {
            "Research Analyst": json.loads(_research_handoff(context))["context"],
            "Financial Analyst": json.loads(_financial_handoff(context))["context"],
        }
        research_number_issues = _number_issues(
            Path(self.state.run_folder), outputs["Research Analyst"]
        )
        research_number_issues.extend(
            _model_derived_growth_issues(
                "Research Analyst",
                outputs["Research Analyst"],
                Path(self.state.run_folder),
            )
        )
        financial_number_issues = _number_issues(
            Path(self.state.run_folder), outputs["Financial Analyst"]
        )
        financial_number_issues.extend(
            _model_derived_growth_issues(
                "Financial Analyst",
                outputs["Financial Analyst"],
                Path(self.state.run_folder),
            )
        )
        if research_number_issues and "Research Analyst" not in retried_roles:
            _print_node("Research Analyst retry")
            retry_handoff, retry_output = _retry_role_numbers(
                "Research Analyst",
                outputs["Research Analyst"],
                role_source_context["Research Analyst"],
                research_number_issues,
            )
            outputs["Research Analyst"] = retry_output
            outputs["Research Analyst"] = _normalize_analyst_output(
                "Research Analyst", outputs["Research Analyst"], context
            )
            analyst_inputs_changed = True
            retried_roles.add("Research Analyst")
            _save_node_record(
                self.state,
                "Research Analyst retry",
                json.loads(retry_handoff),
                retry_output,
            )
            outputs = desk_app.normalize_role_outputs(outputs)
            report, missing = desk_app.assemble_report(
                outputs["Research Analyst"],
                outputs["Financial Analyst"],
                outputs["Investment Advisor"],
            )
            if report is None or missing:
                raise RuntimeError("The Research Analyst number retry did not preserve the five-part template.")
        if core_issues and "Financial Analyst" not in retried_roles:
            _print_node("Financial Analyst retry")
            retry_handoff, retry_output = _retry_financial_core_claims(
                outputs["Financial Analyst"],
                context,
                core_issues,
                financial_number_issues,
            )
            retry_output = _normalize_analyst_output("Financial Analyst", retry_output, context)
            repaired = desk_app.extract_markdown_section(retry_output, "Valuation Insights")
            if repaired:
                outputs["Financial Analyst"] = repaired
            _save_node_record(
                self.state,
                "Financial Analyst retry",
                json.loads(retry_handoff),
                retry_output,
            )
            retried_roles.add("Financial Analyst")
            analyst_inputs_changed = True
            outputs = desk_app.normalize_role_outputs(outputs)
            report, missing = desk_app.assemble_report(
                outputs["Research Analyst"],
                outputs["Financial Analyst"],
                outputs["Investment Advisor"],
            )
            if report is None or missing:
                raise RuntimeError("The Financial Analyst retry did not preserve the five-part template.")
            core_marks = verify_core_claims(Path(self.state.run_folder), report)
            core_issues = [
                {
                    "claim": mark.claim,
                    "mark": mark.mark,
                    "report_said": mark.report_said,
                    "filing_says": mark.filing_says,
                    "reason": mark.evidence,
                }
                for mark in core_marks
                if mark.mark not in {"Correct", "Not in filings"}
            ]
        elif financial_number_issues and "Financial Analyst" not in retried_roles:
            _print_node("Financial Analyst retry")
            retry_handoff, retry_output = _retry_role_numbers(
                "Financial Analyst",
                outputs["Financial Analyst"],
                role_source_context["Financial Analyst"],
                financial_number_issues,
            )
            retry_output = _normalize_analyst_output("Financial Analyst", retry_output, context)
            outputs["Financial Analyst"] = retry_output
            retried_roles.add("Financial Analyst")
            analyst_inputs_changed = True
            _save_node_record(
                self.state,
                "Financial Analyst retry",
                json.loads(retry_handoff),
                retry_output,
            )
            outputs = desk_app.normalize_role_outputs(outputs)
            report, missing = desk_app.assemble_report(
                outputs["Research Analyst"],
                outputs["Financial Analyst"],
                outputs["Investment Advisor"],
            )
            if report is None or missing:
                raise RuntimeError("The Financial Analyst number retry did not preserve the five-part template.")
            core_marks = verify_core_claims(Path(self.state.run_folder), report)
            core_issues = [
                {
                    "claim": mark.claim,
                    "mark": mark.mark,
                    "report_said": mark.report_said,
                    "filing_says": mark.filing_says,
                    "reason": mark.evidence,
                }
                for mark in core_marks
                if mark.mark not in {"Correct", "Not in filings"}
            ]
        if analyst_inputs_changed:
            _print_node("Investment Advisor refresh")
            advisor_handoff = _advisor_handoff(outputs["Research Analyst"], outputs["Financial Analyst"])
            outputs["Investment Advisor"] = _normalize_advisor_output(
                call_role("Investment Advisor", advisor_handoff)
            )
            retried_roles.add("Investment Advisor")
            _save_node_record(
                self.state,
                "Investment Advisor refresh",
                json.loads(advisor_handoff),
                outputs["Investment Advisor"],
            )
            outputs = desk_app.normalize_role_outputs(outputs)
            report, missing = desk_app.assemble_report(
                outputs["Research Analyst"],
                outputs["Financial Analyst"],
                outputs["Investment Advisor"],
            )
            if report is None or missing:
                raise RuntimeError("The Investment Advisor refresh did not preserve the five-part template.")
        persona_mode = lab05_personas_ready()
        unresolved_insights: list[dict[str, str]] = []
        if persona_mode:
            financial_insight_changed = False
            source_context = {
                "Research Analyst": json.loads(_research_handoff(context))["context"],
                "Financial Analyst": json.loads(_financial_handoff(context))["context"],
                "Investment Advisor": {
                    "Research Analyst": outputs["Research Analyst"],
                    "Financial Analyst": outputs["Financial Analyst"],
                },
            }
            initial_insight_issues = insight_issues(outputs, Path(self.state.run_folder))
            for issue in initial_insight_issues:
                role = issue["role"]
                if role in retried_roles:
                    continue
                _print_node(f"{role} retry")
                retry_handoff, retry_output = _retry_role_insight(
                    role,
                    outputs[role],
                    source_context[role],
                    issue["reason"],
                )
                if role == "Financial Analyst":
                    retry_output = _normalize_analyst_output("Financial Analyst", retry_output, context)
                    financial_insight_changed = True
                elif role == "Research Analyst":
                    retry_output = _normalize_analyst_output("Research Analyst", retry_output, context)
                else:
                    retry_output = _normalize_advisor_output(retry_output)
                outputs[role] = retry_output
                retried_roles.add(role)
                _save_node_record(
                    self.state,
                    f"{role} retry",
                    json.loads(retry_handoff),
                    retry_output,
                )
            if financial_insight_changed and "Investment Advisor" not in retried_roles:
                _print_node("Investment Advisor refresh")
                advisor_handoff = _advisor_handoff(outputs["Research Analyst"], outputs["Financial Analyst"])
                outputs["Investment Advisor"] = _normalize_advisor_output(
                    call_role("Investment Advisor", advisor_handoff)
                )
                retried_roles.add("Investment Advisor")
                _save_node_record(
                    self.state,
                    "Investment Advisor refresh",
                    json.loads(advisor_handoff),
                    outputs["Investment Advisor"],
                )
            outputs = desk_app.normalize_role_outputs(outputs)
            report, missing = desk_app.assemble_report(
                outputs["Research Analyst"],
                outputs["Financial Analyst"],
                outputs["Investment Advisor"],
            )
            if report is None or missing:
                raise RuntimeError("An Insight retry did not preserve the five-part template.")
            unresolved_insights = insight_issues(outputs, Path(self.state.run_folder))
            core_marks = verify_core_claims(Path(self.state.run_folder), report)
            core_issues = [
                {
                    "claim": mark.claim,
                    "mark": mark.mark,
                    "report_said": mark.report_said,
                    "filing_says": mark.filing_says,
                    "reason": mark.evidence,
                }
                for mark in core_marks
                if mark.mark not in {"Correct", "Not in filings"}
            ]
        manager_review["deterministic_core_claims"] = [mark.__dict__ for mark in core_marks]
        manager_review["unresolved_core_claims_after_one_retry"] = core_issues
        final_number_issues = [
            mark.__dict__
            for mark in verify_all_other_numbers(Path(self.state.run_folder), report)
            if mark.mark != "Correct"
        ]
        manager_review["unresolved_other_numbers_after_one_retry"] = final_number_issues
        unresolved_model_derived_growth = [
            issue
            for role in ANALYST_ROLES
            for issue in _model_derived_growth_issues(
                role,
                outputs[role],
                Path(self.state.run_folder),
            )
        ]
        manager_review["unresolved_model_derived_growth_after_one_retry"] = (
            unresolved_model_derived_growth
        )
        manager_review["post_generation_report_edits"] = []
        manager_review["code_written_insight_fallbacks"] = []
        manager_review["lab05_persona_checks_enabled"] = persona_mode
        manager_review["unresolved_insight_issues_after_one_retry"] = unresolved_insights
        if (
            core_issues
            or final_number_issues
            or unresolved_insights
            or unresolved_model_derived_growth
        ):
            manager_review["status"] = "failed_after_one_retry"
        if methodology_path.exists():
            assert methodology_plan is not None
            manager_review["faskills_lens_coverage"] = lens_coverage(outputs, methodology_plan)
            _record_driver_if_enabled(
                Path(self.state.run_folder),
                "VALIDATE",
                "Checked five-section completeness, core claims, Insight citations, and all nine lens labels.",
                status=(
                    "complete"
                    if manager_review["faskills_lens_coverage"].get("all_nine_complete")
                    else "limited"
                ),
                details=manager_review["faskills_lens_coverage"],
            )
        header = desk_app.report_header(Path(self.state.run_folder), context)
        report_text = desk_app.render_report_text(header, report)
        run_folder = Path(self.state.run_folder)
        (run_folder / "role_outputs.json").write_text(
            json.dumps(outputs, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (run_folder / "manager_review.json").write_text(
            json.dumps(manager_review, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (run_folder / "report.md").write_text(report_text, encoding="utf-8")
        _record_driver_if_enabled(
            run_folder,
            "EVOLVE",
            "Applied the fixed Manager checklist, used no more than one retry per role, and compiled the five report sections.",
            details={"retried_roles": sorted(retried_roles)},
        )
        self.state.report = report_text
        return report_text

    @listen(run_strategy_manager)
    def run_verifier(self, _: str) -> str:
        _print_node("Verifier")
        run_folder = Path(self.state.run_folder)
        _record_driver_if_enabled(
            run_folder,
            "VALIDATE",
            "Started the mandatory final Verifier on the compiled report and saved evidence.",
        )
        verified_path, marks, semantic_review, payload = verify_saved_run(
            run_folder,
            _semantic_check,
        )
        self.state.verified_report_path = str(verified_path)
        _save_node_record(
            self.state,
            "Verifier",
            payload,
            {
                "verified_report": str(verified_path),
                "marks": [mark.__dict__ for mark in marks],
                "semantic_review": semantic_review,
            },
        )
        manifest_path = run_folder / "manifest.json"
        manifest = desk_app.load_json(manifest_path)
        manifest["week03_agent_team"] = {
            "framework": "CrewAI Flow",
            "node_order": self.state.node_order,
            "verifier_required": True,
            "verified_report": verified_path.name,
        }
        manifest["output_filenames"] = sorted(
            set(manifest.get("output_filenames", []))
            | {
                "node_order.json",
                "node_records.json",
                "verified_report.md",
                "verifier_input.json",
                "verifier_output.json",
            }
        )
        methodology_path = run_folder / "faskills_methodology.json"
        if methodology_path.exists():
            outputs = desk_app.load_json(run_folder / "role_outputs.json")
            _record_driver_if_enabled(
                run_folder,
                "REFLECT",
                "Saved the verified report, DRIVER trace, expert-lens coverage, limitations, and reusable methodology record.",
                details={
                    "verified_report": verified_path.name,
                    "node_order": self.state.node_order,
                },
            )
            methodology_report = render_methodology_report(run_folder, outputs)
            manifest["faskills_methodology"] = {
                "enabled": True,
                "source": "CinderZhang/FAskills financial-researcher v2.0.0",
                "json": methodology_path.name,
                "driver_trace": "faskills_driver_trace.json",
                "markdown": methodology_report.name,
                "nine_lenses_routed_through_course_personas": True,
            }
            manifest["output_filenames"] = sorted(
                set(manifest.get("output_filenames", []))
                | {
                    methodology_path.name,
                    "faskills_driver_trace.json",
                    methodology_report.name,
                }
            )
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Verified report saved: {verified_path}", flush=True)
        return str(verified_path)


def _semantic_check(payload: str) -> str:
    handoff = json.dumps(
        {
            "task": (
                "Check the period and definition of each number using only this report, saved facts, and cited filing lines. "
                "Check qualitative Tavily claims only against the cited saved Tavily excerpts. "
                "Never treat Tavily as filing evidence. For an Insight line, verify the numbers and citations only. "
                "Do not mark an Insight unsupported merely because its analytical implication is an inference rather than "
                "a sentence stated verbatim in a filing. Review every code mark, but return assessment rows only for "
                "disagreements, definition problems, or non-Correct marks so the response stays bounded."
            ),
            "context": json.loads(payload),
            "expected_output": {
                "assessments": [
                    {
                        "claim": "claim",
                        "mark": "Correct, Wrong, or Unsupported",
                        "reason": "reason",
                    }
                ]
            },
        },
        ensure_ascii=False,
    )
    return call_role("Verifier", handoff)


def verify_only(run_folder: Path) -> Path:
    _print_node("Verifier")
    stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    output_name = f"verified_report_rerun_{stamp}.md"
    try:
        path, _, _, _ = verify_saved_run(run_folder, _semantic_check, output_name=output_name)
    except Exception as exc:
        print(f"Model definition review unavailable: {exc}", flush=True)
        path, _, _, _ = verify_saved_run(run_folder, output_name=output_name)
    print(f"Verified report saved: {path}")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the fixed-order equity-research agent team.")
    parser.add_argument("ticker", nargs="?", help="Main U.S. company ticker")
    parser.add_argument("--peers", default="", help="Comma-separated peer tickers")
    parser.add_argument("--price", type=float, help="Closing price used for FY-EPS P/E")
    parser.add_argument("--price-date", default="", help="Closing-price date in YYYY-MM-DD")
    parser.add_argument("--price-source", default="", help="Exchange or LSEG source for the closing price")
    parser.add_argument("--saved-run", type=Path, help="Reuse a successful saved data run")
    parser.add_argument(
        "--faskills",
        action="store_true",
        help="Save the FAskills DRIVER methodology and review-only vendor metrics sidecar",
    )
    parser.add_argument(
        "--tavily",
        action="store_true",
        help="Save one date- and domain-filtered Tavily sidecar; exclude it from graded role hand-offs",
    )
    parser.add_argument(
        "--tavily-depth",
        choices=("basic", "advanced"),
        default="advanced",
        help="Tavily search depth; advanced costs 2 Tavily credits and basic costs 1",
    )
    parser.add_argument(
        "--reuse-tavily",
        action="store_true",
        help="Reuse tavily_research.json from --saved-run without making a Tavily API request",
    )
    parser.add_argument("--verify-only", type=Path, help="Run only the mandatory Verifier on a saved run")
    return parser


def kickoff() -> None:
    args = build_parser().parse_args()
    if args.verify_only:
        verify_only(args.verify_only)
        return
    if not args.ticker:
        raise SystemExit("Ticker is required unless --verify-only is used.")
    if args.price_date and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.price_date):
        raise SystemExit("--price-date must use YYYY-MM-DD format when supplied.")
    if args.reuse_tavily and not args.saved_run:
        raise SystemExit("--reuse-tavily requires --saved-run.")
    if args.reuse_tavily and not args.tavily:
        raise SystemExit("--reuse-tavily also requires --tavily.")
    flow = EquityResearchTeamFlow()
    flow.kickoff(
        inputs={
            "ticker": args.ticker.upper(),
            "peers": parse_peers(args.peers),
            "price": args.price,
            "price_date": args.price_date,
            "price_source": args.price_source,
            "saved_run": str(args.saved_run.resolve()) if args.saved_run else "",
            "faskills": args.faskills,
            "tavily": args.tavily,
            "tavily_depth": args.tavily_depth,
            "reuse_tavily": args.reuse_tavily,
        }
    )


def plot() -> None:
    path = EquityResearchTeamFlow().plot("equity_research_team.html", show=False)
    print(path)


def run_with_trigger() -> None:
    kickoff()


if __name__ == "__main__":
    kickoff()

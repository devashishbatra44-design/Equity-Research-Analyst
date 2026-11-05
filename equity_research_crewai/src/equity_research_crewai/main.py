"""Fixed-order CrewAI Flow for the FIN 67110 equity-research agent team."""

from __future__ import annotations

import argparse
import json
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

from equity_research_crewai.verifier import verify_core_claims, verify_insight_claims, verify_saved_run  # noqa: E402


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
        r"\((10-k\.txt|10-q\.txt|8-k\.txt|exhibit-99-1\.txt):(\d+)(?:-(\d+))?\)",
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
    return issues


def _attach_quantitative_source_notes(financial_output: str, context: dict[str, Any]) -> str:
    """Keep deterministic source notes inside Valuation Insights and the Insight line last."""
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
    lines = clean.splitlines()
    insight_index = next(
        (index for index in range(len(lines) - 1, -1, -1) if lines[index].strip().startswith("Insight:")),
        None,
    )
    insight = lines.pop(insight_index).strip() if insight_index is not None else original_insight
    body = "\n".join(lines).rstrip()
    result = body + "\n\n" + desk_app.quantitative_source_notes(context)
    if insight:
        result += "\n\n" + insight
    return result.strip()


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
    state.node_order.append(node)
    state.node_records.setdefault(node, []).append({"input": handoff, "output": output})
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
    }
    for filename in data_files:
        source_path = source / filename
        if source_path.exists():
            shutil.copy2(source_path, destination / filename)
    copied_manifest_path = destination / "manifest.json"
    copied_manifest = desk_app.load_json(copied_manifest_path)
    copied_manifest["week03_parent_run"] = str(source.relative_to(REPOSITORY_ROOT) if source.is_relative_to(REPOSITORY_ROOT) else source)
    copied_manifest["week03_replay_time"] = datetime.now().astimezone().isoformat()
    copied_manifest["output_filenames"] = sorted(path.name for path in destination.iterdir() if path.is_file())
    copied_manifest_path.write_text(json.dumps(copied_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return destination


def _context(run_folder: Path, state: TeamState) -> dict[str, Any]:
    context = desk_app.read_run_context(run_folder)
    context["price_provenance"] = {
        "share_price": state.price,
        "date": state.price_date,
        "source": state.price_source,
        "arithmetic": context["calculations"].get("price_to_earnings", {}).get("arithmetic"),
        "result": context["calculations"].get("price_to_earnings", {}).get("result"),
        "basis": "latest fiscal-year diluted EPS; not TTM P/E",
    }
    return context


def _research_handoff(context: dict[str, Any]) -> str:
    source = context["business_and_mda_source_text"] | {
        "company": context["company"],
        "earnings_release_source_lines": context["earnings_release_source_text"],
        "filings": context["filings"],
    }
    return desk_app.json_handoff(
        (
            "Research the business model, competitive position, catalysts, and recent developments from the supplied filings. "
            "End with an Insight line. Put an exact citation immediately after every number. "
            "Do not write any four-digit year in the Insight; use current quarter or latest fiscal year."
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
    }
    return desk_app.json_handoff(
        (
            "Analyze the sourced annual statements and calculations, quarter, valuation, and peers. Never calculate in the model. "
            "End with an Insight line. Put an exact citation immediately after every number. "
            "Do not write any four-digit year in the Insight; use current quarter or latest fiscal year."
        ),
        source,
        "One Markdown section with the exact heading Valuation Insights.",
    )


def _advisor_handoff(research_output: str, financial_output: str) -> str:
    return desk_app.json_handoff(
        (
            "Synthesize the two supplied role outputs into a thesis and Buy, Hold, or Sell recommendation. "
            "Choose one deciding number. State any valuation limitation. End with an Insight line. "
            "Put an exact supplied citation immediately after every number. "
            "Do not write any four-digit year in the Insight; use current quarter or latest fiscal year."
        ),
        {"Research Analyst": research_output, "Financial Analyst": financial_output},
        "One Markdown section with the exact heading Investment Recommendation.",
    )


def _manager_handoff(outputs: dict[str, str], report: str | None, missing: list[str]) -> str:
    return desk_app.json_handoff(
        "Review the five-part report. Report missing or inconsistent parts. Never add report content.",
        {"role_outputs": outputs, "compiled_report": report, "missing_sections": missing},
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
) -> tuple[str, str]:
    handoff = desk_app.json_handoff(
        (
            "Rewrite the complete Valuation Insights section once. Repair every listed core-claim issue. "
            "State all eleven course claims explicitly. Use only supplied facts and code calculations."
        ),
        {
            "core_claim_issues": issues,
            "original_output": original_output,
            "source_context": json.loads(_financial_handoff(context))["context"],
        },
        "One complete Markdown section with the exact heading Valuation Insights.",
    )
    return handoff, call_role("Financial Analyst", handoff)


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
            "Treat a calendar year or fiscal year as a numeric value that also needs an exact citation; otherwise omit the year. "
            "Do not include a four-digit calendar or fiscal year in the Insight line; use current quarter or latest fiscal year. "
            "If two numbers come from different sources, cite each number separately. "
            "Do not place one citation at the end of a sentence to support several numbers from different lines. "
            "Remove every number that has no exact supplied citation. "
            "The insight must not restate the earnings release's first paragraph. "
            "Use only filing-line and calculations.json citation tokens that appear in the supplied source context. "
            "Do not invent a calculation citation name or a numerical threshold."
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
            if self.state.price is None or self.state.price <= 0:
                raise RuntimeError("A positive --price is required for a new data run.")
            command = [
                sys.executable,
                str(WEEK02_ROOT / "desk_steps.py"),
                ticker,
                "--peers",
                ",".join(self.state.peers),
                "--price",
                str(self.state.price),
                "--price-date",
                self.state.price_date,
                "--price-source",
                self.state.price_source,
            ]
            before = set(RUNS_ROOT.iterdir()) if RUNS_ROOT.exists() else set()
            subprocess.run(command, cwd=REPOSITORY_ROOT, check=True)
            run_folder = desk_app.newest_successful_run(ticker, before)
        self.state.run_folder = str(run_folder)
        manifest = desk_app.load_json(run_folder / "manifest.json")
        arguments = manifest.get("arguments", {})
        self.state.price = float(arguments.get("price")) if arguments.get("price") is not None else self.state.price
        self.state.price_date = str(arguments.get("price_date") or self.state.price_date)
        self.state.price_source = str(arguments.get("price_source") or self.state.price_source)
        _save_node_record(
            self.state,
            "Steps",
            {"ticker": ticker, "peers": self.state.peers},
            {"run_folder": str(run_folder)},
        )
        return str(run_folder)

    @listen(run_steps)
    def run_research_analyst(self, run_folder_value: str) -> str:
        _print_node("Research Analyst")
        context = _context(Path(run_folder_value), self.state)
        handoff = _research_handoff(context)
        output = call_role("Research Analyst", handoff)
        self.state.research_output = output
        _save_node_record(self.state, "Research Analyst", json.loads(handoff), output)
        return output

    @listen(run_research_analyst)
    def run_financial_analyst(self, _: str) -> str:
        _print_node("Financial Analyst")
        context = _context(Path(self.state.run_folder), self.state)
        handoff = _financial_handoff(context)
        output = call_role("Financial Analyst", handoff)
        output = _attach_quantitative_source_notes(output, context)
        self.state.financial_output = output
        _save_node_record(self.state, "Financial Analyst", json.loads(handoff), output)
        return output

    @listen(run_financial_analyst)
    def run_investment_advisor(self, _: str) -> str:
        _print_node("Investment Advisor")
        handoff = _advisor_handoff(self.state.research_output, self.state.financial_output)
        output = call_role("Investment Advisor", handoff)
        self.state.advisor_output = output
        _save_node_record(self.state, "Investment Advisor", json.loads(handoff), output)
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
        handoff = _manager_handoff(outputs, report, missing)
        manager_raw = call_role("Strategy Manager", handoff)
        manager_review = _parse_manager_output(manager_raw)
        self.state.manager_output = manager_raw
        _save_node_record(self.state, "Strategy Manager", json.loads(handoff), manager_review)
        context = _context(Path(self.state.run_folder), self.state)
        retried_roles: set[str] = set()
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
        if core_issues and "Financial Analyst" not in retried_roles:
            _print_node("Financial Analyst retry")
            retry_handoff, retry_output = _retry_financial_core_claims(
                outputs["Financial Analyst"],
                context,
                core_issues,
            )
            retry_output = _attach_quantitative_source_notes(retry_output, context)
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
        persona_mode = lab05_personas_ready()
        unresolved_insights: list[dict[str, str]] = []
        if persona_mode:
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
                    retry_output = _attach_quantitative_source_notes(retry_output, context)
                outputs[role] = retry_output
                retried_roles.add(role)
                _save_node_record(
                    self.state,
                    f"{role} retry",
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
        manager_review["lab05_persona_checks_enabled"] = persona_mode
        manager_review["unresolved_insight_issues_after_one_retry"] = unresolved_insights
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
        self.state.report = report_text
        return report_text

    @listen(run_strategy_manager)
    def run_verifier(self, _: str) -> str:
        _print_node("Verifier")
        run_folder = Path(self.state.run_folder)
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
        manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"Verified report saved: {verified_path}", flush=True)
        return str(verified_path)


def _semantic_check(payload: str) -> str:
    handoff = json.dumps(
        {
            "task": "Check the period and definition of each number using only this report, saved facts, and cited filing lines.",
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
    path, _, _, _ = verify_saved_run(run_folder, _semantic_check)
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
    parser.add_argument("--verify-only", type=Path, help="Run only the mandatory Verifier on a saved run")
    return parser


def kickoff() -> None:
    args = build_parser().parse_args()
    if args.verify_only:
        verify_only(args.verify_only)
        return
    if not args.ticker:
        raise SystemExit("Ticker is required unless --verify-only is used.")
    if not args.saved_run:
        if not args.price_date or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.price_date):
            raise SystemExit("A new run requires --price-date in YYYY-MM-DD format.")
        if not args.price_source:
            raise SystemExit("A new run requires --price-source.")
    flow = EquityResearchTeamFlow()
    flow.kickoff(
        inputs={
            "ticker": args.ticker.upper(),
            "peers": parse_peers(args.peers),
            "price": args.price,
            "price_date": args.price_date,
            "price_source": args.price_source,
            "saved_run": str(args.saved_run.resolve()) if args.saved_run else "",
        }
    )


def plot() -> None:
    path = EquityResearchTeamFlow().plot("equity_research_team.html", show=False)
    print(path)


def run_with_trigger() -> None:
    kickoff()


if __name__ == "__main__":
    kickoff()

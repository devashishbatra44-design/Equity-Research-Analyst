#!/usr/bin/env python3
"""Run the SEC data pipeline, then the four-role equity-research desk."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

try:
    from .desk_steps import PROJECT_ROOT, RUNS_ROOT, parse_peers
except ImportError:  # also support direct `python week02/desk_app.py` execution
    from desk_steps import PROJECT_ROOT, RUNS_ROOT, parse_peers


HEADINGS = [
    "Overview",
    "Market Positioning and Growth Outlook",
    "Valuation Insights",
    "Future Developments and Strategic Recommendations",
    "Investment Recommendation",
]

ROLES_ROOT = Path(__file__).resolve().parent / "roles"
ROLE_FILES = {
    "Research Analyst": "research_analyst.md",
    "Financial Analyst": "financial_analyst.md",
    "Investment Advisor": "investment_advisor.md",
    "Strategy Manager": "strategy_manager.md",
}


def load_role_instructions() -> dict[str, str]:
    instructions: dict[str, str] = {}
    for role, filename in ROLE_FILES.items():
        path = ROLES_ROOT / filename
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise RuntimeError(f"Role instruction file is empty: {path}")
        instructions[role] = text
    return instructions


ROLE_INSTRUCTIONS = load_role_instructions()

CREWAI_SOURCE_ROOT = Path(__file__).resolve().parents[1] / "equity_research_crewai" / "src"
if str(CREWAI_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(CREWAI_SOURCE_ROOT))


def load_model_config() -> tuple[str, str, str]:
    load_dotenv(PROJECT_ROOT / ".env", override=False)
    api_key = (os.getenv("API_KEY") or os.getenv("GENAI_API_KEY") or "").strip()
    base_url = os.getenv("GENAI_BASE_URL", "").strip()
    model = os.getenv("GENAI_MODEL", "").strip()
    missing = [label for label, value in (("API_KEY or GENAI_API_KEY", api_key), ("GENAI_BASE_URL", base_url), ("GENAI_MODEL", model)) if not value]
    if missing:
        raise RuntimeError("Missing model configuration in .env: " + ", ".join(missing))
    return api_key, base_url, model


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def line_labeled_text(path: Path, start: int, end: int) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    return "\n".join(f"{path.name}:{number}: {lines[number - 1]}" for number in range(start, min(end, len(lines)) + 1))


def bounded_line_labeled_text(path: Path, max_characters: int = 16000) -> str:
    """Return a line-labeled source excerpt without cutting a source line."""
    if max_characters <= 0:
        return ""
    output: list[str] = []
    length = 0
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        labeled = f"{path.name}:{number}: {line}"
        addition = len(labeled) + (1 if output else 0)
        if output and length + addition > max_characters:
            break
        output.append(labeled)
        length += addition
    return "\n".join(output)


def find_heading_line(lines: list[str], patterns: list[str], start_at: int = 0) -> int | None:
    for index in range(start_at, len(lines)):
        if any(re.match(pattern, lines[index].strip(), flags=re.IGNORECASE) for pattern in patterns):
            return index
    return None


def find_item_heading(lines: list[str], item: str, title_pattern: str, start_at: int = 0) -> int | None:
    item_rx = re.compile(rf"^item\s+{re.escape(item)}\b", flags=re.IGNORECASE)
    title_rx = re.compile(title_pattern, flags=re.IGNORECASE)
    candidates = []
    for index in range(start_at, len(lines)):
        heading = lines[index].strip()
        if not item_rx.search(heading) or re.search(r"\|\s*\d+\s*$", heading):
            continue
        # SEC text conversion may put the Item number and its title on
        # separate lines. Check the heading line and the next two lines.
        wrapped_heading = " ".join(line.strip() for line in lines[index:index + 3])
        if title_rx.search(wrapped_heading):
            candidates.append(index)
    # EDGAR text may contain a table of contents and prose references. A
    # standalone all-caps Item heading is the strongest heading signal.
    uppercase = [index for index in candidates if re.match(rf"^ITEM\s+{re.escape(item)}\b", lines[index].strip())]
    return (uppercase or candidates or [None])[0]


def extract_filing_sections(run_folder: Path) -> dict[str, str]:
    path = run_folder / "10-k.txt"
    lines = path.read_text(encoding="utf-8").splitlines()
    business_start = find_item_heading(lines, "1", r"\bbusiness\b")
    mda_start = find_item_heading(lines, "7", r"management.?s discussion and analysis")
    risk_start = find_item_heading(lines, "1A", r"risk factors", (business_start or 0) + 1)
    item_7a_start = find_item_heading(lines, "7A", r"quantitative and qualitative disclosures", (mda_start or 0) + 1)
    if business_start is None or mda_start is None:
        raise RuntimeError("Could not locate the 10-K Item 1 and Item 7 headings in saved filing text.")
    business_end = risk_start if risk_start and risk_start > business_start else min(business_start + 520, len(lines))
    mda_end = item_7a_start if item_7a_start and item_7a_start > mda_start else min(mda_start + 520, len(lines))
    return {
        "business": "\n".join(f"10-k.txt:{i + 1}: {lines[i]}" for i in range(business_start, business_end))[:12000],
        "mda": "\n".join(f"10-k.txt:{i + 1}: {lines[i]}" for i in range(mda_start, mda_end))[:12000],
    }


def statement_line_excerpt(run_folder: Path) -> str:
    path = run_folder / "10-k.txt"
    lines = path.read_text(encoding="utf-8").splitlines()
    statements_start = find_item_heading(lines, "8", r"financial statements and supplementary data")
    start = statements_start if statements_start is not None else 0
    # Prefer statement rows over prose and note disclosures. These lines are
    # sent to the model as exact, auditable evidence.
    patterns = (
        r"^\s*(?:total\s+)?revenues?\s*\||^\s*net sales\s*\|",
        r"^\s*operating income\s*\|",
        r"^\s*net income(?: attributable[^|]*)?\s*\|",
        r"^\s*diluted\s*\|",
        r"^\s*(?:total\s+)?stockholders.? equity\s*\||^\s*total equity\s*\|",
        r"^\s*(?:short-term debt|current portion of long.term debt)\s*\|",
        r"^\s*long.term debt\s*\|",
        r"^\s*net cash provided by operating activities\s*\|",
        r"^\s*(?:additions to|purchases of|payments to acquire) property(?:, plant)? and equipment\s*\|",
    )
    selected: list[str] = []
    for pattern in patterns:
        match = next(
            (i for i, line in enumerate(lines[start:], start=start) if re.search(pattern, line, flags=re.IGNORECASE)),
            None,
        )
        if match is not None:
            selected.append(f"10-k.txt:{match + 1}: {lines[match]}")
    # Keep this source excerpt company-agnostic. XBRL facts below carry the
    # value, period, unit, accession, and concept needed to verify each claim.
    return "\n".join(selected)


def compact_fact(concept: dict[str, Any]) -> dict[str, Any]:
    return {
        key: concept.get(key)
        for key in ("label", "status", "selected_tag", "current", "prior", "reason")
    }


def compact_peer(peer: dict[str, Any]) -> dict[str, Any]:
    facts = peer.get("facts", {})
    concepts = facts.get("concepts", {})
    selected = {
        key: compact_fact(concepts[key])
        for key in ("total_revenue", "operating_income")
        if key in concepts
    }
    return {
        "ticker": peer.get("ticker"),
        "status": peer.get("status"),
        "company": peer.get("company"),
        "reference_fiscal_year": facts.get("reference_fiscal_year"),
        "facts": selected,
        "operating_margin": peer.get("operating_margin"),
        "revenue_line_label": peer.get("revenue_line_label"),
        "revenue_statement_url": peer.get("revenue_statement_url"),
        "source_url": facts.get("company_facts_source_url"),
    }


def extract_release_period(lines: list[str]) -> tuple[str | None, str]:
    period_heading = ""
    for index, line in enumerate(lines):
        if not re.search(r"(?:three|four|thirteen|sixteen|\d+)\s+(?:months?|weeks?)\s+ended", line, flags=re.IGNORECASE):
            continue
        period_heading = line.strip()
        nearby = "\n".join(lines[index:index + 5])
        date_match = re.search(
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s*(\d{4})?",
            nearby,
            flags=re.IGNORECASE,
        )
        if date_match:
            year = date_match.group(3) or re.search(r"\b20\d{2}\b", nearby)
            if year:
                year_value = year.group(0) if hasattr(year, "group") else year
                return f"{date_match.group(1).title()} {int(date_match.group(2))}, {year_value}", period_heading
    # Some releases state the fiscal quarter-end in the opening sentence.
    for line in lines:
        if "quarter" not in line.lower() or "ended" not in line.lower():
            continue
        match = re.search(
            r"quarter.*?ended\s+([A-Z][a-z]+\s+\d{1,2},\s+\d{4})",
            line,
            flags=re.IGNORECASE,
        )
        if match:
            return match.group(1), line.strip()
    return None, period_heading


def quarterly_revenue_growth_from_rows(
    lines: list[str], revenue_line_number: int | None, quarter_period_end: str | None
) -> dict[str, Any] | None:
    """Calculate same-quarter revenue growth by matching the period headers."""
    if not revenue_line_number or not quarter_period_end:
        return None
    row_index = revenue_line_number - 1
    row_match = re.match(
        r"^\s*(?:total\s+)?revenues?\s*\|\s*(.*)$",
        lines[row_index],
        flags=re.IGNORECASE,
    )
    if not row_match:
        return None
    values = [int(value.replace(",", "")) for value in re.findall(r"\(?-?\s*([\d,]+)(?:\.\d+)?\s*\)?", row_match.group(1))]
    if len(values) < 2:
        return None

    try:
        current_period = datetime.strptime(quarter_period_end, "%B %d, %Y").date()
    except ValueError:
        return None

    date_pattern = re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2},?\s+20\d{2}\b",
        flags=re.IGNORECASE,
    )
    matched_periods: list[datetime.date] | None = None
    matched_header_index: int | None = None
    for header_index in range(max(0, row_index - 6), row_index):
        labels = date_pattern.findall(lines[header_index])
        if len(labels) != len(values):
            continue
        parsed = []
        for label in labels:
            try:
                parsed.append(datetime.strptime(label.replace(",", ""), "%B %d %Y").date())
            except ValueError:
                parsed = []
                break
        if not parsed or current_period not in parsed:
            continue

        # Retail fiscal years commonly end on the same weekday rather than the
        # same calendar date.  The comparable quarter can therefore end one or
        # two days away from current_period.replace(year=year - 1).  Select the
        # adjacent prior-year column whose end is 350-380 days earlier.
        current_index = parsed.index(current_period)
        prior_candidates = [
            index
            for index, period in enumerate(parsed)
            if index != current_index and 350 <= (current_period - period).days <= 380
        ]
        if prior_candidates:
            matched_periods = parsed
            matched_header_index = header_index
            prior_index = min(
                prior_candidates,
                key=lambda index: (abs((current_period - parsed[index]).days - 364), abs(index - current_index)),
            )
            break
    if not matched_periods or matched_header_index is None:
        return None

    current_index = matched_periods.index(current_period)
    current_revenue = values[current_index]
    prior_revenue = values[prior_index]
    if prior_revenue == 0:
        return None
    formula = f"({current_revenue:,} - {prior_revenue:,}) / {prior_revenue:,}"
    return {
        "current_quarter_revenue_thousands": current_revenue,
        "prior_year_same_quarter_revenue_thousands": prior_revenue,
        "formula": formula,
        "result_percent": round((current_revenue / prior_revenue - 1) * 100, 4),
        "source_line": (
            f"exhibit-99-1.txt:{matched_header_index + 1}: {lines[matched_header_index].strip()} ; "
            f"exhibit-99-1.txt:{revenue_line_number}: {lines[row_index].strip()}"
        ),
        "basis": "computed from the current quarter and the matching quarter in the prior year",
    }


def read_run_context(run_folder: Path) -> dict[str, Any]:
    manifest = load_json(run_folder / "manifest.json")
    filings = load_json(run_folder / "filings.json")
    facts = load_json(run_folder / "facts.json")
    calculations = load_json(run_folder / "calculations.json")
    peers = load_json(run_folder / "peers.json")
    filing_sections = extract_filing_sections(run_folder)
    release_path = run_folder / "exhibit-99-1.txt"
    release_lines = release_path.read_text(encoding="utf-8").splitlines()
    quarter_period_end, release_headline = extract_release_period(release_lines)
    release_claims = facts.get("earnings_release_extraction", {}).get("claims", {})
    quoted_release = {}
    for key, claim in release_claims.items():
        quoted_release[key] = {
            "status": claim.get("status"),
            "quoted_source_text": claim.get("quoted_source_text"),
            "source_line_start": claim.get("source_line_start"),
            "source_line_end": claim.get("source_line_end"),
            "candidates": claim.get("candidates", []),
        }
    revenue_line_number = quoted_release.get("total_revenue", {}).get("source_line_start")
    if not isinstance(revenue_line_number, int):
        revenue_line_number = next(
            (i + 1 for i, line in enumerate(release_lines) if re.search(r"^\s*(?:total\s+)?revenues?\s*\|", line, flags=re.IGNORECASE)),
            None,
        )
    quarterly_growth = quarterly_revenue_growth_from_rows(
        release_lines, revenue_line_number, quarter_period_end
    )
    if not quarterly_growth:
        # Some earnings releases state quarterly revenue and its YoY change
        # in prose, not as a two-column income-statement row. Preserve the
        # issuer-reported rate without presenting it as a desk calculation.
        revenue_claim = quoted_release.get("total_revenue", {})
        quoted_text = revenue_claim.get("quoted_source_text") or ""
        reported_growth = re.search(
            r"\b(up|down)\s+([\d.]+)\s*(percent|%)\s+year[- ]over[- ]year\b",
            quoted_text,
            flags=re.IGNORECASE,
        )
        if reported_growth:
            direction, amount, _, = reported_growth.groups()
            sign = 1 if direction.lower() == "up" else -1
            quarterly_growth = {
                "reported_percent": float(amount) * sign,
                "result_percent": float(amount) * sign,
                "formula": f"issuer-reported {direction.lower()} {amount}% year over year; not independently recomputed",
                "source_line": (
                    f"exhibit-99-1.txt:{revenue_claim.get('source_line_start', 'unknown')}: "
                    f"{quoted_text}"
                ),
                "basis": "issuer-reported; not computed from two revenue columns",
            }
    quoted_release["quarter_revenue_growth"] = quarterly_growth or {"status": "unavailable", "reason": "Could not identify the two quarter columns from the release income statement."}
    return {
        "company": manifest["company"],
        "run_time": manifest["local_run_time"],
        "filings": filings,
        "business_and_mda_source_text": filing_sections,
        "annual_facts": {key: compact_fact(value) for key, value in facts["concepts"].items()},
        "reference_fiscal_year": facts["reference_fiscal_year"],
        "prior_fiscal_year": facts["prior_fiscal_year"],
        "calculations": calculations["calculations"],
        "quarterly_release_claims": quoted_release,
        "quarter_period_end": quarter_period_end,
        "earnings_release_period_heading": release_headline,
        "earnings_release_source_text": bounded_line_labeled_text(release_path),
        "release_income_statement_lines": "\n".join(
            f"exhibit-99-1.txt:{i + 1}: {line}"
            for i, line in enumerate(release_lines[:45])
        ),
        "annual_statement_source_lines": statement_line_excerpt(run_folder),
        "peers": {"definition": peers.get("definition"), "peers": [compact_peer(p) for p in peers.get("peers", [])]},
    }


def json_handoff(task: str, context: Any, expected_output: str) -> str:
    return json.dumps(
        {"task": task, "context": context, "expected_output": expected_output},
        ensure_ascii=False,
        separators=(",", ":"),
    )


def record_role_call(
    records: dict[str, list[dict[str, Any]]],
    role: str,
    purpose: str,
    handoff: str,
    output: str,
    execution_mode: str = "model_call",
) -> None:
    try:
        parsed_handoff: Any = json.loads(handoff)
    except ValueError:
        parsed_handoff = handoff
    records.setdefault(role, []).append(
        {
            "purpose": purpose,
            "execution_mode": execution_mode,
            "instruction_file": f"week02/roles/{ROLE_FILES[role]}",
            "input": parsed_handoff,
            "output": output,
        }
    )


def call_model(
    model: str,
    role: str,
    instruction: str,
    handoff: str,
    temperature: float = 0.1,
    records: dict[str, list[dict[str, Any]]] | None = None,
    purpose: str = "initial",
) -> str:
    print(f"Running role: {role}", flush=True)
    from equity_research_crewai.main import run_role as run_crewai_role

    output = run_crewai_role(role, instruction, handoff, model, temperature)
    if records is not None:
        record_role_call(records, role, purpose, handoff, output, "crewai_flow")
    return output


def extract_markdown_section(output: str, heading: str) -> str | None:
    match = re.search(
        rf"^(#{{1,6}})\s+{re.escape(heading)}\s*#*\s*$",
        output,
        flags=re.MULTILINE | re.IGNORECASE,
    )
    if not match:
        return None
    heading_level = len(match.group(1))
    next_heading = re.search(
        rf"^#{{1,{heading_level}}}\s+",
        output[match.end():],
        flags=re.MULTILINE,
    )
    end = match.end() + next_heading.start() if next_heading else len(output)
    return output[match.start():end].strip()


def assemble_report(research: str, financial: str, advisor: str) -> tuple[str | None, list[str]]:
    sections = {
        "Overview": extract_markdown_section(research, "Overview"),
        "Market Positioning and Growth Outlook": extract_markdown_section(research, "Market Positioning and Growth Outlook"),
        "Valuation Insights": extract_markdown_section(financial, "Valuation Insights"),
        "Future Developments and Strategic Recommendations": extract_markdown_section(research, "Future Developments and Strategic Recommendations"),
        "Investment Recommendation": extract_markdown_section(advisor, "Investment Recommendation"),
    }
    missing = [heading for heading, value in sections.items() if not value]
    if missing:
        return None, missing
    return "\n\n".join(sections[heading] for heading in HEADINGS), []


def report_body_from_role_outputs(outputs: dict[str, str]) -> str:
    """Return the exact five-section report body supported by saved role outputs."""
    normalized = normalize_role_outputs(outputs)
    report, missing = assemble_report(
        normalized["Research Analyst"],
        normalized["Financial Analyst"],
        normalized["Investment Advisor"],
    )
    if report is None:
        raise RuntimeError("Saved role outputs are missing required sections: " + ", ".join(missing))
    return report


def render_report_text(header: str, report: str) -> str:
    """Render a report without adding analysis outside the saved role outputs."""
    return (
        header.rstrip()
        + "\n\n"
        + report.strip()
        + "\n\n---\n\nThis is a learning exercise, not financial advice.\n\n"
        + "AI assistance: OpenAI Codex, CrewAI, and Purdue GenAI Studio. "
        + "I verified the sources myself; the judgments are mine.\n\n"
        + "Any remaining errors are my own.\n"
    )


def normalize_role_outputs(outputs: dict[str, str]) -> dict[str, str]:
    """Keep the first instance of each role's required section."""
    research = outputs.get("Research Analyst", "")
    research_sections = [
        extract_markdown_section(research, heading)
        for heading in (
            "Overview",
            "Market Positioning and Growth Outlook",
            "Future Developments and Strategic Recommendations",
        )
    ]
    financial = outputs.get("Financial Analyst", "")
    financial = extract_markdown_section(financial, "Valuation Insights") or financial
    advisor = outputs.get("Investment Advisor", "")
    advisor = extract_markdown_section(advisor, "Investment Recommendation") or advisor
    return {
        "Research Analyst": "\n\n".join(section for section in research_sections if section) or research,
        "Financial Analyst": financial,
        "Investment Advisor": advisor,
    }


def manager_review(
    model: str,
    role_outputs: dict[str, str],
    report: str | None,
    missing: list[str],
    records: dict[str, list[dict[str, Any]]] | None = None,
    purpose: str = "initial_review",
) -> dict[str, Any]:
    expected = {
        "status": "pass or retry",
        "sections_to_retry": ["one or more exact required headings"],
        "issues": ["brief consistency or completeness issue, tied to a role output"],
    }
    context = {
        "role_outputs": role_outputs,
        "assembled_report": report,
        "missing_sections_detected_by_code": missing,
        "required_sections": HEADINGS,
    }
    instruction = ROLE_INSTRUCTIONS["Strategy Manager"]
    output = call_model(
        model,
        "Strategy Manager",
        instruction,
        json_handoff(
            "Check the report once and identify only required retries.",
            context,
            json.dumps(expected),
        ),
        0,
        records,
        purpose,
    )
    try:
        parsed = json.loads(output)
    except ValueError as exc:
        raise RuntimeError(f"Strategy Manager returned invalid JSON: {exc}") from exc
    if parsed.get("status") not in {"pass", "retry"}:
        raise RuntimeError("Strategy Manager status must be pass or retry.")
    allowed = set(HEADINGS)
    sections = parsed.get("sections_to_retry", [])
    if not isinstance(sections, list) or any(section not in allowed for section in sections):
        raise RuntimeError("Strategy Manager returned an unknown section to retry.")
    if missing:
        parsed["status"] = "retry"
        parsed["sections_to_retry"] = list(dict.fromkeys(sections + missing))
    return parsed


def role_for_section(section: str) -> str:
    if section in {"Overview", "Market Positioning and Growth Outlook", "Future Developments and Strategic Recommendations"}:
        return "Research Analyst"
    if section == "Valuation Insights":
        return "Financial Analyst"
    return "Investment Advisor"


def section_context(section: str, company: dict[str, Any], source: Any, peer_outputs: dict[str, str]) -> dict[str, Any]:
    if section == "Valuation Insights":
        return {"company": company, "financial_sources_and_calculations": source}
    if section == "Investment Recommendation":
        return {"Research Analyst": peer_outputs.get("Research Analyst", ""), "Financial Analyst": peer_outputs.get("Financial Analyst", "")}
    return {"company": company, "filing_and_release_sources": source}


def quantitative_source_notes(context: dict[str, Any]) -> str:
    lines = ["**Annual XBRL source details**", ""]
    for key, fact in context["annual_facts"].items():
        current = fact.get("current")
        prior = fact.get("prior")
        if not current:
            lines.append(f"- {fact.get('label', key)}: unavailable in the selected 10-K facts.")
            continue
        unit = current.get("unit")

        def display_fact_value(item: dict[str, Any]) -> str:
            value = float(item["value"])
            if unit in {"USD/share", "USD/shares", "USD/share"}:
                return f"${value:.2f}"
            return f"${value / 1_000_000:,.0f} million"

        comparison = f"; prior {display_fact_value(prior)} at {prior['period_end']}" if prior else ""
        lines.append(
            f"- {fact['label']}: {display_fact_value(current)} at {current['period_end']}{comparison}; "
            f"XBRL tag `{fact['selected_tag']}`; {current['filing_form']} accession {current['accession_number']}; "
            f"source: {current['source_url']}."
        )
    lines.extend(["", "**Price and peer source details**", ""])
    pe = context["price_provenance"]
    eps = context["annual_facts"]["diluted_eps"]["current"]
    if pe.get("result") is None or pe.get("share_price") is None:
        lines.append(
            "- FY-EPS P/E: not computed because no share price was supplied. "
            f"Price date: {pe['date']}; price source: {pe['source']}."
        )
    else:
        lines.append(
            f"- FY-EPS P/E `(calculations.json:price_to_earnings)`: "
            f"{float(pe['result']):.4f}x = {float(pe['share_price']):.2f} / {float(eps['value']):.2f}. "
            f"Price date: {pe['date']}; price source: {pe['source']}. EPS period end: {eps['period_end']}; "
            f"EPS tag: `{eps['xbrl_tag']}`; {eps['filing_form']} accession {eps['accession_number']}. Not TTM P/E."
        )
    for peer in context["peers"].get("peers", []):
        if peer.get("status") != "success":
            lines.append(f"- {peer.get('ticker')}: peer facts unavailable; {peer.get('reason', 'see peers.json')}.")
            continue
        facts = peer.get("facts", {})
        revenue = facts.get("total_revenue", {}).get("current")
        operating = facts.get("operating_income", {}).get("current")
        margin = peer.get("operating_margin", {})
        if not revenue or not operating or margin.get("validation_status") != "available":
            lines.append(f"- {peer.get('ticker')}: peer margin unavailable; see peers.json.")
            continue
        lines.append(
            f"- {peer['company']['legal_name']} ({peer['ticker']}) operating margin: {float(margin['result']) * 100:.4f}% "
            f"= {float(operating['value']) / 1_000_000:,.0f} / {float(revenue['value']) / 1_000_000:,.0f} million; "
            f"period end {revenue['period_end']}; denominator line label "
            f"`{peer.get('revenue_line_label') or 'not recovered from the filing'}`; "
            f"revenue tag `{revenue['xbrl_tag']}`; "
            f"operating-income tag `{operating['xbrl_tag']}`; 10-K accession {revenue['accession_number']}."
        )
        if str(peer.get("revenue_line_label") or "").strip().lower() == "net sales":
            lines.append(
                f"  Definition note: the {peer['ticker']} consolidated income statement labels its top revenue line "
                "`Net sales`; that issuer-reported top line is the total operating-revenue denominator used here."
            )
    lines.extend(["", "**Code-supplied calculation details**", ""])
    calculation_labels = {
        "revenue_growth": "Revenue growth",
        "operating_margin": "Operating margin",
        "return_on_average_equity": "Return on average equity",
        "debt_to_equity": "Debt to equity",
        "free_cash_flow": "Free cash flow",
    }
    for key, label in calculation_labels.items():
        calculation = context["calculations"].get(key, {})
        if calculation.get("validation_status") == "available":
            lines.append(
                f"- {label} `(calculations.json:{key})`. Arithmetic: {calculation.get('arithmetic')}; "
                f"definition: {calculation.get('definition') or calculation.get('formula')}."
            )
    lines.extend(["", "**Quarter release source excerpts**", ""])
    for key, label in (("total_revenue", "Total revenue"), ("diluted_eps", "Diluted EPS")):
        claim = context["quarterly_release_claims"].get(key, {})
        quote = str(claim.get("quoted_source_text") or "").replace("\n", " ")
        lines.append(
            f"- {label}. Exhibit 99.1 source line {claim.get('source_line_start', 'not located')}: {quote}"
        )
    return "\n".join(lines)


def strip_quantitative_source_notes(financial_output: str) -> str:
    marker = re.search(
        r"^\*\*(?:Annual XBRL source details|Price and peer source details)\*\*\s*$",
        financial_output,
        flags=re.MULTILINE,
    )
    return financial_output[:marker.start()].rstrip() if marker else financial_output.rstrip()


def retry_role_section(
    model: str,
    section: str,
    original: str,
    issue: str,
    role: str,
    context: Any,
    records: dict[str, list[dict[str, Any]]] | None = None,
) -> str:
    instruction = ROLE_INSTRUCTIONS[role]
    retry_task = {
        "task": f"Revise only the {section} section once, addressing the manager's issue.",
        "manager_issue": issue,
        "original_role_output": original,
        "source_context": context,
        "expected_output": f"Only the complete ## {section} Markdown section. Do not add other headings.",
    }
    return call_model(
        model,
        role,
        instruction,
        json.dumps(retry_task, ensure_ascii=False),
        0.1,
        records,
        f"retry_{section}",
    )


def source_line_for_accession(filing: dict[str, Any]) -> str:
    return f"{filing.get('form')} accession {filing.get('accessionNumber')}"


def report_header(run_folder: Path, context: dict[str, Any]) -> str:
    company_name = context["company"]["legal_name"]
    ticker = context["company"]["ticker"]
    filings = context["filings"]
    named = "; ".join(
        f"{key.upper()} accession {filing.get('accessionNumber')}"
        for key, filing in filings.items()
    )
    return (
        f"# {company_name} ({ticker}) — filings read: {named}\n"
        f"# Run time: {datetime.now().astimezone().isoformat()}\n\n"
    )


def render_audit_worksheet(report: str, context: dict[str, Any], run_folder: Path) -> str:
    facts = context["annual_facts"]
    calculations = context["calculations"]
    quarterly_growth = context["quarterly_release_claims"].get("quarter_revenue_growth", {})
    release_lines = (run_folder / "exhibit-99-1.txt").read_text(encoding="utf-8").splitlines()

    def money_millions(value: Any) -> str:
        return f"${float(value) / 1_000_000:,.0f} million" if value is not None else "unavailable"

    def metric_value(key: str) -> str:
        if key in facts:
            observation = facts[key].get("current")
            if not observation:
                return "unavailable"
            value = observation.get("value")
            return f"${float(value):,.2f}" if observation.get("unit") == "USD/share" else money_millions(value)
        calc = calculations.get(key, {})
        result = calc.get("result") if calc.get("validation_status") == "available" else None
        if result is None:
            return "unavailable"
        if key in {"revenue_growth", "operating_margin", "return_on_average_equity"}:
            return f"{float(result) * 100:.4f}%"
        if key == "debt_to_equity":
            return f"{float(result):.4f}x"
        if key == "free_cash_flow":
            return money_millions(result)
        return str(result)

    release_rev = context["quarterly_release_claims"].get("total_revenue", {})
    release_line_number = release_rev.get("source_line_start")
    revenue_quote = release_rev.get("quoted_source_text") or ""
    revenue_row = re.match(r"^\s*(?:total\s+)?revenues?\s*\|\s*(.*)$", revenue_quote, flags=re.IGNORECASE)
    revenue_values = re.findall(r"\(?-?\s*([\d,]+)(?:\.\d+)?\s*\)?", revenue_row.group(1)) if revenue_row else []
    quarter_revenue_value = "review the release income statement"
    if revenue_values:
        source_unit_context = " ".join(release_lines[max(0, (release_line_number or 1) - 5):(release_line_number or 1)])
        if re.search(r"in\s+thousands?", source_unit_context, flags=re.IGNORECASE):
            revenue_unit = "thousand"
        elif re.search(r"in\s+millions?", source_unit_context, flags=re.IGNORECASE):
            revenue_unit = "million"
        else:
            revenue_unit = "as stated in the release"
        quarter_revenue_value = f"${int(revenue_values[0].replace(',', '')):,} {revenue_unit}"
    if not revenue_values:
        prose_revenue = re.search(
            r"(?:quarterly|total)\s+revenue\s+of\s+\$\s*([\d.]+)\s*(billion|million)",
            revenue_quote,
            flags=re.IGNORECASE,
        )
        if prose_revenue:
            quarter_revenue_value = f"${prose_revenue.group(1)} {prose_revenue.group(2).lower()}"
    quarter_eps_quote = context["quarterly_release_claims"].get("diluted_eps", {}).get("quoted_source_text") or ""
    eps_match = re.search(r"\$\s*([\d.]+)\s+per diluted share", quarter_eps_quote, flags=re.IGNORECASE)
    if not eps_match:
        eps_match = re.search(r"^\s*Diluted[^|]*\|\s*\$?\s*([\d.]+)", quarter_eps_quote, flags=re.IGNORECASE)
    if not eps_match:
        eps_match = re.search(
            r"diluted earnings per share\s+(?:was|were)\s+\$\s*([\d.]+)",
            quarter_eps_quote,
            flags=re.IGNORECASE,
        )
    eps_value = float(eps_match.group(1)) if eps_match else None
    if eps_value is None:
        table_eps = re.search(r"\|\s*\$\s*(?:\|\s*)?(\()?\s*(-?[\d.]+)\s*\)?", quarter_eps_quote)
        if table_eps:
            eps_value = abs(float(table_eps.group(2))) * (-1 if table_eps.group(1) else 1)
    quarter_eps_value = (
        f"$({abs(eps_value):.2f})" if eps_value is not None and eps_value < 0
        else (f"${eps_value:.2f}" if eps_value is not None else "review the release per-share lines")
    )
    core = [
        (1, "Total revenue, latest fiscal year", metric_value("total_revenue"), f"10-K accession {facts['total_revenue']['current']['accession_number']}; tag {facts['total_revenue']['selected_tag']}"),
        (2, "Revenue growth versus prior year", metric_value("revenue_growth"), f"Formula: {calculations['revenue_growth'].get('formula')}"),
        (3, "Operating income and operating margin", f"{metric_value('operating_income')}; {metric_value('operating_margin')}", f"10-K tag {facts['operating_income']['selected_tag']}; margin formula: {calculations['operating_margin'].get('formula')}"),
        (4, "Net income attributable to the company", metric_value("net_income"), f"10-K tag {facts['net_income']['selected_tag']}"),
        (5, "Diluted earnings per share, GAAP", metric_value("diluted_eps"), f"10-K tag {facts['diluted_eps']['selected_tag']}"),
        (6, "Return on average equity", metric_value("return_on_average_equity"), f"Formula: {calculations['return_on_average_equity'].get('formula')}"),
        (7, "Debt to equity, current debt included", metric_value("debt_to_equity"), f"Formula: {calculations['debt_to_equity'].get('formula')}"),
        (8, "Free cash flow", metric_value("free_cash_flow"), f"Formula: {calculations['free_cash_flow'].get('formula')}"),
        (9, "Latest quarter revenue", quarter_revenue_value, f"Exhibit 99.1 source line {release_rev.get('source_line_start', 'locate manually')}"),
        (10, "Quarterly revenue growth versus same quarter last year", f"{quarterly_growth.get('result_percent', 'unavailable')}% | {quarterly_growth.get('formula', '')}", quarterly_growth.get("source_line", "Exhibit 99.1; locate the two quarter columns")),
        (11, "Quarterly diluted EPS, GAAP", quarter_eps_value, f"Exhibit 99.1 source line {context['quarterly_release_claims'].get('diluted_eps', {}).get('source_line_start', 'locate manually')}"),
    ]
    rows = []
    for number, claim, expected, source in core:
        safe_expected = str(expected).replace("|", "\\|").replace("\n", " ")
        safe_source = str(source).replace("|", "\\|").replace("\n", " ")
        rows.append(f"| {number} | {claim} | __________________ | {safe_expected} | {safe_source} | **TO MARK BY HAND** |")

    other_rows = []
    pe = context["price_provenance"]
    eps = facts["diluted_eps"]["current"]
    other_rows.append(
        f"| FY-EPS P/E | {float(pe['result']):.4f}x = {float(pe['share_price']):.2f} / {float(eps['value']):.2f}; close {pe['date']}; EPS period {eps['period_end']}, tag {eps['xbrl_tag']}, accession {eps['accession_number']} | **TO MARK BY HAND** | {pe['source']} |"
    )
    for peer in context["peers"].get("peers", []):
        if peer.get("status") != "success":
            other_rows.append(f"| {peer.get('ticker')} margin | unavailable | **TO MARK BY HAND** | {peer.get('reason', 'see peers.json')} |")
            continue
        peer_facts = peer.get("facts", {})
        rev = peer_facts.get("total_revenue", {}).get("current")
        op = peer_facts.get("operating_income", {}).get("current")
        margin = peer.get("operating_margin", {})
        if rev and op and margin.get("validation_status") == "available":
            source = (
                f"{rev['period_end']}; denominator label {peer.get('revenue_line_label') or 'not recovered'}; "
                f"revenue tag {rev['xbrl_tag']}; operating-income tag {op['xbrl_tag']}; "
                f"10-K accession {rev['accession_number']}"
            )
            expected = f"{float(margin['result']) * 100:.4f}% = {float(op['value']) / 1e6:,.0f} / {float(rev['value']) / 1e6:,.0f} million"
            other_rows.append(f"| {peer['ticker']} operating margin | {expected} | **TO MARK BY HAND** | {source} |")

    template_present = all(extract_markdown_section(report, heading) for heading in HEADINGS)
    return (
        f"# Manual Report Audit — {context['company']['ticker']}\n\n"
        "Use the course audit checklist. Compare the report with the named filing yourself. "
        "These marks are intentionally blank because the lab requires human sign-off.\n\n"
        "Counts at top: Errors (wrong + unsupported): ______. Missing: ______.\n\n"
        "| # | Required claim | Report said | Filing says | Filing/source reference | Mark by student |\n"
        "|---:|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n## Other Financial Analyst numbers\n\n"
        "Check each peer, extra ratio, and P/E in the report. These are expected calculations and source trails, not audit marks.\n\n"
        "| Report claim | Filing/source value | Mark by student | Note |\n|---|---|---|---|\n"
        + "\n".join(other_rows)
        + "\n\n"
        "## Report checks\n\n"
        f"- Template: all five required parts are present in the generated draft: {'yes' if template_present else 'no'}. Confirm the content yourself. Mark: __________.\n"
        "- Recommendation: does it name a reported number, and does the thesis rely on claims you marked correct? Mark: __________.\n\n"
        "## Partner check on the separate partner-pick report\n\n"
        "- Partner claim 1 and mark: ______________________________\n"
        "- Partner claim 2 and mark: ______________________________\n"
        "- Partner name and initials: ______________________________\n\n"
        "Source folder: `" + run_folder.name + "`.\n\n"
        "This is a learning exercise, not financial advice.\n\n"
        "AI assistance: OpenAI Codex built the desk; Purdue GenAI Studio generated the draft. Manual source verification and judgments remain pending.\n\n"
        "Any remaining errors are my own.\n"
    )


def newest_successful_run(ticker: str, before: set[Path]) -> Path:
    choices = []
    for path in RUNS_ROOT.iterdir():
        if path in before or not (path / "manifest.json").exists():
            continue
        manifest = load_json(path / "manifest.json")
        if manifest.get("main_ticker") == ticker and manifest.get("run_status") == "success":
            choices.append(path)
    if not choices:
        raise RuntimeError("The seven-step data run did not create a successful new run folder.")
    return max(choices, key=lambda path: (path / "manifest.json").stat().st_mtime)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the SEC pipeline and the four-role equity-research desk.")
    parser.add_argument("ticker", help="Main U.S. company ticker")
    parser.add_argument("--peers", required=True, help="Comma-separated peer tickers")
    parser.add_argument("--price", required=True, type=float, help="Tuesday close used for fiscal-year P/E")
    parser.add_argument("--price-date", required=True, help="Date of the closing price (YYYY-MM-DD)")
    parser.add_argument("--price-source", required=True, help="URL or source label for the closing price")
    parser.add_argument("--saved-run", type=Path, help="Reuse a successful local data run while rerunning the model roles")
    parser.add_argument("--reuse-role-outputs", action="store_true", help="Normalize and recheck the previously saved role outputs in --saved-run")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    ticker = args.ticker.strip().upper()
    if not ticker or args.price <= 0:
        raise SystemExit("Ticker must be nonempty and --price must be positive.")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.price_date):
        raise SystemExit("--price-date must use YYYY-MM-DD.")
    peers = parse_peers(args.peers)
    if args.saved_run:
        run_folder = args.saved_run.resolve()
        if not (run_folder / "manifest.json").exists():
            raise RuntimeError(f"No manifest.json in saved run folder: {run_folder}")
        saved_manifest = load_json(run_folder / "manifest.json")
        if saved_manifest.get("run_status") != "success" or saved_manifest.get("main_ticker") != ticker:
            raise RuntimeError("--saved-run must point to a successful data run for the requested ticker.")
        saved_arguments = saved_manifest.get("arguments", {})
        if saved_arguments.get("price") is not None and float(saved_arguments["price"]) != args.price:
            raise RuntimeError("--price does not match the price saved in --saved-run.")
    else:
        before = set(RUNS_ROOT.iterdir()) if RUNS_ROOT.exists() else set()
        pipeline_path = Path(__file__).resolve().with_name("desk_steps.py")
        command = [sys.executable, str(pipeline_path), ticker, "--peers", ",".join(peers), "--price", str(args.price), "--price-date", args.price_date, "--price-source", args.price_source]
        result = subprocess.run(command, cwd=PROJECT_ROOT, check=False)
        if result.returncode:
            return result.returncode
        run_folder = newest_successful_run(ticker, before)
    context = read_run_context(run_folder)
    run_manifest = load_json(run_folder / "manifest.json")
    run_arguments = run_manifest.get("arguments", {})
    if run_arguments.get("price_date") != args.price_date or run_arguments.get("price_source") != args.price_source:
        raise RuntimeError("Price date/source must be saved in the data run. Rerun desk_steps with --price-date and --price-source.")
    context["price_provenance"] = {
        "share_price": args.price,
        "date": args.price_date,
        "source": args.price_source,
        "arithmetic": context["calculations"].get("price_to_earnings", {}).get("arithmetic"),
        "result": context["calculations"].get("price_to_earnings", {}).get("result"),
        "basis": "latest fiscal-year diluted EPS; not TTM P/E",
    }

    _, _, model = load_model_config()
    role_records: dict[str, list[dict[str, Any]]] = {}

    research_context = context["business_and_mda_source_text"] | {
        "company": context["company"],
        "earnings_release_source_lines": context["earnings_release_source_text"],
        "filings": context["filings"],
    }
    research_task = json_handoff(
        "Research the company's business model, competitive position, catalysts, and recent developments from the supplied filings.",
        research_context,
        "Markdown sections with exact headings: Overview; Market Positioning and Growth Outlook; Future Developments and Strategic Recommendations.",
    )
    finance_context = {
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
    finance_task = json_handoff(
        "Analyze the sourced annual statements and calculations, quarter, valuation, and peers. Do not calculate in the model.",
        finance_context,
        "One Markdown section with the exact heading Valuation Insights.",
    )
    if args.reuse_role_outputs:
        if not args.saved_run:
            raise RuntimeError("--reuse-role-outputs requires --saved-run.")
        outputs = load_json(run_folder / "role_outputs.json")
        required_roles = {"Research Analyst", "Financial Analyst", "Investment Advisor"}
        if not required_roles.issubset(outputs):
            raise RuntimeError("Saved role_outputs.json does not contain all three analyst role outputs.")
        outputs = normalize_role_outputs(outputs)
        research_output = outputs["Research Analyst"]
        finance_output = outputs["Financial Analyst"]
        advisor_output = outputs["Investment Advisor"]
        record_role_call(
            role_records,
            "Research Analyst",
            "reused_initial",
            research_task,
            research_output,
            "reused_saved_output",
        )
        record_role_call(
            role_records,
            "Financial Analyst",
            "reused_initial",
            finance_task,
            finance_output,
            "reused_saved_output",
        )
    else:
        research_output = call_model(
            model,
            "Research Analyst",
            ROLE_INSTRUCTIONS["Research Analyst"],
            research_task,
            records=role_records,
        )
        finance_output = call_model(
            model,
            "Financial Analyst",
            ROLE_INSTRUCTIONS["Financial Analyst"],
            finance_task,
            records=role_records,
        )
        advisor_output = ""
        outputs = {"Research Analyst": research_output, "Financial Analyst": finance_output, "Investment Advisor": advisor_output}
    finance_output = strip_quantitative_source_notes(finance_output) + "\n\n" + quantitative_source_notes(context)
    outputs["Financial Analyst"] = finance_output
    advisor_context = {"Research Analyst": research_output, "Financial Analyst": finance_output}
    advisor_task = json_handoff(
        "Synthesize the two role outputs into a thesis and Buy, Hold, or Sell recommendation. Choose one deciding number from them. If valuation data is incomplete, state that limitation.",
        advisor_context,
        "One Markdown section with the exact heading Investment Recommendation.",
    )
    advisor_output = call_model(
        model,
        "Investment Advisor",
        ROLE_INSTRUCTIONS["Investment Advisor"],
        advisor_task,
        records=role_records,
    )
    outputs["Investment Advisor"] = advisor_output
    outputs = normalize_role_outputs(outputs)
    research_output = outputs["Research Analyst"]
    finance_output = outputs["Financial Analyst"]
    advisor_output = outputs["Investment Advisor"]
    outputs_path = run_folder / "role_outputs.json"
    outputs_path.write_text(json.dumps(outputs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report, missing = assemble_report(research_output, finance_output, advisor_output)
    review = manager_review(model, outputs, report, missing, role_records)
    (run_folder / "manager_review.json").write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if review["status"] == "retry":
        for section in dict.fromkeys(review["sections_to_retry"]):
            role = role_for_section(section)
            issue = "; ".join(review.get("issues", [])) or f"The section {section} was missing or failed the completeness check."
            original = outputs[role]
            role_context = research_context if role == "Research Analyst" else (finance_context if role == "Financial Analyst" else advisor_context)
            retry_output = retry_role_section(
                model,
                section,
                original,
                issue,
                role,
                role_context,
                role_records,
            )
            if role == "Research Analyst":
                existing = [extract_markdown_section(retry_output, heading) or extract_markdown_section(original, heading) for heading in ("Overview", "Market Positioning and Growth Outlook", "Future Developments and Strategic Recommendations")]
                research_output = "\n\n".join(part for part in existing if part)
                outputs[role] = research_output
            elif role == "Financial Analyst":
                finance_output = extract_markdown_section(retry_output, section) or retry_output
                outputs[role] = finance_output
            else:
                advisor_output = extract_markdown_section(retry_output, section) or retry_output
                outputs[role] = advisor_output
            outputs_path.write_text(json.dumps(outputs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        report, missing = assemble_report(research_output, finance_output, advisor_output)
        review = manager_review(
            model,
            outputs,
            report,
            missing,
            role_records,
            "post_retry_review",
        )
        (run_folder / "manager_review.json").write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if report is None:
        raise RuntimeError("The Strategy Manager could not complete the required five-part report after one retry: " + ", ".join(missing))
    if review["status"] != "pass":
        raise RuntimeError("The Strategy Manager found unresolved report issues: " + json.dumps(review.get("issues", []), ensure_ascii=False))

    header = report_header(run_folder, context)
    report_text = render_report_text(header, report)
    report_path = run_folder / "report.md"
    report_path.write_text(report_text, encoding="utf-8")
    review_path = run_folder / "manager_review.json"
    review_path.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    role_output_path = run_folder / "role_outputs.json"
    role_output_path.write_text(json.dumps(outputs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    role_records_path = run_folder / "role_records.json"
    role_records_path.write_text(
        json.dumps(role_records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    audit_path = run_folder / "manual_audit.md"
    audit_path.write_text(render_audit_worksheet(report, context, run_folder), encoding="utf-8")

    manifest_path = run_folder / "manifest.json"
    manifest = load_json(manifest_path)
    manifest["output_filenames"] = sorted(
        set(
            manifest.get("output_filenames", [])
            + [
                "report.md",
                "manager_review.json",
                "role_outputs.json",
                "role_records.json",
                "manual_audit.md",
            ]
        )
    )
    manifest["model_provider"] = "CrewAI using Purdue GenAI Studio (OpenAI-compatible endpoint)"
    manifest["model_name"] = model
    manifest["model_key_source"] = "local .env; secret value not stored"
    manifest["manager_review"] = {"status": review["status"], "issues": review.get("issues", [])}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Report saved: {report_path}")
    print(f"Human audit worksheet saved: {audit_path}")
    print(f"Manager review: {review['status']}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1)

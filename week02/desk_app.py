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
from openai import OpenAI

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

ROLE_INSTRUCTIONS = {
    "Research Analyst": (
        "Use only the 10-K business section, the 10-K MD&A section, and the earnings release in your JSON context. "
        "Describe the business model, competitive position, catalysts, and recent developments. "
        "Write the Overview, Market Positioning and Growth Outlook, and Future Developments and Strategic Recommendations sections. "
        "Every factual claim must include a short exact quotation and its source file line number. "
        "Keep every number, condition, and hedge exactly supported by the context. Do not add facts from memory. "
        "If the source does not support a claim, state that the filing does not establish it. "
        "Return only those three Markdown sections with the exact required headings."
    ),
    "Financial Analyst": (
        "Use only the facts, calculations, quarterly release excerpts, peer facts, and source-line excerpts in your JSON context. "
        "Write the Valuation Insights section. Discuss all nine annual concepts, the ratios supplied by code, quarterly revenue and diluted EPS, "
        "quarterly revenue growth supplied by code, and peer operating margins when available. Use the quarter-end date explicitly supplied from the earnings release, "
        "not the latest 10-Q date. Do not calculate in the model. "
        "State all eleven audit claims explicitly: annual total revenue, annual revenue growth, operating income and margin, attributable net income, "
        "GAAP diluted EPS, return on average equity, debt to equity including current debt, free cash flow, quarter revenue, same-quarter revenue growth, "
        "and quarter GAAP diluted EPS. Also state P/E using the code-supplied share price, date, source and latest fiscal-year diluted EPS; "
        "label it FY-EPS P/E, not TTM P/E. Do not omit a claim; state unavailable only when its supplied source is unavailable. "
        "Do not invent or round inputs beyond what the source supports. "
        "For each number, state its filing, period, unit, XBRL tag or exact filing line, and accession when supplied. "
        "Name total revenue as the denominator for operating margin. State unavailable values plainly. "
        "Return only the Valuation Insights Markdown section with that exact heading."
    ),
    "Investment Advisor": (
        "Use only the Research Analyst and Financial Analyst outputs in your JSON context. "
        "Write the Investment Recommendation section with a Buy, Hold, or Sell recommendation, a thesis, and the single deciding number. "
        "Cite the supplied claim and period. If the supplied analysis lacks a valuation benchmark or cannot establish value, prefer Hold and say why; "
        "when P/E is supplied, name it as the deciding number and explain that a single multiple without a suitable comparison cannot establish intrinsic value. "
        "do not infer that high growth or customer retention alone makes a stock attractive. Do not introduce any company fact, number, or reasoning from outside those two role outputs. "
        "Do not present the recommendation as financial advice. Return only that Markdown section with the exact heading."
    ),
}


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


def find_heading_line(lines: list[str], patterns: list[str], start_at: int = 0) -> int | None:
    for index in range(start_at, len(lines)):
        if any(re.match(pattern, lines[index].strip(), flags=re.IGNORECASE) for pattern in patterns):
            return index
    return None


def find_item_heading(lines: list[str], item: str, title_pattern: str, start_at: int = 0) -> int | None:
    item_rx = re.compile(rf"^item\s+{re.escape(item)}\b", flags=re.IGNORECASE)
    title_rx = re.compile(title_pattern, flags=re.IGNORECASE)
    candidates = [
        index for index in range(start_at, len(lines))
        if item_rx.search(lines[index].strip())
        and title_rx.search(lines[index].strip())
        and not re.search(r"\|\s*\d+\s*$", lines[index].strip())
    ]
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
    patterns = (
        r"total revenue|total revenues|net sales|membership fees",
        r"operating income",
        r"net income attributable|net income",
        r"diluted",
        r"stockholders.? equity|total equity",
        r"current portion of long.term debt|long.term debt",
        r"net cash provided by.*operating activities",
        r"additions to property and equipment|payments to acquire property",
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
    revenue_line_number = next(
        (i + 1 for i, line in enumerate(release_lines) if re.search(r"^\s*Total revenues?\s*\|", line, flags=re.IGNORECASE)),
        None,
    )
    revenue_line = release_lines[revenue_line_number - 1] if revenue_line_number else ""
    revenue_columns = re.search(r"^\s*Total revenues?\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)", revenue_line, flags=re.IGNORECASE)
    quarterly_growth = None
    if revenue_columns:
        current_q, prior_q = (int(value.replace(",", "")) for value in revenue_columns.groups())
        quarterly_growth = {
            "current_quarter_revenue_millions": current_q,
            "prior_year_same_quarter_revenue_millions": prior_q,
            "formula": f"({current_q:,} - {prior_q:,}) / {prior_q:,}",
            "result_percent": round((current_q / prior_q - 1) * 100, 4),
            "source_line": f"exhibit-99-1.txt:{revenue_line_number}: {revenue_line.strip()}",
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
        "release_income_statement_lines": "\n".join(
            f"exhibit-99-1.txt:{i + 1}: {line}"
            for i, line in enumerate(release_lines)
            if any(token in line.lower() for token in ("total revenue", "diluted | $ | 6.75", "net income for the fourth quarter"))
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


def call_model(client: OpenAI, model: str, role: str, instruction: str, handoff: str, temperature: float = 0.1) -> str:
    print(f"Running role: {role}", flush=True)
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=3200,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are one role in an equity-research desk. Write 80% of the way to ASD-STE100. "
                    "Use short, direct sentences. Keep every number, condition, and hedge supported. "
                    "Never invent facts, sources, quotes, filing lines, or arithmetic. "
                    "Follow the JSON task, context, and expected-output fields.\n\n" + instruction
                ),
            },
            {"role": "user", "content": handoff},
        ],
    )
    content = response.choices[0].message.content if response.choices else None
    finish_reason = getattr(response.choices[0], "finish_reason", None) if response.choices else None
    if not content or not content.strip():
        choice = response.choices[0] if response.choices else None
        reason = getattr(choice, "finish_reason", None)
        usage = getattr(response, "usage", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        raise RuntimeError(
            f"The {role} returned no answer text (finish_reason={reason}, completion_tokens={completion_tokens}). "
            "The provider response metadata is recorded without exposing key material or private model reasoning."
        )
    if finish_reason == "length":
        raise RuntimeError(f"The {role} response was truncated at the output limit; no report will be marked complete.")
    return content.strip()


def extract_markdown_section(output: str, heading: str) -> str | None:
    match = re.search(rf"^#{{1,6}}\s+{re.escape(heading)}\s*#*\s*$", output, flags=re.MULTILINE | re.IGNORECASE)
    if not match:
        return None
    next_heading = re.search(r"^#{1,6}\s+", output[match.end():], flags=re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(output)
    return output[match.start():end].strip()


def assemble_report(research: str, financial: str, advisor: str) -> tuple[str | None, list[str]]:
    combined = "\n\n".join([research, financial, advisor])
    sections = {heading: extract_markdown_section(combined, heading) for heading in HEADINGS}
    missing = [heading for heading, value in sections.items() if not value]
    if missing:
        return None, missing
    return "\n\n".join(sections[heading] for heading in HEADINGS), []


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


def manager_review(client: OpenAI, model: str, role_outputs: dict[str, str], report: str | None, missing: list[str]) -> dict[str, Any]:
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
    instruction = (
        "You are the Strategy Manager. Review whether all five report parts are present and consistent with the role outputs. "
        "Check that the five headings appear exactly, numerical claims are supported by the supplied role outputs, and the recommendation "
        "names a number that appears in the report. Return only valid JSON matching the expected_output schema. "
        "Use status pass when the report is complete and consistent. Use retry only for sections that need one role retry. "
        "Map Overview, Market Positioning and Growth Outlook, and Future Developments and Strategic Recommendations to Research Analyst; "
        "map Valuation Insights to Financial Analyst; map Investment Recommendation to Investment Advisor. "
        "Never add report content or new facts."
    )
    output = call_model(client, model, "Strategy Manager", instruction, json_handoff("Check the report once and identify only required retries.", context, json.dumps(expected)), 0)
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
    lines.append(
        f"- FY-EPS P/E: {float(pe['result']):.4f}x = {float(pe['share_price']):.2f} / {float(eps['value']):.2f}. "
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
            f"period end {revenue['period_end']}; total-revenue tag `{revenue['xbrl_tag']}`; "
            f"operating-income tag `{operating['xbrl_tag']}`; 10-K accession {revenue['accession_number']}."
        )
    return "\n".join(lines)


def strip_quantitative_source_notes(financial_output: str) -> str:
    marker = re.search(
        r"^\*\*(?:Annual XBRL source details|Price and peer source details)\*\*\s*$",
        financial_output,
        flags=re.MULTILINE,
    )
    return financial_output[:marker.start()].rstrip() if marker else financial_output.rstrip()


def retry_role_section(client: OpenAI, model: str, section: str, original: str, issue: str, role: str, context: Any) -> str:
    instruction = ROLE_INSTRUCTIONS[role]
    retry_task = {
        "task": f"Revise only the {section} section once, addressing the manager's issue.",
        "manager_issue": issue,
        "original_role_output": original,
        "source_context": context,
        "expected_output": f"Only the complete ## {section} Markdown section. Do not add other headings.",
    }
    return call_model(client, model, role, instruction, json.dumps(retry_task, ensure_ascii=False), 0.1)


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
    revenue_match = re.search(r"Total revenues?\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)", release_rev.get("quoted_source_text") or "", flags=re.IGNORECASE)
    quarter_revenue_value = f"${int(revenue_match.group(1).replace(',', '')):,} million" if revenue_match else "review the release income statement"
    quarter_eps_quote = context["quarterly_release_claims"].get("diluted_eps", {}).get("quoted_source_text") or ""
    eps_match = re.search(r"\$\s*([\d.]+)\s+per diluted share", quarter_eps_quote, flags=re.IGNORECASE)
    if not eps_match:
        eps_match = re.search(r"^\s*Diluted[^|]*\|\s*\$?\s*([\d.]+)", quarter_eps_quote, flags=re.IGNORECASE)
    quarter_eps_value = f"${float(eps_match.group(1)):.2f}" if eps_match else "review the release per-share lines"
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
        rows.append(f"| {number} | {claim} | {safe_expected} | {safe_source} | **TO MARK BY HAND** | __________________ |")

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
                f"{rev['period_end']}; revenue tag {rev['xbrl_tag']}; operating-income tag {op['xbrl_tag']}; "
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
        "| # | Required claim | Expected value to compare with report | Filing/source reference | Mark by student | Filing value or note |\n"
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

    api_key, base_url, model = load_model_config()
    client = OpenAI(api_key=api_key, base_url=base_url.rstrip("/") + "/", timeout=90, max_retries=0)

    research_context = context["business_and_mda_source_text"] | {
        "company": context["company"],
        "earnings_release_source_lines": context["release_income_statement_lines"],
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
    else:
        research_output = call_model(client, model, "Research Analyst", ROLE_INSTRUCTIONS["Research Analyst"], research_task)
        finance_output = call_model(client, model, "Financial Analyst", ROLE_INSTRUCTIONS["Financial Analyst"], finance_task)
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
    advisor_output = call_model(client, model, "Investment Advisor", ROLE_INSTRUCTIONS["Investment Advisor"], advisor_task)
    outputs["Investment Advisor"] = advisor_output
    outputs = normalize_role_outputs(outputs)
    research_output = outputs["Research Analyst"]
    finance_output = outputs["Financial Analyst"]
    advisor_output = outputs["Investment Advisor"]
    outputs_path = run_folder / "role_outputs.json"
    outputs_path.write_text(json.dumps(outputs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report, missing = assemble_report(research_output, finance_output, advisor_output)
    review = manager_review(client, model, outputs, report, missing)
    (run_folder / "manager_review.json").write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if review["status"] == "retry":
        for section in dict.fromkeys(review["sections_to_retry"]):
            role = role_for_section(section)
            issue = "; ".join(review.get("issues", [])) or f"The section {section} was missing or failed the completeness check."
            original = outputs[role]
            role_context = research_context if role == "Research Analyst" else (finance_context if role == "Financial Analyst" else advisor_context)
            retry_output = retry_role_section(client, model, section, original, issue, role, role_context)
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
        review = manager_review(client, model, outputs, report, missing)
        (run_folder / "manager_review.json").write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if report is None:
        raise RuntimeError("The Strategy Manager could not complete the required five-part report after one retry: " + ", ".join(missing))
    if review["status"] != "pass":
        raise RuntimeError("The Strategy Manager found unresolved report issues: " + json.dumps(review.get("issues", []), ensure_ascii=False))

    header = report_header(run_folder, context)
    report_text = header + report.strip() + "\n\n---\n\nThis is a learning exercise, not financial advice.\n\nAI assistance: OpenAI Codex built the desk; Purdue GenAI Studio generated the draft. Manual source verification and judgments remain pending.\n\nAny remaining errors are my own.\n"
    report_path = run_folder / "report.md"
    report_path.write_text(report_text, encoding="utf-8")
    review_path = run_folder / "manager_review.json"
    review_path.write_text(json.dumps(review, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    role_output_path = run_folder / "role_outputs.json"
    role_output_path.write_text(json.dumps(outputs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    audit_path = run_folder / "manual_audit.md"
    audit_path.write_text(render_audit_worksheet(report, context, run_folder), encoding="utf-8")

    manifest_path = run_folder / "manifest.json"
    manifest = load_json(manifest_path)
    manifest["output_filenames"] = sorted(
        set(manifest.get("output_filenames", []) + ["report.md", "manager_review.json", "role_outputs.json", "manual_audit.md"])
    )
    manifest["model_provider"] = "Purdue GenAI Studio (OpenAI-compatible endpoint)"
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

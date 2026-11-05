"""Deterministic and model-assisted checks for a saved equity-research run."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass
class VerificationMark:
    claim: str
    report_said: str
    filing_says: str
    mark: str
    evidence: str


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _numbers(text: str) -> list[float]:
    pattern = r"(?<![A-Za-z])\$?(-?\d[\d,]*(?:\.\d+)?)"
    return [float(value.replace(",", "")) for value in re.findall(pattern, text)]


def _scaled_amount(match: re.Match[str]) -> float:
    value = float(match.group(1).replace(",", "").rstrip("."))
    scale = (match.group(2) or "").lower()
    if scale.startswith("billion"):
        return value * 1_000_000_000
    if scale.startswith("million"):
        return value * 1_000_000
    if scale.startswith("thousand"):
        return value * 1_000
    return value


def _amounts(report: str, pattern: str) -> list[float]:
    return [_scaled_amount(match) for match in re.finditer(pattern, report, flags=re.IGNORECASE | re.DOTALL)]


def _percents(report: str, pattern: str) -> list[float]:
    return [float(match.group(1).replace(",", "")) for match in re.finditer(pattern, report, flags=re.IGNORECASE)]


def _ratios(report: str, pattern: str) -> list[float]:
    return [
        float(match.group(1).replace(",", "").rstrip("."))
        for match in re.finditer(pattern, report, flags=re.IGNORECASE)
    ]


def _close(a: float, b: float, tolerance: float) -> bool:
    return math.isclose(a, b, rel_tol=0.0, abs_tol=tolerance)


def _format_money(value: float) -> str:
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.3f} billion"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.3f} million"
    return f"${value:,.2f}"


def _release_quarter_revenues(
    run_folder: Path,
    facts: dict[str, Any],
) -> tuple[float | None, float | None, str]:
    """Return the current and same-quarter prior-year revenue from the release table."""
    claim = facts.get("earnings_release_extraction", {}).get("claims", {}).get("total_revenue", {})
    quote = str(claim.get("quoted_source_text") or "")
    values = _numbers(quote)
    if len(values) < 2:
        return None, None, quote

    source_line = claim.get("source_line_start")
    release_path = run_folder / "exhibit-99-1.txt"
    lines = release_path.read_text(encoding="utf-8", errors="replace").splitlines() if release_path.exists() else []
    row_index = int(source_line) - 1 if isinstance(source_line, int) else -1
    nearby = lines[max(0, row_index - 10):row_index + 1] if row_index >= 0 else []
    unit_context = " ".join(nearby).lower() + " " + quote.lower()
    multiplier = 1_000 if "in thousands" in unit_context else 1_000_000

    prior_index = 1
    date_pattern = re.compile(
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{1,2},?\s+20\d{2}\b",
        flags=re.IGNORECASE,
    )
    for header in reversed(nearby[:-1]):
        labels = date_pattern.findall(header)
        if len(labels) != len(values):
            continue
        periods = [datetime.strptime(label.replace(",", ""), "%B %d %Y").date() for label in labels]
        current_period = periods[0]
        candidates = [
            index
            for index, period in enumerate(periods[1:], start=1)
            if 350 <= (current_period - period).days <= 380
        ]
        if candidates:
            prior_index = min(candidates, key=lambda index: abs(index - 1))
            break
    return values[0] * multiplier, values[prior_index] * multiplier, quote


def _quarter_eps(facts: dict[str, Any]) -> tuple[float | None, str]:
    claim = facts.get("earnings_release_extraction", {}).get("claims", {}).get("diluted_eps", {})
    quote = str(claim.get("quoted_source_text") or "")
    match = re.search(r"\$([\d,.]+)\s+per diluted share", quote, flags=re.IGNORECASE)
    if match:
        return float(match.group(1).replace(",", "")), quote
    table_values = _numbers(quote)
    return (table_values[0] if table_values else None), quote


def _fact(facts: dict[str, Any], name: str) -> dict[str, Any]:
    return facts.get("concepts", {}).get(name, {}).get("current", {})


def _calculation(calculations: dict[str, Any], name: str) -> dict[str, Any]:
    return calculations.get("calculations", {}).get(name, {})


def _valuation_section(report: str) -> str:
    match = re.search(r"^##\s+Valuation Insights\s*$", report, flags=re.MULTILINE | re.IGNORECASE)
    if not match:
        return report
    next_section = re.search(r"^#{1,2}\s+", report[match.end():], flags=re.MULTILINE)
    end = match.end() + next_section.start() if next_section else len(report)
    return report[match.start():end]


def _has_arithmetic(text: str) -> bool:
    return bool(
        re.search(
            r"(?:\*\*)?(?:Formula|Arithmetic)(?:\*\*)?\s*:|\bcalculated\s+as\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def _mark_values(
    claim: str,
    reported: list[float],
    expected: list[float],
    filing_says: str,
    evidence: str,
    tolerances: list[float],
    source_ok: bool = True,
) -> VerificationMark:
    report_said = ", ".join(f"{value:g}" for value in reported) if reported else "Not stated"
    if not reported:
        return VerificationMark(claim, report_said, filing_says, "Unsupported", "The report does not state this required claim.")
    if not source_ok:
        return VerificationMark(claim, report_said, filing_says, "Unsupported", evidence)
    if len(reported) != len(expected) or any(
        not _close(actual, target, tolerance)
        for actual, target, tolerance in zip(reported, expected, tolerances)
    ):
        return VerificationMark(claim, report_said, filing_says, "Wrong", evidence)
    return VerificationMark(claim, report_said, filing_says, "Correct", evidence)


def _mark_unavailable_calculation(
    claim: str,
    analysis: str,
    number_pattern: str,
    label_pattern: str,
    reason: str,
) -> VerificationMark:
    """Distinguish an honest unavailable claim from an invented value."""
    reported = _ratios(analysis, number_pattern)
    evidence = reason or "The required calculation inputs are not available in the saved filing facts."
    if reported:
        return VerificationMark(
            claim,
            ", ".join(f"{value:g}" for value in reported),
            "Not stated in the supplied filings",
            "Unsupported",
            evidence,
        )
    unavailable = re.search(
        rf"{label_pattern}[^\n.]*(?:not stated in (?:the )?filings|unavailable)",
        analysis,
        flags=re.IGNORECASE,
    )
    if unavailable:
        return VerificationMark(
            claim,
            unavailable.group(0).strip(),
            "Not stated in the supplied filings",
            "Not in filings",
            evidence,
        )
    return VerificationMark(
        claim,
        "Not stated",
        "Not stated in the supplied filings",
        "Missing",
        evidence,
    )


def verify_core_claims(run_folder: Path, report: str) -> list[VerificationMark]:
    analysis = _valuation_section(report)
    facts = load_json(run_folder / "facts.json")
    calculations = load_json(run_folder / "calculations.json")
    annual_revenue = _fact(facts, "total_revenue")
    operating_income = _fact(facts, "operating_income")
    net_income = _fact(facts, "net_income")
    diluted_eps = _fact(facts, "diluted_eps")
    revenue_growth = _calculation(calculations, "revenue_growth")
    operating_margin = _calculation(calculations, "operating_margin")
    return_on_equity = _calculation(calculations, "return_on_average_equity")
    debt_to_equity = _calculation(calculations, "debt_to_equity")
    free_cash_flow = _calculation(calculations, "free_cash_flow")
    quarter_revenue, prior_quarter_revenue, revenue_quote = _release_quarter_revenues(run_folder, facts)
    quarter_eps, eps_quote = _quarter_eps(facts)
    quarter_growth = None
    if quarter_revenue is not None and prior_quarter_revenue:
        quarter_growth = (quarter_revenue - prior_quarter_revenue) / prior_quarter_revenue * 100

    annual_tag = str(annual_revenue.get("xbrl_tag") or "")
    operating_tag = str(operating_income.get("xbrl_tag") or "")
    net_income_tag = str(net_income.get("xbrl_tag") or "")
    eps_tag = str(diluted_eps.get("xbrl_tag") or "")
    marks = [
        _mark_values(
            "1. Total revenue, latest fiscal year",
            _amounts(analysis, r"(?m)^(?!Insight:)[^\n]*?\bannual\s+total\s+revenue\s+(?:of|was)\s+\$?([\d,.]+)\s*(million|billion|thousand)?"),
            [float(annual_revenue.get("value"))],
            _format_money(float(annual_revenue.get("value"))),
            f"{annual_tag}; period {annual_revenue.get('period_end')}; accession {annual_revenue.get('accession_number')}",
            [1_000_000],
            source_ok=annual_tag in analysis and str(annual_revenue.get("period_end")) in analysis,
        ),
        _mark_values(
            "2. Revenue growth versus prior year",
            _percents(analysis, r"(?m)^(?!Insight:)[^\n]*?\bannual\s+revenue\s+growth\s+(?:was|of)\s+([\d,.]+)%"),
            [float(revenue_growth.get("result")) * 100],
            f"{float(revenue_growth.get('result')) * 100:.4f}%",
            str(revenue_growth.get("arithmetic")),
            [0.02],
            source_ok="Code-supplied calculation" in analysis or _has_arithmetic(analysis),
        ),
        _mark_values(
            "3. Operating income and operating margin",
            _amounts(analysis, r"(?m)^(?!Insight:)[^\n]*?\bannual\s+operating\s+income\s+(?:of|was)\s+\$?([\d,.]+)\s*(million|billion|thousand)?")
            + _percents(analysis, r"(?m)^(?!Insight:)[^\n]*?\bannual\s+operating\s+margin\s+(?:was|of)\s+([\d,.]+)%"),
            [float(operating_income.get("value")), float(operating_margin.get("result")) * 100],
            f"{_format_money(float(operating_income.get('value')))}; {float(operating_margin.get('result')) * 100:.4f}%",
            f"{operating_tag}; {operating_margin.get('arithmetic')}",
            [1_000_000, 0.02],
            source_ok=operating_tag in analysis and _has_arithmetic(analysis),
        ),
        _mark_values(
            "4. Net income attributable to the company",
            _amounts(analysis, r"(?m)^(?!Insight:)[^\n]*?\bannual\s+net\s+income(?:\s+attributable\s+to\s+the\s+company)?\s+(?:of|was)\s+\$?([\d,.]+)\s*(million|billion|thousand)?"),
            [float(net_income.get("value"))],
            _format_money(float(net_income.get("value"))),
            f"{net_income_tag}; period {net_income.get('period_end')}",
            [1_000_000],
            source_ok=net_income_tag in analysis,
        ),
        _mark_values(
            "5. Diluted earnings per share, GAAP",
            _amounts(analysis, r"(?m)^(?!Insight:)[^\n]*?\bannual\s+GAAP\s+diluted\s+(?:earnings per share|EPS)\s+(?:of|was)\s+\$?([\d,.]+)\s*(million|billion|thousand)?"),
            [float(diluted_eps.get("value"))],
            f"${float(diluted_eps.get('value')):.2f}",
            f"{eps_tag}; period {diluted_eps.get('period_end')}",
            [0.005],
            source_ok=eps_tag in analysis,
        ),
        _mark_values(
            "6. Return on average equity",
            _percents(analysis, r"(?m)^(?!Insight:)[^\n]*?\breturn\s+on\s+average\s+equity\s+(?:was|of)\s+([\d,.]+)%"),
            [float(return_on_equity.get("result")) * 100],
            f"{float(return_on_equity.get('result')) * 100:.4f}%",
            str(return_on_equity.get("arithmetic")),
            [0.02],
            source_ok="Code-supplied calculation" in analysis or _has_arithmetic(analysis),
        ),
        (
            _mark_values(
                "7. Debt to equity, including current debt",
                _ratios(analysis, r"(?m)^(?!Insight:)[^\n]*?\bdebt\s+to\s+equity\s+(?:was|of)\s+([\d,.]+)"),
                [float(debt_to_equity.get("result"))],
                f"{float(debt_to_equity.get('result')):.4f}",
                str(debt_to_equity.get("arithmetic")),
                [0.01],
                source_ok="Current portion of long-term debt" in analysis and ("Code-supplied calculation" in analysis or _has_arithmetic(analysis)),
            )
            if debt_to_equity.get("result") is not None
            else _mark_unavailable_calculation(
                "7. Debt to equity, including current debt",
                analysis,
                r"(?m)^(?!Insight:)[^\n]*?\bdebt\s+to\s+equity\s+(?:was|of)\s+([\d,.]+)",
                r"debt\s+to\s+equity",
                str(debt_to_equity.get("unavailable_reason") or ""),
            )
        ),
        _mark_values(
            "8. Free cash flow",
            _amounts(analysis, r"(?m)^(?!Insight:)[^\n]*?\bfree\s+cash\s+flow\s+(?:was|of)\s+\$?([\d,.]+)\s*(million|billion|thousand)?"),
            [float(free_cash_flow.get("result"))],
            _format_money(float(free_cash_flow.get("result"))),
            str(free_cash_flow.get("arithmetic")),
            [1_000_000],
            source_ok=("Net cash provided by operating activities" in analysis or "Net cash from operations" in analysis) and ("Code-supplied calculation" in analysis or _has_arithmetic(analysis)),
        ),
    ]
    if quarter_revenue is not None:
        marks.append(
            _mark_values(
                "9. Latest-quarter revenue",
                _amounts(analysis, r"(?m)^(?!Insight:)[^\n]*?\bquarter\s+total\s+revenue\s+(?:of|was)\s+\$?([\d,.]+)\s*(million|billion|thousand)?"),
                [quarter_revenue],
                _format_money(quarter_revenue),
                revenue_quote,
                [1_000_000],
                source_ok=("8-K Exhibit 99.1" in analysis or "Exhibit 99.1" in analysis) and "Total revenue" in analysis,
            )
        )
    if quarter_growth is not None:
        marks.append(
            _mark_values(
                "10. Quarter revenue growth versus the same quarter last year",
                _percents(analysis, r"(?m)^(?!Insight:)[^\n]*?\bquarter\s+revenue\s+growth\s+(?:was|of)\s+([\d,.]+)%"),
                [quarter_growth],
                f"{quarter_growth:.4f}%",
                f"({quarter_revenue:g} - {prior_quarter_revenue:g}) / {prior_quarter_revenue:g}",
                [0.02],
                source_ok="Code-supplied calculation" in analysis or _has_arithmetic(analysis),
            )
        )
    if quarter_eps is not None:
        marks.append(
            _mark_values(
                "11. Quarter diluted EPS, GAAP",
                _amounts(analysis, r"(?m)^(?!Insight:)[^\n]*?\bquarter\s+GAAP\s+diluted\s+(?:earnings per share|EPS)\s+(?:of|was)\s+\$?([\d,.]+)\s*(million|billion|thousand)?"),
                [quarter_eps],
                f"${quarter_eps:.2f}",
                eps_quote,
                [0.005],
                source_ok=("8-K Exhibit 99.1" in analysis or "Exhibit 99.1" in analysis)
                and ("per diluted share" in analysis or bool(re.search(r"Diluted\s*\|", analysis, flags=re.IGNORECASE))),
            )
        )
    return marks


def verify_insight_claims(run_folder: Path, report: str) -> list[VerificationMark]:
    """Check each Lab 05 Insight line against the filing lines it cites."""
    marks: list[VerificationMark] = []
    insight_lines = [
        line.strip()
        for line in report.splitlines()
        if line.strip().lower().startswith("insight:")
    ]
    citation_pattern = re.compile(
        r"\((10-k\.txt|10-q\.txt|8-k\.txt|exhibit-99-1\.txt):(\d+)(?:-(\d+))?\)",
        flags=re.IGNORECASE,
    )
    calculation_pattern = re.compile(r"\(calculations\.json:([a-z_]+)\)", flags=re.IGNORECASE)
    calculations = load_json(run_folder / "calculations.json") if (run_folder / "calculations.json").exists() else {}
    for index, insight in enumerate(insight_lines, start=1):
        citations = citation_pattern.findall(insight)
        calculation_citations = calculation_pattern.findall(insight)
        claim_without_citations = calculation_pattern.sub("", citation_pattern.sub("", insight))
        reported_numbers = _numbers(claim_without_citations)
        source_lines: list[str] = []
        missing_citation = False
        for filename, line_start_text, line_end_text in citations:
            path = run_folder / filename.lower()
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
            line_start = int(line_start_text)
            line_end = int(line_end_text or line_start_text)
            if not (0 < line_start <= line_end <= len(lines)):
                missing_citation = True
                continue
            source_lines.extend(lines[line_start - 1:line_end])
        calculation_numbers: list[float] = []
        calculation_evidence: list[str] = []
        for calculation_name in calculation_citations:
            calculation = calculations.get("calculations", {}).get(calculation_name, {})
            if calculation.get("validation_status") != "available":
                missing_citation = True
                continue
            result = float(calculation.get("result"))
            calculation_numbers.extend([result, result * 100])
            calculation_numbers.extend(_numbers(str(calculation.get("arithmetic") or "")))
            calculation_evidence.append(
                f"{calculation_name}: {calculation.get('arithmetic')}; result {result:g}"
            )
        evidence_parts = source_lines + calculation_evidence
        evidence = " | ".join(evidence_parts) if evidence_parts else "No valid source citation."
        if not citations or missing_citation or not source_lines:
            mark = "Unsupported"
        else:
            source_numbers = [number for line in source_lines for number in _numbers(line)] + calculation_numbers
            unmatched = [
                number
                for number in reported_numbers
                if not any(_close(number, source_number, 0.005) for source_number in source_numbers)
            ]
            mark = "Wrong" if unmatched else "Correct"
            if unmatched:
                evidence = f"The cited line does not contain: {', '.join(f'{number:g}' for number in unmatched)}. " + evidence
        marks.append(
            VerificationMark(
                claim=f"Insight {index}",
                report_said=claim_without_citations.removeprefix("Insight:").strip(),
                filing_says=evidence,
                mark=mark,
                evidence=evidence,
            )
        )
    return marks


def cited_line_evidence(run_folder: Path, report: str) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    pattern = re.compile(r"\((10-k\.txt|10-q\.txt|8-k\.txt|exhibit-99-1\.txt):(\d+)\)", re.IGNORECASE)
    cache: dict[str, list[str]] = {}
    for match in pattern.finditer(report):
        filename = match.group(1).lower()
        line_number = int(match.group(2))
        path = run_folder / filename
        if filename not in cache:
            cache[filename] = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
        lines = cache[filename]
        source_line = lines[line_number - 1] if 0 < line_number <= len(lines) else ""
        prefix = report[max(0, match.start() - 500):match.start()]
        sentence = re.split(r"(?<=[.!?])\s+", prefix.strip())[-1]
        evidence.append(
            {
                "citation": f"{filename}:{line_number}",
                "report_sentence": sentence,
                "source_line": source_line,
                "line_found": bool(source_line),
            }
        )
    return evidence


def build_semantic_payload(run_folder: Path, report: str, marks: list[VerificationMark]) -> dict[str, Any]:
    facts = load_json(run_folder / "facts.json")
    compact_facts = {
        "reference_fiscal_year": facts.get("reference_fiscal_year"),
        "concepts": {
            name: {
                "label": concept.get("label"),
                "selected_tag": concept.get("selected_tag"),
                "current": concept.get("current"),
                "prior": concept.get("prior"),
            }
            for name, concept in facts.get("concepts", {}).items()
        },
        "earnings_release_extraction": facts.get("earnings_release_extraction"),
    }
    return {
        "task": (
            "Check whether each cited line or XBRL fact states the report's number for the stated period and definition. "
            "Use the mark Not in filings when the code mark says Not in filings and the report does not invent a value. "
            "Do not assess the Investment Advisor's thesis. For an Insight line, check its numbers, periods, definitions, "
            "and cited evidence only; do not grade whether its analytical inference is persuasive. Return JSON only."
        ),
        "compiled_report": report,
        "saved_facts": compact_facts,
        "code_marks": [asdict(mark) for mark in marks],
        "cited_filing_lines": cited_line_evidence(run_folder, report),
        "expected_output": {
            "assessments": [
                {"claim": "claim name", "mark": "Correct, Wrong, Unsupported, or Not in filings", "reason": "short reason"}
            ]
        },
    }


def parse_semantic_review(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    parsed = json.loads(text)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("assessments"), list):
        raise ValueError("The semantic verifier did not return an assessments list.")
    return parsed


def render_verified_report(
    report: str,
    marks: list[VerificationMark],
    semantic_review: dict[str, Any] | None,
) -> str:
    lines = report.splitlines()
    first_line = lines[0] if lines else "# Verified equity-research report"
    remainder = "\n".join(lines[1:]).lstrip()
    wrong = sum(mark.mark == "Wrong" for mark in marks)
    unsupported = sum(mark.mark == "Unsupported" for mark in marks)
    missing = sum(mark.mark == "Missing" for mark in marks)
    not_in_filings = sum(mark.mark == "Not in filings" for mark in marks)
    table = [
        "## Verifier marks",
        "",
        (
            f"Code-checked claims: {len(marks)}. Wrong: {wrong}. Unsupported: {unsupported}. "
            f"Missing: {missing}. Not in filings: {not_in_filings}."
        ),
        "",
        "| Claim | Report said | Filing says | Mark | Evidence |",
        "|---|---:|---:|---|---|",
    ]
    for mark in marks:
        cells = [mark.claim, mark.report_said, mark.filing_says, mark.mark, mark.evidence]
        table.append("| " + " | ".join(str(cell).replace("|", "\\|").replace("\n", " ") for cell in cells) + " |")
    table.extend(["", "### Model definition review", ""])
    if semantic_review is None:
        table.append("The model definition review was not available. The code marks remain authoritative for exact values and arithmetic.")
    else:
        assessments = semantic_review.get("assessments", [])
        if not assessments:
            table.append("The model returned no additional definition findings.")
        for item in assessments:
            table.append(f"- **{item.get('mark', 'Unsupported')} — {item.get('claim', 'Unlabeled claim')}:** {item.get('reason', '')}")
    return first_line + "\n\n" + "\n".join(table) + "\n\n" + remainder + "\n"


def verify_saved_run(
    run_folder: Path,
    semantic_check: Callable[[str], str] | None = None,
) -> tuple[Path, list[VerificationMark], dict[str, Any] | None, dict[str, Any]]:
    run_folder = run_folder.resolve()
    report_path = run_folder / "report.md"
    if not report_path.exists():
        raise FileNotFoundError(f"No report.md in saved run: {run_folder}")
    report = report_path.read_text(encoding="utf-8")
    marks = verify_core_claims(run_folder, report) + verify_insight_claims(run_folder, report)
    payload = build_semantic_payload(run_folder, report, marks)
    semantic_review = None
    semantic_raw = ""
    if semantic_check is not None:
        semantic_raw = semantic_check(json.dumps(payload, ensure_ascii=False))
        semantic_review = parse_semantic_review(semantic_raw)
    verified_text = render_verified_report(report, marks, semantic_review)
    verified_path = run_folder / "verified_report.md"
    verified_path.write_text(verified_text, encoding="utf-8")
    (run_folder / "verifier_input.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_folder / "verifier_output.json").write_text(
        json.dumps(
            {
                "code_marks": [asdict(mark) for mark in marks],
                "semantic_review": semantic_review,
                "semantic_raw": semantic_raw,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return verified_path, marks, semantic_review, payload

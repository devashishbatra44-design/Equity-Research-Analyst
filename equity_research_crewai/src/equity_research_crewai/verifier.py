"""Deterministic and model-assisted checks for a saved equity-research run."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse


FILING_CITATION_RE = re.compile(
    r"(10-k\.txt|10-q\.txt|8-k\.txt|exhibit-99-1\.txt):\s*(\d+)(?:-(\d+))?",
    flags=re.IGNORECASE,
)
CALCULATION_CITATION_RE = re.compile(r"calculations\.json:\s*([a-z_]+)", flags=re.IGNORECASE)
FACT_CITATION_RE = re.compile(
    r"facts\.json:\s*([a-z_]+)(?::(current|prior))?",
    flags=re.IGNORECASE,
)
PEER_CITATION_RE = re.compile(
    r"peers\.json:\s*([A-Z.\-]+):([a-z_]+)",
    flags=re.IGNORECASE,
)
MANIFEST_CITATION_RE = re.compile(r"manifest\.json:\s*(price|price_date)", flags=re.IGNORECASE)
FASKILLS_CITATION_RE = re.compile(r"faskills_metrics\.json:\s*([a-z0-9_]+)", flags=re.IGNORECASE)
XBRL_APPENDIX_CITATION_RE = re.compile(
    r"XBRL\s+tag\s+`?((?:[A-Za-z0-9_-]+):[A-Za-z0-9_]+)`?",
    flags=re.IGNORECASE,
)
PEER_APPENDIX_CITATION_RE = re.compile(
    r"\(([A-Z.\-]+)\)\s+operating\s+margin",
    flags=re.IGNORECASE,
)
RELEASE_APPENDIX_CITATION_RE = re.compile(
    r"Exhibit\s+99\.1\s+source\s+line\s+(\d+)",
    flags=re.IGNORECASE,
)
ISO_DATE_RE = re.compile(r"\b(?:19|20)\d{2}-\d{2}-\d{2}\b")
ACCESSION_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}\b")
NUMBER_MENTION_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:\$\s*)?-?\d[\d,]*(?:\.\d+)?(?:/\d+)?"
    r"(?:\s*(?:%|x|billion|million|thousand|basis points?|members?|warehouses?|SKUs?))?",
    flags=re.IGNORECASE,
)


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


def _number_from_mention(text: str) -> float:
    match = re.search(r"-?\d[\d,]*(?:\.\d+)?", text)
    if not match:
        raise ValueError(f"No number in mention: {text}")
    return float(match.group(0).replace(",", ""))


def _mask_matches(text: str, pattern: re.Pattern[str]) -> str:
    return pattern.sub(lambda match: " " * (match.end() - match.start()), text)


def _all_permitted_citation_patterns() -> tuple[re.Pattern[str], ...]:
    return (
        FILING_CITATION_RE,
        CALCULATION_CITATION_RE,
        FACT_CITATION_RE,
        PEER_CITATION_RE,
        MANIFEST_CITATION_RE,
        XBRL_APPENDIX_CITATION_RE,
        PEER_APPENDIX_CITATION_RE,
        RELEASE_APPENDIX_CITATION_RE,
    )


def _numeric_equivalent(report_value: float, source_value: float) -> bool:
    """Allow presentation-unit changes such as 15.825 billion versus 15,825 million."""
    if _close(report_value, source_value, 0.005):
        return True
    for scale in (1_000.0, 1_000_000.0, 1_000_000_000.0):
        if _close(report_value * scale, source_value, max(0.005, abs(source_value) * 1e-8)):
            return True
        if _close(report_value, source_value * scale, max(0.005, abs(report_value) * 1e-8)):
            return True
    return False


def _reported_precision(mention: str) -> int:
    """Return the decimal precision used for the first number in a report mention."""
    match = re.search(r"-?\d[\d,]*(?:\.(\d+))?", mention)
    return len(match.group(1) or "") if match else 0


def _usable_arithmetic_inputs(values: list[float]) -> list[float]:
    """Remove dates and duplicate values before trying simple filing arithmetic."""
    usable: list[float] = []
    for value in values:
        if not math.isfinite(value) or value == 0:
            continue
        if value.is_integer() and 1900 <= value <= 2100:
            continue
        if not any(_numeric_equivalent(value, existing) for existing in usable):
            usable.append(value)
    return usable


def _rounded_match(reported: float, calculated: float, mention: str) -> bool:
    """Compare a derived result at the precision printed in the report."""
    precision = _reported_precision(mention)
    tolerance = (0.5 * (10 ** -precision)) + 1e-9
    return math.isclose(reported, calculated, rel_tol=0.0, abs_tol=tolerance)


def _mention_numeric_equivalent(mention: str, report_value: float, source_value: float) -> bool:
    """Compare a cited value using the unit and rounding printed in the report."""
    lower = mention.lower()
    if "billion" in lower:
        report_scale = 1_000_000_000.0
    elif "million" in lower:
        report_scale = 1_000_000.0
    elif "thousand" in lower:
        report_scale = 1_000.0
    else:
        report_scale = 1.0
    precision = _reported_precision(mention)
    tolerance = (0.5 * (10 ** -precision) * report_scale) + 1e-9
    report_base = report_value * report_scale
    for source_scale in (1.0, 1_000.0, 1_000_000.0, 1_000_000_000.0):
        if math.isclose(report_base, source_value * source_scale, rel_tol=0.0, abs_tol=tolerance):
            return True
    if report_scale == 1.0:
        return _rounded_match(report_value, source_value, mention) or _numeric_equivalent(
            report_value, source_value
        )
    return False


def _derived_arithmetic_match(
    line: str,
    mention: str,
    reported_value: float,
    source_values: list[float],
) -> str | None:
    """Validate simple growth, ratio, or difference arithmetic from cited inputs.

    This is intentionally narrow. It supports the course definition of Correct:
    the filing supplies the inputs and the report's rounded arithmetic holds.
    """
    values = _usable_arithmetic_inputs(source_values)
    if len(values) < 2:
        return None

    lower_line = line.lower()
    is_percent = "%" in mention or "basis point" in mention.lower()
    is_basis_points = "basis point" in mention.lower()
    is_multiple = bool(re.search(r"\bx\b", mention, flags=re.IGNORECASE))
    growth_language = bool(
        re.search(
            r"\b(?:grew|growth|increase[ds]?|decrease[ds]?|decline[ds]?|rose|fell|up|down|year.over.year|yoy)\b",
            lower_line,
        )
    )
    ratio_language = bool(
        re.search(
            r"\b(?:margin|ratio|return|conversion|rate|yield|share|as a percent|percentage)\b",
            lower_line,
        )
    )

    for left in values:
        for right in values:
            if left == right or right == 0:
                continue
            if is_percent and growth_language:
                # Do not infer a growth rate from unrelated percentage values in
                # a dense cited sentence. Course growth checks use reported
                # monetary or operating-count inputs.
                if abs(left) <= 100 or abs(right) <= 100:
                    continue
                growth = ((left - right) / abs(right)) * 100
                if _rounded_match(reported_value, growth, mention):
                    return f"({left:g} - {right:g}) / {right:g} = {growth:.8g}%"
            if is_percent and ratio_language:
                ratio_percent = (left / right) * 100
                if _rounded_match(reported_value, ratio_percent, mention):
                    return f"{left:g} / {right:g} = {ratio_percent:.8g}%"
            if is_basis_points:
                basis_point_difference = (left - right) * 100
                if _rounded_match(reported_value, basis_point_difference, mention):
                    return (
                        f"({left:g} percentage points - {right:g} percentage points) "
                        f"= {basis_point_difference:.8g} basis points"
                    )
            if is_multiple and ratio_language:
                ratio = left / right
                if _rounded_match(reported_value, ratio, mention):
                    return f"{left:g} / {right:g} = {ratio:.8g}x"
            if growth_language and not is_percent and not is_multiple:
                difference = left - right
                if _rounded_match(reported_value, difference, mention):
                    return f"{left:g} - {right:g} = {difference:.8g}"
    return None


def _mask_numeric_labels(text: str) -> str:
    """Ignore structural numerals such as the 5 in 'DuPont 5-factor'."""
    return re.sub(
        r"(?<![A-Za-z0-9_])\d+(?=\s*[- ]\s*(?:factor|step|stage|part|point|week)\b)",
        lambda match: " " * (match.end() - match.start()),
        text,
        flags=re.IGNORECASE,
    )


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


def _distinct_values(values: list[float], tolerance: float) -> list[float]:
    """Collapse repeated, numerically identical report statements."""
    distinct: list[float] = []
    for value in values:
        if not any(_close(value, existing, tolerance) for existing in distinct):
            distinct.append(value)
    return distinct


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


def _find_filing_line(path: Path, label_pattern: str, value: float) -> tuple[int | None, str]:
    if not path.exists():
        return None, ""
    value_forms = {f"{value:g}", f"{value:.2f}"}
    candidates: list[tuple[int, str]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if re.search(label_pattern, line, flags=re.IGNORECASE) and any(form in line for form in value_forms):
            candidates.append((line_number, line.strip()))
    if candidates:
        return max(
            candidates,
            key=lambda item: (
                int(bool(re.match(r"^\s*diluted\b", item[1], flags=re.IGNORECASE))),
                int("|" in item[1]),
                -len(item[1]),
            ),
        )
    return None, ""


def _valuation_section(report: str) -> str:
    match = re.search(r"^#{1,2}\s+Valuation Insights\s*$", report, flags=re.MULTILINE | re.IGNORECASE)
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


def _matching_report_lines(text: str, patterns: list[str]) -> str:
    matched: list[str] = []
    for pattern in patterns:
        line = next(
            (
                candidate.strip()
                for candidate in text.splitlines()
                if re.search(pattern, candidate, flags=re.IGNORECASE)
                and not re.match(r"^\s*(?:#+\s*)?(?:\*+)?\d+[.)]", candidate)
                and (NUMBER_MENTION_RE.search(candidate) or "not stated" in candidate.lower() or "unavailable" in candidate.lower())
            ),
            "",
        )
        if line:
            matched.append(line)
    return " ".join(matched)


def verify_core_claims(run_folder: Path, report: str) -> list[VerificationMark]:
    analysis = _valuation_section(report)
    core_analysis = analysis
    core_marker = "### Required Course Claims — Code-Built Audit Block"
    if core_marker in analysis:
        core_analysis = analysis.rsplit(core_marker, 1)[1]
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
    eps_line_number, eps_line_text = _find_filing_line(
        run_folder / "10-k.txt",
        r"\bdiluted\b",
        float(diluted_eps.get("value")),
    )
    eps_line_evidence = (
        f"; 10-k.txt:{eps_line_number}: {eps_line_text}" if eps_line_number is not None else ""
    )
    marks = [
        _mark_values(
            "1. Total revenue, latest fiscal year",
            _amounts(core_analysis, r"(?mi)^(?!\s*Insight:)(?![^\n]*\brelationship\s+between\b)[^\n]*?\bannual\s+total\s+revenue\s+(?:of|was)\s+\$?([\d,.]+)\s*(million|billion|thousand)?"),
            [float(annual_revenue.get("value"))],
            _format_money(float(annual_revenue.get("value"))),
            f"{annual_tag}; period {annual_revenue.get('period_end')}; accession {annual_revenue.get('accession_number')}",
            [1_000_000],
            source_ok=bool(re.search(r"facts\.json:\s*total_revenue\b", core_analysis, flags=re.IGNORECASE))
            or (annual_tag in analysis and str(annual_revenue.get("period_end")) in analysis),
        ),
        _mark_values(
            "2. Revenue growth versus prior year",
            _percents(core_analysis, r"(?mi)^(?!\s*Insight:)(?![^\n]*\brelationship\s+between\b)[^\n]*?\bannual\s+revenue\s+growth\s+(?:was|of)\s+([\d,.]+)%"),
            [float(revenue_growth.get("result")) * 100],
            f"{float(revenue_growth.get('result')) * 100:.4f}%",
            str(revenue_growth.get("arithmetic")),
            [0.02],
            source_ok=bool(re.search(r"calculations\.json:\s*revenue_growth\b", core_analysis, flags=re.IGNORECASE))
            or "Code-supplied calculation" in analysis
            or _has_arithmetic(analysis),
        ),
        _mark_values(
            "3. Operating income and operating margin",
            _amounts(core_analysis, r"(?mi)^(?!\s*Insight:)(?![^\n]*\brelationship\s+between\b)[^\n]*?\bannual\s+operating\s+income\s+(?:of|was)\s+\$?([\d,.]+)\s*(million|billion|thousand)?")
            + _percents(core_analysis, r"(?mi)^(?!\s*Insight:)(?![^\n]*\brelationship\s+between\b)[^\n]*?\bannual\s+operating\s+margin\s+(?:was|of)\s+([\d,.]+)%"),
            [float(operating_income.get("value")), float(operating_margin.get("result")) * 100],
            f"{_format_money(float(operating_income.get('value')))}; {float(operating_margin.get('result')) * 100:.4f}%",
            f"{operating_tag}; {operating_margin.get('arithmetic')}",
            [1_000_000, 0.02],
            source_ok=(
                bool(re.search(r"facts\.json:\s*operating_income\b", core_analysis, flags=re.IGNORECASE))
                and bool(re.search(r"calculations\.json:\s*operating_margin\b", core_analysis, flags=re.IGNORECASE))
            )
            or (operating_tag in analysis and _has_arithmetic(analysis)),
        ),
        _mark_values(
            "4. Net income attributable to the company",
            _amounts(core_analysis, r"(?mi)^(?!\s*Insight:)(?![^\n]*\brelationship\s+between\b)[^\n]*?\bannual\s+net\s+income(?:\s+attributable\s+to\s+the\s+company)?\s+(?:of|was)\s+\$?([\d,.]+)\s*(million|billion|thousand)?"),
            [float(net_income.get("value"))],
            _format_money(float(net_income.get("value"))),
            f"{net_income_tag}; period {net_income.get('period_end')}",
            [1_000_000],
            source_ok=bool(re.search(r"facts\.json:\s*net_income\b", core_analysis, flags=re.IGNORECASE))
            or net_income_tag in analysis,
        ),
        _mark_values(
            "5. Diluted earnings per share, GAAP",
            _amounts(core_analysis, r"(?mi)^(?!\s*Insight:)(?![^\n]*\brelationship\s+between\b)[^\n]*?\bannual\s+GAAP\s+diluted\s+(?:earnings per share|EPS)\s+(?:of|was)\s+\$?([\d,.]+)\s*(million|billion|thousand)?"),
            [float(diluted_eps.get("value"))],
            f"${float(diluted_eps.get('value')):.2f}",
            f"{eps_tag}; period {diluted_eps.get('period_end')}{eps_line_evidence}",
            [0.005],
            source_ok=bool(re.search(r"facts\.json:\s*diluted_eps\b", core_analysis, flags=re.IGNORECASE))
            or eps_tag in analysis,
        ),
        _mark_values(
            "6. Return on average equity",
            _percents(core_analysis, r"(?mi)^(?!\s*Insight:)(?![^\n]*\brelationship\s+between\b)[^\n]*?\breturn\s+on\s+average\s+equity\s+(?:was|of)\s+([\d,.]+)%"),
            [float(return_on_equity.get("result")) * 100],
            f"{float(return_on_equity.get('result')) * 100:.4f}%",
            str(return_on_equity.get("arithmetic")),
            [0.02],
            source_ok=bool(
                re.search(r"calculations\.json:\s*return_on_average_equity\b", core_analysis, flags=re.IGNORECASE)
            )
            or "Code-supplied calculation" in analysis
            or _has_arithmetic(analysis),
        ),
        (
            _mark_values(
                "7. Debt to equity, including current debt",
                _ratios(core_analysis, r"(?mi)^(?!\s*Insight:)(?![^\n]*\brelationship\s+between\b)[^\n]*?\bdebt\s+to\s+equity\s+(?:was|of)\s+([\d,.]+)"),
                [float(debt_to_equity.get("result"))],
                f"{float(debt_to_equity.get('result')):.4f}",
                str(debt_to_equity.get("arithmetic")),
                [0.01],
                source_ok=bool(re.search(r"calculations\.json:\s*debt_to_equity\b", core_analysis, flags=re.IGNORECASE))
                or (
                    "Current portion of long-term debt" in analysis
                    and ("Code-supplied calculation" in analysis or _has_arithmetic(analysis))
                ),
            )
            if debt_to_equity.get("result") is not None
            else _mark_unavailable_calculation(
                "7. Debt to equity, including current debt",
                core_analysis,
                r"(?mi)^(?!\s*Insight:)(?![^\n]*\brelationship\s+between\b)[^\n]*?\bdebt\s+to\s+equity\s+(?:was|of)\s+([\d,.]+)",
                r"debt\s+to\s+equity",
                str(debt_to_equity.get("unavailable_reason") or ""),
            )
        ),
        _mark_values(
            "8. Free cash flow",
            _distinct_values(
                _amounts(
                    core_analysis,
                    r"(?mi)^(?!\s*Insight:)(?![^\n]*\brelationship\s+between\b)[^\n]*?\bfree\s+cash\s+flow\s+(?:was|of)\s+\$?([\d,.]+)\s*(million|billion|thousand)?",
                ),
                1_000_000,
            ),
            [float(free_cash_flow.get("result"))],
            _format_money(float(free_cash_flow.get("result"))),
            str(free_cash_flow.get("arithmetic")),
            [1_000_000],
            source_ok=bool(re.search(r"calculations\.json:\s*free_cash_flow\b", core_analysis, flags=re.IGNORECASE))
            or (
                ("Net cash provided by operating activities" in analysis or "Net cash from operations" in analysis)
                and ("Code-supplied calculation" in analysis or _has_arithmetic(analysis))
            ),
        ),
    ]
    if quarter_revenue is not None:
        marks.append(
            _mark_values(
                "9. Latest-quarter revenue",
                _amounts(core_analysis, r"(?mi)^(?!\s*Insight:)(?![^\n]*\brelationship\s+between\b)[^\n]*?(?<!-)quarter\s+total\s+revenue\s+(?:of|was)\s+\$?([\d,.]+)\s*(million|billion|thousand)?"),
                [quarter_revenue],
                _format_money(quarter_revenue),
                revenue_quote,
                [1_000_000],
                source_ok=bool(re.search(r"exhibit-99-1\.txt:\s*\d+", core_analysis, flags=re.IGNORECASE))
                or (("8-K Exhibit 99.1" in analysis or "Exhibit 99.1" in analysis) and "Total revenue" in analysis),
            )
        )
    if quarter_growth is not None:
        marks.append(
            _mark_values(
                "10. Quarter revenue growth versus the same quarter last year",
                _percents(core_analysis, r"(?mi)^(?!\s*Insight:)(?![^\n]*\brelationship\s+between\b)[^\n]*?(?<!-)quarter\s+revenue\s+growth\s+(?:was|of)\s+([\d,.]+)%"),
                [quarter_growth],
                f"{quarter_growth:.4f}%",
                f"({quarter_revenue:g} - {prior_quarter_revenue:g}) / {prior_quarter_revenue:g}",
                [0.02],
                source_ok=bool(
                    re.search(r"calculations\.json:\s*quarter_revenue_growth\b", core_analysis, flags=re.IGNORECASE)
                )
                or "Code-supplied calculation" in analysis
                or _has_arithmetic(analysis),
            )
        )
    if quarter_eps is not None:
        marks.append(
            _mark_values(
                "11. Quarter diluted EPS, GAAP",
                _amounts(core_analysis, r"(?mi)^(?!\s*Insight:)(?![^\n]*\brelationship\s+between\b)[^\n]*?(?<!-)quarter\s+GAAP\s+diluted\s+(?:earnings per share|EPS)\s+(?:of|was)\s+\$?([\d,.]+)\s*(million|billion|thousand)?"),
                [quarter_eps],
                f"${quarter_eps:.2f}",
                eps_quote,
                [0.005],
                source_ok=bool(re.search(r"exhibit-99-1\.txt:\s*\d+", core_analysis, flags=re.IGNORECASE))
                or (
                    ("8-K Exhibit 99.1" in analysis or "Exhibit 99.1" in analysis)
                    and ("per diluted share" in analysis or bool(re.search(r"Diluted\s*\|", analysis, flags=re.IGNORECASE)))
                ),
            )
        )
    display_patterns = {
        "1.": [r"annual\s+total\s+revenue"],
        "2.": [r"annual\s+revenue\s+growth"],
        "3.": [r"annual\s+operating\s+income", r"annual\s+operating\s+margin"],
        "4.": [r"annual\s+net\s+income"],
        "5.": [r"annual\s+GAAP\s+diluted"],
        "6.": [r"return\s+on\s+average\s+equity"],
        "7.": [r"debt\s+to\s+equity"],
        "8.": [r"free\s+cash\s+flow"],
        "9.": [r"quarter\s+total\s+revenue"],
        "10.": [r"quarter\s+revenue\s+growth"],
        "11.": [r"quarter\s+GAAP\s+diluted"],
    }
    for mark in marks:
        prefix = mark.claim.split(" ", 1)[0]
        report_text = _matching_report_lines(core_analysis, display_patterns.get(prefix, []))
        if report_text:
            mark.report_said = report_text
    return marks


def verify_insight_claims(run_folder: Path, report: str) -> list[VerificationMark]:
    """Check each Lab 05 Insight line against the filing lines it cites."""
    marks: list[VerificationMark] = []
    insight_lines = [
        line.strip()
        for line in report.splitlines()
        if line.strip().lower().startswith("insight:")
    ]
    citation_pattern = FILING_CITATION_RE
    calculation_pattern = CALCULATION_CITATION_RE
    faskills_pattern = FASKILLS_CITATION_RE
    calculations = load_json(run_folder / "calculations.json") if (run_folder / "calculations.json").exists() else {}
    facts = load_json(run_folder / "facts.json") if (run_folder / "facts.json").exists() else {}
    faskills = load_json(run_folder / "faskills_metrics.json") if (run_folder / "faskills_metrics.json").exists() else {}
    for index, insight in enumerate(insight_lines, start=1):
        citations = citation_pattern.findall(insight)
        calculation_citations = calculation_pattern.findall(insight)
        faskills_citations = faskills_pattern.findall(insight)
        claim_without_citations = faskills_pattern.sub("", calculation_pattern.sub("", citation_pattern.sub("", insight)))
        reported_mentions = [match.group(0).strip() for match in NUMBER_MENTION_RE.finditer(claim_without_citations)]
        source_lines: list[str] = []
        cited_ranges: list[tuple[str, int, int]] = []
        missing_citation = False
        for filename, line_start_text, line_end_text in citations:
            path = run_folder / filename.lower()
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
            line_start = int(line_start_text)
            line_end = int(line_end_text or line_start_text)
            if not (0 < line_start <= line_end <= len(lines)):
                missing_citation = True
                continue
            cited_ranges.append((filename.lower(), line_start, line_end))
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
        # Vendor-only inputs do not meet the course's SEC reproducibility rule.
        faskills_allowed = False
        for metric_name in faskills_citations:
            metric = faskills.get("metrics", {}).get(metric_name, {})
            if not faskills_allowed or metric.get("validation_status") != "available":
                missing_citation = True
                continue
            result = metric.get("value")
            if not isinstance(result, (int, float)):
                missing_citation = True
                continue
            calculation_numbers.extend([float(result), float(result) * 100])
            calculation_numbers.extend(_numbers(json.dumps(metric.get("inputs", {}))))
            calculation_evidence.append(
                f"FAskills {metric_name}: {metric.get('formula')}; result {float(result):g}; "
                f"period {faskills.get('source_periods', {}).get('current_period')}; "
                f"accession {faskills.get('source_periods', {}).get('current_accession')}"
            )
        evidence_parts = source_lines + calculation_evidence
        revenue_claim = facts.get("earnings_release_extraction", {}).get("claims", {}).get("total_revenue", {})
        revenue_line = revenue_claim.get("source_line_start")
        cites_release_revenue = isinstance(revenue_line, int) and any(
            filename == "exhibit-99-1.txt" and line_start <= revenue_line <= line_end
            for filename, line_start, line_end in cited_ranges
        )
        if cites_release_revenue:
            current_revenue, prior_revenue, _ = _release_quarter_revenues(run_folder, facts)
            if current_revenue is not None and prior_revenue not in {None, 0}:
                quarter_growth_percent = (current_revenue - prior_revenue) / prior_revenue * 100
                calculation_numbers.extend([quarter_growth_percent, quarter_growth_percent / 100])
                calculation_evidence.append(
                    "quarter_revenue_growth: "
                    f"({current_revenue:g} - {prior_revenue:g}) / {prior_revenue:g}; "
                    f"result {quarter_growth_percent:.4f}%"
                )
                evidence_parts = source_lines + calculation_evidence
        evidence = " | ".join(evidence_parts) if evidence_parts else "No valid source citation."
        if not citations or missing_citation or not source_lines:
            mark = "Unsupported"
        else:
            source_numbers = [number for line in source_lines for number in _numbers(line)] + calculation_numbers
            unmatched: list[str] = []
            arithmetic_evidence: list[str] = []
            for mention in reported_mentions:
                number = _number_from_mention(mention)
                if any(
                    _mention_numeric_equivalent(mention, number, source_number)
                    for source_number in source_numbers
                ):
                    continue
                arithmetic = _derived_arithmetic_match(
                    claim_without_citations,
                    mention,
                    number,
                    source_numbers,
                )
                if arithmetic:
                    arithmetic_evidence.append(arithmetic)
                    continue
                unmatched.append(mention)
            mark = "Wrong" if unmatched else "Correct"
            if arithmetic_evidence:
                evidence = "Simple arithmetic from cited inputs: " + "; ".join(arithmetic_evidence) + ". " + evidence
            if unmatched:
                evidence = f"The cited line does not contain or establish: {', '.join(unmatched)}. " + evidence
        marks.append(
            VerificationMark(
                claim=f"Insight {index}",
                report_said=insight.removeprefix("Insight:").strip(),
                filing_says=evidence,
                mark=mark,
                evidence=evidence,
            )
        )
    return marks


def _non_advisor_report_lines(report: str) -> list[tuple[int, str]]:
    """Return substantive report lines, excluding metadata and the Advisor's thesis section."""
    kept: list[tuple[int, str]] = []
    in_advisor = False
    for line_number, line in enumerate(report.splitlines(), start=1):
        stripped = line.strip()
        if re.match(r"^#{1,2}\s+Investment Recommendation\s*$", stripped, flags=re.IGNORECASE):
            in_advisor = True
            continue
        if in_advisor:
            continue
        if line_number <= 2 or not stripped or stripped == "---" or stripped.startswith("#"):
            continue
        if stripped.startswith(("This is a learning exercise", "AI assistance:", "Any remaining errors")):
            continue
        kept.append((line_number, stripped))
    return kept


def _is_core_or_insight_line(line: str) -> bool:
    clean = re.sub(r"^[*_-]+", "", line).strip().lower()
    if clean.startswith("insight:"):
        return True
    return bool(
        re.match(
            r"^(?:annual\s+(?:total\s+revenue|revenue\s+growth|operating\s+income|operating\s+margin|"
            r"net\s+income|gaap\s+diluted)|return\s+on\s+average\s+equity|debt\s+to\s+equity|"
            r"free\s+cash\s+flow|quarter\s+(?:total\s+revenue|revenue\s+growth|gaap\s+diluted))\b",
            clean,
        )
    )


def _appendix_fact_source(run_folder: Path, line: str) -> tuple[list[float], list[str], bool]:
    """Resolve the desk's human-readable XBRL appendix citation format."""
    if PEER_APPENDIX_CITATION_RE.search(line):
        return [], [], False
    tag_match = XBRL_APPENDIX_CITATION_RE.search(line)
    if not tag_match:
        return [], [], False
    facts_path = run_folder / "facts.json"
    if not facts_path.exists():
        return [], ["The XBRL appendix citation cannot be checked because facts.json is absent."], True

    requested_tag = tag_match.group(1).lower()
    requested_periods = set(ISO_DATE_RE.findall(line))
    accession_match = ACCESSION_RE.search(line)
    requested_accession = accession_match.group(0) if accession_match else ""
    facts = load_json(facts_path)
    matches: list[tuple[str, str, dict[str, Any]]] = []
    for concept_name, concept in facts.get("concepts", {}).items():
        if not isinstance(concept, dict):
            continue
        for period_name in ("current", "prior"):
            observation = concept.get(period_name) or {}
            if str(observation.get("xbrl_tag") or "").lower() != requested_tag:
                continue
            if requested_periods and str(observation.get("period_end") or "") not in requested_periods:
                continue
            if requested_accession and str(observation.get("accession_number") or "") != requested_accession:
                continue
            if isinstance(observation.get("value"), (int, float)):
                matches.append((concept_name, period_name, observation))
    if not matches:
        requested = f"tag {tag_match.group(1)}"
        if requested_periods:
            requested += f", periods {sorted(requested_periods)}"
        if requested_accession:
            requested += f", accession {requested_accession}"
        return [], [f"No facts.json observation matches {requested}."], True

    values: list[float] = []
    evidence: list[str] = []
    for concept_name, period_name, observation in matches:
        values.append(float(observation["value"]))
        evidence.append(
            f"facts.json:{concept_name}:{period_name}: {observation['value']}; "
            f"tag {observation.get('xbrl_tag')}; period {observation.get('period_end')}; "
            f"accession {observation.get('accession_number')}"
        )
    return values, evidence, False


def _appendix_peer_source(run_folder: Path, line: str) -> tuple[list[float], list[str], bool]:
    match = PEER_APPENDIX_CITATION_RE.search(line)
    if not match:
        return [], [], False
    peers_path = run_folder / "peers.json"
    if not peers_path.exists():
        return [], ["The peer appendix cannot be checked because peers.json is absent."], True
    ticker = match.group(1).upper()
    peers = load_json(peers_path).get("peers", [])
    peer = next((row for row in peers if str(row.get("ticker") or "").upper() == ticker), None)
    if not peer:
        return [], [f"Peer {ticker} is absent from peers.json."], True
    record = peer.get("operating_margin", {})
    if record.get("validation_status") != "available" or not isinstance(record.get("result"), (int, float)):
        return [], [f"Peer {ticker} operating margin is unavailable."], True
    values = [float(record["result"]), float(record["result"]) * 100]
    values.extend(_numbers(str(record.get("arithmetic") or "")))
    values.extend(_numbers(json.dumps(record.get("inputs", {}))))
    evidence = [
        f"peers.json:{ticker}:operating_margin: {record.get('arithmetic')}; result {float(record['result']):g}; "
        f"period {peer.get('period_end')}; denominator {peer.get('revenue_line_label')}"
    ]
    return values, evidence, False


def _appendix_release_source(run_folder: Path, line: str) -> tuple[list[float], list[str], bool]:
    matches = RELEASE_APPENDIX_CITATION_RE.findall(line)
    if not matches:
        return [], [], False
    path = run_folder / "exhibit-99-1.txt"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
    values: list[float] = []
    evidence: list[str] = []
    invalid = False
    for line_text in matches:
        line_number = int(line_text)
        if not 0 < line_number <= len(lines):
            invalid = True
            evidence.append(f"Invalid citation exhibit-99-1.txt:{line_number}.")
            continue
        source_line = lines[line_number - 1]
        values.extend(_numbers(source_line))
        evidence.append(f"exhibit-99-1.txt:{line_number}: {source_line}")
    return values, evidence, invalid


def _filing_search_correction(
    run_folder: Path,
    report_line: str,
    mention: str,
    value: float,
) -> tuple[str, str] | None:
    """Find a misplaced but real number in the saved filing texts.

    The result is a correction location, not permission to mark the original
    citation Correct. A wrong-line citation remains Unsupported.
    """
    report_words = {
        word.lower()
        for word in re.findall(r"[A-Za-z]{3,}", FILING_CITATION_RE.sub("", report_line))
        if word.lower()
        not in {
            "the", "and", "for", "from", "with", "that", "this", "was", "were",
            "has", "had", "its", "into", "than", "year", "fiscal", "quarter",
            "million", "billion", "thousand", "percent", "basis", "points",
        }
    }
    cited_targets = {
        filename.lower(): int(line_start)
        for filename, line_start, _ in FILING_CITATION_RE.findall(report_line)
    }
    candidates: list[tuple[float, str, int, str]] = []
    for filename in ("10-k.txt", "10-q.txt", "8-k.txt", "exhibit-99-1.txt"):
        path = run_folder / filename
        if not path.exists():
            continue
        for line_number, source_line in enumerate(
            path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
        ):
            source_mentions = [match.group(0).strip() for match in NUMBER_MENTION_RE.finditer(source_line)]
            if not any(
                _mention_numeric_equivalent(source_mention, _number_from_mention(source_mention), value)
                or _mention_numeric_equivalent(mention, value, _number_from_mention(source_mention))
                for source_mention in source_mentions
            ):
                continue
            source_words = {word.lower() for word in re.findall(r"[A-Za-z]{3,}", source_line)}
            overlap = len(report_words & source_words)
            exact_text_bonus = 4.0 if mention.replace("$", "").strip() in source_line else 0.0
            file_bonus = 1.0 if filename in report_line.lower() else 0.0
            cited_line = cited_targets.get(filename)
            proximity_bonus = (
                max(0.0, 8.0 - (abs(line_number - cited_line) / 10.0))
                if cited_line is not None
                else 0.0
            )
            score = float(overlap) + exact_text_bonus + file_bonus + proximity_bonus
            candidates.append((score, filename, line_number, source_line.strip()))
    if not candidates:
        return None
    score, filename, line_number, source_line = max(candidates, key=lambda item: item[0])
    if score < 1.0:
        return None
    location = f"{filename}:{line_number}"
    return location, source_line


def _source_numbers_for_line(run_folder: Path, line: str) -> tuple[list[float], list[str], bool]:
    source_numbers: list[float] = []
    evidence: list[str] = []
    invalid = False
    for filename, start_text, end_text in FILING_CITATION_RE.findall(line):
        path = run_folder / filename.lower()
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.exists() else []
        start = int(start_text)
        end = int(end_text or start_text)
        if not (0 < start <= end <= len(lines)):
            invalid = True
            evidence.append(f"Invalid citation {filename.lower()}:{start}-{end}.")
            continue
        excerpt = lines[start - 1:end]
        source_numbers.extend(number for source_line in excerpt for number in _numbers(source_line))
        evidence.append(f"{filename.lower()}:{start}-{end}: " + " | ".join(excerpt))
    calculations = load_json(run_folder / "calculations.json") if (run_folder / "calculations.json").exists() else {}
    for calculation_name in CALCULATION_CITATION_RE.findall(line):
        calculation = calculations.get("calculations", {}).get(calculation_name, {})
        if calculation.get("validation_status") != "available" or calculation.get("result") is None:
            invalid = True
            evidence.append(f"Calculation {calculation_name} is unavailable.")
            continue
        result = float(calculation["result"])
        source_numbers.extend([result, result * 100])
        source_numbers.extend(_numbers(str(calculation.get("arithmetic") or "")))
        source_numbers.extend(_numbers(json.dumps(calculation.get("inputs", {}))))
        evidence.append(
            f"calculations.json:{calculation_name}: {calculation.get('arithmetic')}; result {result:g}"
        )
    facts = load_json(run_folder / "facts.json") if (run_folder / "facts.json").exists() else {}
    for concept_name, period_name in FACT_CITATION_RE.findall(line):
        period_key = (period_name or "current").lower()
        concept = facts.get("concepts", {}).get(concept_name.lower(), {})
        observation = concept.get(period_key) or {}
        value = observation.get("value")
        if not isinstance(value, (int, float)):
            invalid = True
            evidence.append(f"Fact {concept_name}:{period_key} is unavailable.")
            continue
        source_numbers.append(float(value))
        source_numbers.extend(_numbers(str(observation.get("period_end") or "")))
        evidence.append(
            f"facts.json:{concept_name}:{period_key}: {value}; "
            f"tag {observation.get('xbrl_tag')}; period {observation.get('period_end')}; "
            f"accession {observation.get('accession_number')}"
        )
    peers = load_json(run_folder / "peers.json") if (run_folder / "peers.json").exists() else {}
    peer_rows = {
        str(peer.get("ticker") or "").upper(): peer
        for peer in peers.get("peers", [])
        if isinstance(peer, dict)
    }
    for ticker, measure_name in PEER_CITATION_RE.findall(line):
        peer = peer_rows.get(ticker.upper())
        measure = measure_name.lower()
        if not peer:
            invalid = True
            evidence.append(f"Peer {ticker.upper()} is unavailable.")
            continue
        if measure == "operating_margin":
            record = peer.get("operating_margin", {})
            value = record.get("result")
            if isinstance(value, (int, float)):
                source_numbers.extend([float(value), float(value) * 100])
                source_numbers.extend(_numbers(json.dumps(record.get("inputs", {}))))
                evidence.append(
                    f"peers.json:{ticker.upper()}:operating_margin: {record.get('arithmetic')}; result {float(value):g}; "
                    f"denominator {peer.get('revenue_line_label')}"
                )
                continue
        invalid = True
        evidence.append(f"Peer measure {ticker.upper()}:{measure} is unavailable.")
    manifest = load_json(run_folder / "manifest.json") if (run_folder / "manifest.json").exists() else {}
    arguments = manifest.get("arguments", {})
    for field_name in MANIFEST_CITATION_RE.findall(line):
        value = arguments.get(field_name.lower())
        if value in (None, ""):
            invalid = True
            evidence.append(f"Manifest field {field_name} is unavailable.")
            continue
        source_numbers.extend(_numbers(str(value)))
        evidence.append(f"manifest.json:{field_name.lower()}: {value}")
    appendix_values, appendix_evidence, appendix_invalid = _appendix_fact_source(run_folder, line)
    source_numbers.extend(appendix_values)
    evidence.extend(appendix_evidence)
    invalid = invalid or appendix_invalid
    peer_values, peer_evidence, peer_invalid = _appendix_peer_source(run_folder, line)
    source_numbers.extend(peer_values)
    evidence.extend(peer_evidence)
    invalid = invalid or peer_invalid
    release_values, release_evidence, release_invalid = _appendix_release_source(run_folder, line)
    source_numbers.extend(release_values)
    evidence.extend(release_evidence)
    invalid = invalid or release_invalid
    return source_numbers, evidence, invalid


def verify_all_other_numbers(run_folder: Path, report: str) -> list[VerificationMark]:
    """Verify every non-core number outside the Investment Advisor's thesis.

    Filing lines and deterministic calculations are the only permitted numerical
    sources. Web numbers and vendor-derived FAskills metrics fail closed.
    """
    marks: list[VerificationMark] = []
    for report_line_number, line in _non_advisor_report_lines(report):
        if _is_core_or_insight_line(line):
            continue
        masked = line
        for citation_pattern in _all_permitted_citation_patterns():
            masked = _mask_matches(masked, citation_pattern)
        masked = _mask_matches(masked, FASKILLS_CITATION_RE)
        masked = re.sub(r"https?://[^\s)]+", lambda match: " " * (match.end() - match.start()), masked)
        masked = re.sub(
            r"\b(?:10-K|10-Q|8-K|Exhibit\s+99\.1)\b",
            lambda match: " " * (match.end() - match.start()),
            masked,
            flags=re.IGNORECASE,
        )
        masked = _mask_matches(masked, ISO_DATE_RE)
        masked = _mask_matches(masked, ACCESSION_RE)
        masked = re.sub(
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+(?:19|20)\d{2}\b",
            lambda match: " " * (match.end() - match.start()),
            masked,
            flags=re.IGNORECASE,
        )
        masked = re.sub(
            r"\bCIK\s*:?[ \t]*\d+\b|\b(?:source\s+)?lines?\s+\d+(?:\s*[-–]\s*\d+)?\b",
            lambda match: " " * (match.end() - match.start()),
            masked,
            flags=re.IGNORECASE,
        )
        masked = re.sub(
            r"\bQ[1-4]\b|\b(?:19|20)\d{2}\b",
            lambda match: " " * (match.end() - match.start()),
            masked,
            flags=re.IGNORECASE,
        )
        masked = _mask_numeric_labels(masked)
        masked = re.sub(r"^\s*(?:[-*]\s+|\d+[.)]\s+)", lambda match: " " * (match.end() - match.start()), masked)
        mention_matches = list(NUMBER_MENTION_RE.finditer(masked))
        if not mention_matches:
            continue
        urls = re.findall(r"https?://[^\s)]+", line, flags=re.IGNORECASE)
        has_web_source = any(
            (urlparse(url).hostname or "").lower() not in {"sec.gov", "www.sec.gov"}
            and not (urlparse(url).hostname or "").lower().endswith(".sec.gov")
            for url in urls
        )
        for mention_index, mention_match in enumerate(mention_matches, start=1):
            mention = mention_match.group(0).strip()
            value = _number_from_mention(mention)
            claim = f"Other number L{report_line_number}.{mention_index}"
            next_start = mention_matches[mention_index].start() if mention_index < len(mention_matches) else len(line)
            citation_window = line[mention_match.end():next_start]
            preceding_text = line[:mention_match.start()]
            score_mention = (
                mention in {"1", "2", "3", "4", "5"}
                and bool(re.search(r":\s*\*{0,2}\s*$", preceding_text))
            )
            has_vendor_source = bool(FASKILLS_CITATION_RE.search(citation_window))
            has_permitted_citation = any(
                pattern.search(citation_window) for pattern in _all_permitted_citation_patterns()
            )
            # A dense financial sentence may cite several lines at its end.
            # Match each value against every permitted same-line source rather
            # than assuming the first following token belongs to it.
            source_window = line
            has_permitted_citation = any(
                pattern.search(source_window) for pattern in _all_permitted_citation_patterns()
            )
            source_numbers, evidence_parts, invalid_source = _source_numbers_for_line(run_folder, source_window)
            correction_cache: str | None = None

            def correction_text() -> str:
                nonlocal correction_cache
                if correction_cache is None:
                    correction = _filing_search_correction(run_folder, line, mention, value)
                    correction_cache = (
                        f"Found at {correction[0]}: {correction[1]}"
                        if correction
                        else "Not stated in the saved filings"
                    )
                return correction_cache

            direct_match = has_permitted_citation and not invalid_source and any(
                _mention_numeric_equivalent(
                    (
                        mention + " million"
                        if not re.search(r"%|x|billion|million|thousand|basis point", mention, flags=re.IGNORECASE)
                        and re.search(r"\bmillion\b", line, flags=re.IGNORECASE)
                        else mention
                    ),
                    value,
                    source_value,
                )
                for source_value in source_numbers
            )
            arithmetic = (
                _derived_arithmetic_match(line, mention, value, source_numbers)
                if has_permitted_citation and not invalid_source and not direct_match
                else None
            )
            if score_mention and has_permitted_citation and not invalid_source:
                mark = "Correct"
                evidence = "Analytical score; the cited filing or calculation supplies the evidence used for the score."
                filing_says = "Analytical score, not a filing value"
            elif direct_match:
                mark = "Correct"
                evidence = " | ".join(evidence_parts)
                filing_says = "Matched cited filing or deterministic calculation"
            elif arithmetic:
                mark = "Correct"
                evidence = (
                    f"The cited filing supplies the inputs and the report rounding holds: {arithmetic}. "
                    + " | ".join(evidence_parts)
                )
                filing_says = "Matched simple arithmetic from cited filing inputs"
            elif has_web_source:
                mark = "Unsupported"
                evidence = (
                    "Web numbers are supplementary and are not permitted as report evidence. "
                    + correction_text()
                )
                filing_says = correction_text()
            elif has_vendor_source:
                mark = "Unsupported"
                evidence = (
                    "Vendor-derived FAskills inputs are not fully reproduced from SEC XBRL and cannot support report numbers. "
                    + correction_text()
                )
                filing_says = correction_text()
            elif not has_permitted_citation or invalid_source:
                mark = "Unsupported"
                evidence = "A number with no valid filing-line or deterministic-calculation citation is unsupported."
                if evidence_parts:
                    evidence += " " + " | ".join(evidence_parts)
                evidence += " " + correction_text()
                filing_says = correction_text()
            else:
                mark = "Unsupported"
                evidence = (
                    f"The cited evidence does not state {mention}, and simple arithmetic from the cited inputs "
                    "does not establish it at the report's rounding. "
                    + " | ".join(evidence_parts)
                    + " "
                    + correction_text()
                )
                filing_says = correction_text()
            marks.append(VerificationMark(claim, mention, filing_says, mark, evidence))
    return marks


def cited_line_evidence(run_folder: Path, report: str) -> list[dict[str, Any]]:
    evidence: list[dict[str, Any]] = []
    pattern = re.compile(r"(10-k\.txt|10-q\.txt|8-k\.txt|exhibit-99-1\.txt):\s*(\d+)", re.IGNORECASE)
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


def cited_tavily_evidence(run_folder: Path, report: str) -> list[dict[str, Any]]:
    """Return only saved Tavily sources whose exact URL appears in the report."""
    path = run_folder / "tavily_research.json"
    if not path.exists():
        return []
    record = load_json(path)
    evidence: list[dict[str, Any]] = []
    for result in record.get("results", []):
        if not isinstance(result, dict):
            continue
        url = str(result.get("url") or "")
        if not url or url not in report:
            continue
        evidence.append(
            {
                "title": result.get("title"),
                "url": url,
                "published_date": result.get("published_date"),
                "content": result.get("content"),
                "source_class": result.get("source_class"),
                "filing_evidence": False,
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
    faskills_path = run_folder / "faskills_metrics.json"
    compact_faskills = {
        "status": "blocked from report use",
        "reason": "The vendor-derived inputs are not yet fully reproduced from SEC XBRL facts.",
    } if faskills_path.exists() else {"status": "not present"}
    tavily_path = run_folder / "tavily_research.json"
    tavily = load_json(tavily_path) if tavily_path.exists() else {}
    compact_tavily = {
        "status": "present",
        "query": tavily.get("query"),
        "retrieved_at": tavily.get("retrieved_at"),
        "course_boundary": tavily.get("course_boundary"),
        "cited_results": cited_tavily_evidence(run_folder, report),
    } if tavily else {"status": "not present"}
    return {
        "task": (
            "Check whether each cited line or XBRL fact states the report's number for the stated period and definition. "
            "Use the mark Not in filings when the code mark says Not in filings and the report does not invent a value. "
            "Do not assess the Investment Advisor's thesis. For an Insight line, check its numbers, periods, definitions, "
            "and cited evidence only; do not grade whether its analytical inference is persuasive. "
            "Mark an Insight Correct when its numbers, periods, definitions, and citations are correct, even when the "
            "relationship or implication is the analyst's inference rather than a sentence stated verbatim in a filing. "
            "Every code mark represents one numerical statement outside the Investment Advisor thesis. "
            "Web numbers, vendor-derived metrics, and uncited numbers are Unsupported. Never override those fail-closed marks. "
            "For a qualitative supplementary web claim, check only the saved Tavily excerpt cited by the exact URL. "
            "Never accept Tavily as a replacement for filing evidence. Return JSON only."
        ),
        "compiled_report": report,
        "saved_facts": compact_facts,
        "supplemental_faskills_metrics": compact_faskills,
        "supplemental_tavily_research": compact_tavily,
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
        table.append(
            "The optional model definition review was not run for this offline proof. "
            "The deterministic code marks above are the Checkpoint 2 evidence for exact values and arithmetic."
        )
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
    *,
    output_name: str = "verified_report.md",
) -> tuple[Path, list[VerificationMark], dict[str, Any] | None, dict[str, Any]]:
    run_folder = run_folder.resolve()
    report_path = run_folder / "report.md"
    if not report_path.exists():
        raise FileNotFoundError(f"No report.md in saved run: {run_folder}")
    report = report_path.read_text(encoding="utf-8")
    marks = (
        verify_core_claims(run_folder, report)
        + verify_insight_claims(run_folder, report)
        + verify_all_other_numbers(run_folder, report)
    )
    payload = build_semantic_payload(run_folder, report, marks)
    semantic_review = None
    semantic_raw = ""
    semantic_error = ""
    if semantic_check is not None:
        try:
            semantic_raw = semantic_check(json.dumps(payload, ensure_ascii=False))
            semantic_review = parse_semantic_review(semantic_raw)
        except Exception as exc:
            semantic_error = f"{type(exc).__name__}: {exc}"
    verified_text = render_verified_report(report, marks, semantic_review)
    verified_path = run_folder / output_name
    verified_path.write_text(verified_text, encoding="utf-8")
    suffix = ""
    if output_name != "verified_report.md":
        suffix = "_" + Path(output_name).stem.removeprefix("verified_report_")
    (run_folder / f"verifier_input{suffix}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (run_folder / f"verifier_output{suffix}.json").write_text(
        json.dumps(
            {
                "code_marks": [asdict(mark) for mark in marks],
                "semantic_review": semantic_review,
                "semantic_raw": semantic_raw,
                "semantic_error": semantic_error,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    return verified_path, marks, semantic_review, payload

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

from equity_research_crewai.verifier import (
    _quarter_eps,
    _release_quarter_revenues,
    load_json,
    verify_core_claims,
    verify_insight_claims,
    verify_saved_run,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CLEAN_RUN = REPOSITORY_ROOT / "week02" / "runs" / "COSTCO_WHOLESALE_CORP_NEW_COST_20261102_234708"
NETFLIX_RUN = REPOSITORY_ROOT / "week02" / "runs" / "NETFLIX_INC_NFLX_20261102_202506"


def copy_run(tmp_path: Path, name: str) -> Path:
    destination = tmp_path / name
    shutil.copytree(CLEAN_RUN, destination)
    return destination


def mark_for(marks, prefix: str):
    return next(mark for mark in marks if mark.claim.startswith(prefix))


def test_clean_report_has_all_eleven_core_claims_correct() -> None:
    report = (CLEAN_RUN / "report.md").read_text(encoding="utf-8")
    marks = verify_core_claims(CLEAN_RUN, report)
    assert len(marks) == 11
    assert {mark.mark for mark in marks} == {"Correct"}


def test_repeated_identical_free_cash_flow_is_not_marked_wrong() -> None:
    report = (CLEAN_RUN / "report.md").read_text(encoding="utf-8")
    report = report.replace(
        "Free cash flow was $9,382 million.",
        "Free cash flow was $9,382 million.\n\nDalio lens: positive free cash flow of $9,382 million.",
        1,
    )
    marks = verify_core_claims(CLEAN_RUN, report)
    assert mark_for(marks, "8.").mark == "Correct"


def test_seeded_eps_error_is_wrong_and_corrected(tmp_path: Path) -> None:
    run = copy_run(tmp_path, "seeded_eps")
    report_path = run / "report.md"
    report = report_path.read_text(encoding="utf-8")
    report = report.replace(
        "annual GAAP diluted earnings per share of $20.76",
        "annual GAAP diluted earnings per share of $21.76",
        1,
    )
    report_path.write_text(report, encoding="utf-8")
    _, marks, _, _ = verify_saved_run(run)
    mark = mark_for(marks, "5.")
    assert mark.mark == "Wrong"
    assert mark.report_said == "21.76"
    assert mark.filing_says == "$20.76"


def test_invented_growth_is_wrong(tmp_path: Path) -> None:
    run = copy_run(tmp_path, "invented_growth")
    report_path = run / "report.md"
    report = report_path.read_text(encoding="utf-8")
    insertion = "\nInvented test claim: Annual revenue growth was 14.14%.\n"
    report = re.sub(r"(Annual revenue growth was 10\.14%\.)", r"\1" + insertion, report, count=1)
    report_path.write_text(report, encoding="utf-8")
    _, marks, _, _ = verify_saved_run(run)
    assert mark_for(marks, "2.").mark == "Wrong"


def test_verified_report_keeps_filings_line_first(tmp_path: Path) -> None:
    run = copy_run(tmp_path, "clean")
    original_first = (run / "report.md").read_text(encoding="utf-8").splitlines()[0]
    verified_path, _, _, _ = verify_saved_run(run)
    verified = verified_path.read_text(encoding="utf-8")
    assert verified.splitlines()[0] == original_first
    assert "## Verifier marks" in verified


def test_sentence_period_after_eps_is_not_parsed_as_part_of_number() -> None:
    report = (CLEAN_RUN / "report.md").read_text(encoding="utf-8")
    report = report.replace(
        "annual GAAP diluted earnings per share of $20.76 for",
        "annual GAAP diluted EPS was $20.76. The period was",
        1,
    )
    marks = verify_core_claims(CLEAN_RUN, report)
    assert mark_for(marks, "5.").mark == "Correct"


def test_plain_arithmetic_label_and_attributable_net_income_word_order() -> None:
    report = (CLEAN_RUN / "report.md").read_text(encoding="utf-8")
    report = report.replace("**Formula:**", "Arithmetic:")
    report = report.replace(
        "annual net income of $9,226 million",
        "annual net income attributable to the company was $9,226 million",
        1,
    )
    marks = verify_core_claims(CLEAN_RUN, report)
    assert {mark.mark for mark in marks} == {"Correct"}


def test_insight_number_is_checked_against_its_cited_line() -> None:
    correct = "Insight: Annual GAAP diluted EPS was $20.76. (10-k.txt:1294)"
    wrong = "Insight: Annual GAAP diluted EPS was $21.76. (10-k.txt:1294)"
    correct_marks = verify_insight_claims(CLEAN_RUN, correct)
    wrong_marks = verify_insight_claims(CLEAN_RUN, wrong)
    assert correct_marks[0].mark == "Correct"
    assert wrong_marks[0].mark == "Wrong"


def test_insight_accepts_line_range_and_code_calculation() -> None:
    insight = (
        "Insight: Total revenue was $95,723 million and the FY-EPS P/E was 47.7905x. "
        "(exhibit-99-1.txt:37-39) (calculations.json:price_to_earnings)"
    )
    marks = verify_insight_claims(CLEAN_RUN, insight)
    assert marks[0].mark == "Correct"


def test_insight_accepts_code_computed_quarter_growth_from_cited_release_row() -> None:
    insight = (
        "Insight: Current-quarter revenue growth was 11.10% (exhibit-99-1.txt:39), "
        "compared with latest-fiscal-year revenue growth of 10.14% "
        "(calculations.json:revenue_growth)."
    )
    marks = verify_insight_claims(CLEAN_RUN, insight)
    assert marks[0].mark == "Correct"


def test_unavailable_debt_to_equity_does_not_crash_or_invent_zero(tmp_path: Path) -> None:
    run = copy_run(tmp_path, "unavailable_debt")
    calculations_path = run / "calculations.json"
    calculations = json.loads(calculations_path.read_text(encoding="utf-8"))
    calculations["calculations"]["debt_to_equity"].update(
        {
            "inputs": {},
            "arithmetic": "",
            "result": None,
            "validation_status": "unavailable",
            "unavailable_reason": "The current portion of long-term debt is not stated in the supplied facts.",
        }
    )
    calculations_path.write_text(json.dumps(calculations), encoding="utf-8")
    report_path = run / "report.md"
    report = report_path.read_text(encoding="utf-8")
    report = re.sub(
        r"Debt to equity was 0\.17[^\n]*",
        "Debt to equity was not stated in the filings because the current debt input is unavailable.",
        report,
        count=1,
        flags=re.IGNORECASE,
    )
    marks = verify_core_claims(run, report)
    mark = mark_for(marks, "7.")
    assert mark.mark == "Not in filings"
    assert mark.report_said.lower().startswith("debt to equity")


def test_number_for_unavailable_debt_to_equity_is_unsupported(tmp_path: Path) -> None:
    run = copy_run(tmp_path, "invented_debt")
    calculations_path = run / "calculations.json"
    calculations = json.loads(calculations_path.read_text(encoding="utf-8"))
    calculations["calculations"]["debt_to_equity"].update(
        {
            "inputs": {},
            "arithmetic": "",
            "result": None,
            "validation_status": "unavailable",
            "unavailable_reason": "The current portion of long-term debt is not stated in the supplied facts.",
        }
    )
    calculations_path.write_text(json.dumps(calculations), encoding="utf-8")
    marks = verify_core_claims(run, (run / "report.md").read_text(encoding="utf-8"))
    assert mark_for(marks, "7.").mark == "Unsupported"


def test_release_parser_uses_same_quarter_and_table_units() -> None:
    facts = load_json(NETFLIX_RUN / "facts.json")
    current, prior, _ = _release_quarter_revenues(NETFLIX_RUN, facts)
    eps, _ = _quarter_eps(facts)
    assert current == 12_874_176_000
    assert prior == 11_510_307_000
    assert eps == 0.87

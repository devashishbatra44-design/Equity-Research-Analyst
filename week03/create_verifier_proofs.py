"""Create four purpose-built Lab 04 verifier fixtures.

These folders test known answers. They are not graph-produced reports and are
not submission artifacts.
"""

from __future__ import annotations

import re
import shutil
import sys
from collections import Counter
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "equity_research_crewai" / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from equity_research_crewai.verifier import verify_saved_run  # noqa: E402


SOURCE_RUN = (
    REPOSITORY_ROOT
    / "week03"
    / "runs"
    / "COSTCO_WHOLESALE_CORP_NEW_COST_20261109_020525_RECONCILED_20261109_151446"
)
OUTPUT_ROOT = REPOSITORY_ROOT / "week03" / "verification_tests"
FILES = (
    "10-k.txt",
    "10-q.txt",
    "8-k.txt",
    "exhibit-99-1.txt",
    "facts.json",
    "calculations.json",
    "peers.json",
    "filings.json",
    "manifest.json",
    "report.md",
)


def copy_source(name: str) -> Path:
    destination = OUTPUT_ROOT / name
    destination.mkdir(parents=True, exist_ok=True)
    for filename in FILES:
        shutil.copy2(SOURCE_RUN / filename, destination / filename)
    return destination


def main() -> None:
    clean = copy_source("clean_report")
    seeded = copy_source("seeded_eps_error")
    invented = copy_source("invented_growth_error")
    unsupported = copy_source("web_and_unsourced_numbers")

    seeded_report = (seeded / "report.md").read_text(encoding="utf-8")
    seeded_report = seeded_report.replace(
        "Annual GAAP diluted EPS was $20.76",
        "Annual GAAP diluted EPS was $21.76",
        1,
    )
    (seeded / "report.md").write_text(seeded_report, encoding="utf-8")

    invented_report = (invented / "report.md").read_text(encoding="utf-8")
    invented_report = invented_report.replace("Annual revenue growth was 10.1437%", "Annual revenue growth was 14.14%", 1)
    (invented / "report.md").write_text(invented_report, encoding="utf-8")

    unsupported_report = (unsupported / "report.md").read_text(encoding="utf-8")
    unsupported_claims = (
        "\nWeb-sourced test claim: Executive memberships grew 9.6% to 35.4 million "
        "([Yahoo](https://finance.yahoo.com/example)).\n\n"
        "Unsourced test claim: An uncited operating KPI improved 7.5%.\n"
    )
    unsupported_report = unsupported_report.replace(
        "# Investment Recommendation",
        unsupported_claims + "\n# Investment Recommendation",
        1,
    )
    (unsupported / "report.md").write_text(unsupported_report, encoding="utf-8")

    proof_marks = {}
    for folder in (clean, seeded, invented, unsupported):
        verified_path, marks, _, _ = verify_saved_run(folder)
        proof_marks[folder.name] = marks
        print(f"{folder.name}: {dict(Counter(mark.mark for mark in marks))}")
        print(f"Saved: {verified_path}")

    assert {mark.mark for mark in proof_marks["clean_report"]} == {"Correct"}
    assert any(mark.claim.startswith("5.") and mark.mark == "Wrong" for mark in proof_marks["seeded_eps_error"])
    assert any("14.14%" in mark.report_said and mark.mark == "Wrong" for mark in proof_marks["invented_growth_error"])
    unsupported_values = {
        mark.report_said
        for mark in proof_marks["web_and_unsourced_numbers"]
        if mark.mark == "Unsupported"
    }
    assert {"9.6%", "35.4 million", "7.5%"}.issubset(unsupported_values)


if __name__ == "__main__":
    main()

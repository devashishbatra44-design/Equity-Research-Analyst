"""Create the three Lab 04 verifier proof folders from the reviewed saved run."""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "equity_research_crewai" / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from equity_research_crewai.verifier import verify_saved_run  # noqa: E402


SOURCE_RUN = REPOSITORY_ROOT / "week02" / "runs" / "COSTCO_WHOLESALE_CORP_NEW_COST_20261102_234708"
OUTPUT_ROOT = REPOSITORY_ROOT / "week03" / "verification_tests"
FILES = (
    "10-k.txt",
    "10-q.txt",
    "8-k.txt",
    "exhibit-99-1.txt",
    "facts.json",
    "calculations.json",
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

    seeded_report = (seeded / "report.md").read_text(encoding="utf-8")
    seeded_report = seeded_report.replace(
        "annual GAAP diluted earnings per share of $20.76",
        "annual GAAP diluted earnings per share of $21.76",
        1,
    )
    seeded_report = seeded_report.replace(
        '**Filing Line:** "Diluted"',
        '**Filing Line:** "Diluted — $21.76"',
        1,
    )
    (seeded / "report.md").write_text(seeded_report, encoding="utf-8")

    invented_report = (invented / "report.md").read_text(encoding="utf-8")
    invented_report = re.sub(
        r"(Annual revenue growth was 10\.14%\.)",
        r"\1\n\nInvented test claim: Annual revenue growth was 14.14%.",
        invented_report,
        count=1,
    )
    (invented / "report.md").write_text(invented_report, encoding="utf-8")

    for folder in (clean, seeded, invented):
        verified_path, marks, _, _ = verify_saved_run(folder)
        summary = ", ".join(f"{mark.claim.split('.')[0]}={mark.mark}" for mark in marks)
        print(f"{folder.name}: {summary}")
        print(f"Saved: {verified_path}")


if __name__ == "__main__":
    main()

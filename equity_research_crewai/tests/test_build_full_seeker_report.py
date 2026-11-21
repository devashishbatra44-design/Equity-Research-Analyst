from __future__ import annotations

import json
from pathlib import Path

from equity_research_crewai.build_full_seeker_report import build_results
from equity_research_crewai.spinoff_seeker import FINAL_LINE


ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "week04" / "runs" / "seeker_20261119_full"


def _load(name: str) -> dict[str, object]:
    return json.loads((RUN / name).read_text(encoding="utf-8"))


def test_full_report_joins_every_audited_distribution() -> None:
    results, report = build_results(
        _load("registry.json"),
        _load("official_close_f1_audit.json"),
        _load("sec_f2_audit.json"),
        _load("form4_f3_audit.json"),
        ROOT / "week04" / "HUMAN_FACTORS.md",
    )
    assert len(results) == 20
    assert sum(result.total_points is not None for result in results) == 10
    assert sum(result.total_points is None and result.entry.is_spinoff for result in results) == 9
    assert sum(not result.entry.is_spinoff for result in results) == 1
    assert report.splitlines()[0] == (
        "Run date: 2026-11-19 | Price date: per-entry first regular close | Index date: 2026-11-19"
    )
    assert report.splitlines()[-1] == FINAL_LINE
    assert "Versant Media Group, Inc." in report
    assert "PIMCO Asset-Based Lending Company LLC" in report

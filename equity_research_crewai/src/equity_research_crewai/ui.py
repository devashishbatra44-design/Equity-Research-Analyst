"""Streamlit page for the fixed-order equity-research agent team."""

from __future__ import annotations

import subprocess
import sys
import shutil
from datetime import date
from pathlib import Path

import streamlit as st


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[2]
WEEK4_FACTOR_BASELINE = REPOSITORY_ROOT / "week04/OWNED_FACTOR_CHECK_BASELINE.md"


def _latest(pattern: str) -> Path | None:
    matches = sorted(REPOSITORY_ROOT.glob(pattern), key=lambda path: path.stat().st_mtime)
    return matches[-1] if matches else None


def _run_command(command: list[str]) -> None:
    subprocess.run(command, cwd=REPOSITORY_ROOT, check=True)


def _refresh_seeker(start_date: date, end_date: date) -> Path:
    source_report = _latest("week04/runs/seeker_*/report.md")
    if source_report is None:
        raise RuntimeError("No saved seeker registry is available.")
    source = source_report.parent
    output = REPOSITORY_ROOT / "week04" / "runs" / f"seeker_{end_date:%Y%m%d}_ui"
    output.mkdir(parents=True, exist_ok=True)
    for name in ("registry.json", "f2_filing_evidence.json"):
        shutil.copy2(source / name, output / name)
    python = sys.executable
    module = [python, "-m"]
    _run_command(module + ["equity_research_crewai.sec_spinoff_discovery", "--start", start_date.isoformat(), "--end", end_date.isoformat(), "--output", str(output / "sec_form10_cert_candidates.json")])
    _run_command(module + ["equity_research_crewai.sec_form10_text_screen", "--input", str(output / "sec_form10_cert_candidates.json"), "--output", str(output / "form10_text_screen.json")])
    _run_command(module + ["equity_research_crewai.official_close_f1_audit", "--registry", str(output / "registry.json"), "--output", str(output / "official_close_f1_audit.json")])
    _run_command(module + ["equity_research_crewai.sec_f2_audit", "--input", str(output / "f2_filing_evidence.json"), "--output", str(output / "sec_f2_audit.json")])
    _run_command(module + ["equity_research_crewai.sec_form4_audit", "--registry", str(output / "registry.json"), "--output", str(output / "form4_f3_audit.json")])
    _run_command(module + ["equity_research_crewai.build_full_seeker_report", "--registry", str(output / "registry.json"), "--f1", str(output / "official_close_f1_audit.json"), "--f2", str(output / "sec_f2_audit.json"), "--f3", str(output / "form4_f3_audit.json"), "--form10-screen", str(output / "form10_text_screen.json"), "--human-factors", str(REPOSITORY_ROOT / "week04/HUMAN_FACTORS.md"), "--report-output", str(output / "report.md"), "--evidence-output", str(output / "evidence.md")])
    return output / "report.md"


def main() -> None:
    st.set_page_config(page_title="Verified Equity-Research Desk", layout="wide")
    st.title("Verified Equity-Research Desk")
    st.caption("The fixed graph always runs the Steps, three analyst roles, Strategy Manager, and Verifier.")

    with st.expander("Week 4 seeker and investor worksheet"):
        start_date = st.date_input("Distribution start date", value=date(2025, 11, 19))
        end_date = st.date_input("Index date", value=date.today())
        if st.button("Run seeker from start date"):
            if end_date < start_date:
                st.error("The index date must be on or after the start date.")
            else:
                with st.spinner("Refreshing SEC census, factors, prices, and report"):
                    try:
                        refreshed = _refresh_seeker(start_date, end_date)
                    except (OSError, subprocess.CalledProcessError, RuntimeError) as exc:
                        st.error(f"Seeker refresh failed: {exc}")
                    else:
                        st.success(f"Saved {refreshed.relative_to(REPOSITORY_ROOT)}")
        seeker_report = _latest("week04/runs/seeker_*/report.md")
        worksheet_report = _latest("week04/runs/worksheet_*/worksheet.md")
        seeker_column, worksheet_column, factor_column = st.columns(3)
        with seeker_column:
            st.subheader("Spinoff seeker")
            if seeker_report is not None:
                st.markdown(seeker_report.read_text(encoding="utf-8"))
            else:
                st.warning("The saved Week 4 seeker report is not available.")
        with worksheet_column:
            st.subheader("Latest investor worksheet")
            if worksheet_report is not None:
                st.markdown(worksheet_report.read_text(encoding="utf-8"))
                desk_report = next(iter(sorted(worksheet_report.parent.glob("verified_report*.md"))), None)
                if desk_report is not None:
                    st.subheader("Desk report")
                    st.markdown(desk_report.read_text(encoding="utf-8"))
                else:
                    st.info("No desk report is saved beside this worksheet.")
            else:
                st.warning("The saved Week 4 worksheet is not available.")
        with factor_column:
            st.subheader("Owned factor check")
            if WEEK4_FACTOR_BASELINE.exists():
                st.markdown(WEEK4_FACTOR_BASELINE.read_text(encoding="utf-8"))
            else:
                st.warning("The frozen factor-check baseline is not available.")

    ticker = st.text_input("Ticker").strip().upper()
    peers = st.text_input("Peers (comma-separated)").strip().upper()
    price = st.number_input("Closing price", min_value=0.0, value=0.0, step=0.01)
    price_date = st.text_input("Closing-price date (YYYY-MM-DD)").strip()
    price_source = st.text_input("Price source (exchange or LSEG)").strip()
    use_faskills = st.checkbox(
        "Run the course-safe FAskills methodology",
        help=(
            "Uses one Financial Datasets API request, applies all nine source-bounded analytical lenses through the three course personas, "
            "and saves the DRIVER trace plus audited metrics."
        ),
    )
    use_tavily = st.checkbox(
        "Add supplementary Tavily web research",
        help=(
            "Runs one focused Tavily search. Web results go only to the Research Analyst and cannot replace SEC evidence."
        ),
    )
    tavily_depth = st.selectbox(
        "Tavily search depth",
        options=("advanced", "basic"),
        help="Advanced uses 2 Tavily credits. Basic uses 1 Tavily credit.",
        disabled=not use_tavily,
    )

    if st.button("Run agent team", type="primary"):
        if not ticker or price <= 0 or not price_date or not price_source:
            st.error("Enter a ticker, a positive price, the price date, and the price source.")
            return
        command = [
            sys.executable,
            "-m",
            "equity_research_crewai.main",
            ticker,
            "--peers",
            peers,
            "--price",
            str(price),
            "--price-date",
            price_date,
            "--price-source",
            price_source,
        ]
        if use_faskills:
            command.append("--faskills")
        if use_tavily:
            command.extend(["--tavily", "--tavily-depth", tavily_depth])
        status = st.status("Starting fixed graph", expanded=True)
        output_box = st.empty()
        lines: list[str] = []
        process = subprocess.Popen(
            command,
            cwd=REPOSITORY_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert process.stdout is not None
        verified_path: Path | None = None
        for line in process.stdout:
            clean = line.rstrip()
            lines.append(clean)
            output_box.code("\n".join(lines[-60:]))
            if clean.startswith("Node: "):
                status.write(clean)
            if clean.startswith("Verified report saved: "):
                verified_path = Path(clean.split(": ", 1)[1])
        return_code = process.wait()
        if return_code:
            status.update(label="Run failed", state="error")
            return
        status.update(label="Run complete; the Verifier ran", state="complete")
        if verified_path and verified_path.exists():
            st.markdown(verified_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()

"""Streamlit page for the fixed-order equity-research agent team."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import streamlit as st


PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[2]


def main() -> None:
    st.set_page_config(page_title="Verified Equity-Research Desk", layout="wide")
    st.title("Verified Equity-Research Desk")
    st.caption("The fixed graph always runs the Steps, three analyst roles, Strategy Manager, and Verifier.")

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

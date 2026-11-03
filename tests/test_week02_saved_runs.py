import json
import math
import re
from pathlib import Path

import pytest

from week02.desk_app import read_run_context


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = PROJECT_ROOT / "week02" / "runs"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def latest_successful_run(ticker: str) -> Path:
    candidates = []
    for manifest_path in RUNS_ROOT.glob("*/manifest.json"):
        manifest = load_json(manifest_path)
        if manifest.get("main_ticker") == ticker and manifest.get("run_status") == "success":
            candidates.append((manifest.get("local_run_time", ""), manifest_path.parent))
    assert candidates, f"No successful saved run exists for {ticker}."
    return max(candidates)[1]


def test_desk_and_role_sources_do_not_name_a_company():
    sources = [PROJECT_ROOT / "week02" / "desk_steps.py", PROJECT_ROOT / "week02" / "desk_app.py"]
    sources.extend(sorted((PROJECT_ROOT / "week02" / "roles").glob("*.md")))
    prohibited = ("COST", "WMT", "TGT", "BJ", "AAPL", "BDC", "NFLX", "Costco", "Walmart", "Target", "Apple", "Belden", "Netflix")
    for source in sources:
        text = source.read_text(encoding="utf-8")
        for name in prohibited:
            assert not re.search(rf"(?<![A-Za-z0-9]){re.escape(name)}(?![A-Za-z0-9])", text, re.IGNORECASE), (
                f"{source.relative_to(PROJECT_ROOT)} names {name}."
            )


def test_saved_cost_run_periods_revenue_definition_and_ratios():
    run_folder = latest_successful_run("COST")
    facts = load_json(run_folder / "facts.json")
    calculations = load_json(run_folder / "calculations.json")["calculations"]
    fiscal_year_end = facts["reference_fiscal_year"]["period_end"]

    for concept in facts["concepts"].values():
        current = concept.get("current")
        if current:
            assert current["period_end"] == fiscal_year_end

    revenue = facts["concepts"]["total_revenue"]
    assert revenue["selected_tag"].startswith("us-gaap:")
    release_line = facts["earnings_release_extraction"]["claims"]["total_revenue"]["quoted_source_text"]
    release_values = [float(value.replace(",", "")) for value in re.findall(r"\d[\d,]*", release_line)]
    assert revenue["current"]["value"] / 1_000_000 in release_values

    expected = {
        "revenue_growth": lambda x: (x["current_revenue"] - x["prior_revenue"]) / x["prior_revenue"],
        "operating_margin": lambda x: x["operating_income"] / x["total_revenue"],
        "return_on_average_equity": lambda x: x["net_income"] / ((x["current_equity"] + x["prior_equity"]) / 2),
        "debt_to_equity": lambda x: (x["long_term_debt"] + x["current_portion"]) / x["stockholders_equity"],
        "free_cash_flow": lambda x: x["cash_from_operations"] - x["property_equipment_additions_as_positive_expenditure"],
        "price_to_earnings": lambda x: x["share_price"] / x["diluted_eps"],
    }
    for key, formula in expected.items():
        item = calculations[key]
        assert item["validation_status"] == "available"
        assert math.isclose(item["result"], formula(item["inputs"]), rel_tol=1e-12, abs_tol=1e-12)


def test_saved_cost_release_extraction_and_peers_succeeded():
    run_folder = latest_successful_run("COST")
    facts = load_json(run_folder / "facts.json")
    peers = load_json(run_folder / "peers.json")
    claims = facts["earnings_release_extraction"]["claims"]
    assert claims["total_revenue"]["status"] == "found"
    assert claims["diluted_eps"]["status"] == "found"
    assert peers["peers"]
    assert all(peer["status"] == "success" for peer in peers["peers"])


def test_saved_cost_quarter_revenue_growth_uses_comparable_fiscal_dates():
    run_folder = latest_successful_run("COST")
    if not (run_folder / "10-k.txt").exists():
        pytest.skip("Downloaded SEC filing text is intentionally excluded from Git.")
    growth = read_run_context(run_folder)["quarterly_release_claims"]["quarter_revenue_growth"]
    assert growth["current_quarter_revenue_thousands"] == 95_723
    assert growth["prior_year_same_quarter_revenue_thousands"] == 86_156
    assert growth["formula"] == "(95,723 - 86,156) / 86,156"
    assert math.isclose(growth["result_percent"], 11.1043, abs_tol=0.0001)

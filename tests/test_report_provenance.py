import json
from pathlib import Path

from week02.desk_app import render_report_text, report_body_from_role_outputs


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = PROJECT_ROOT / "week02" / "runs"

FINAL_RUNS = (
    "COSTCO_WHOLESALE_CORP_NEW_COST_20261102_234708",
    "Apple_Inc_AAPL_20261102_184430",
    "BELDEN_INC_BDC_20261102_233949",
    "NETFLIX_INC_NFLX_20261102_202506",
)


def test_final_reports_match_saved_role_outputs():
    for name in FINAL_RUNS:
        run_folder = RUNS_ROOT / name
        actual = (run_folder / "report.md").read_text(encoding="utf-8")
        header = "\n".join(actual.splitlines()[:2])
        outputs = json.loads((run_folder / "role_outputs.json").read_text(encoding="utf-8"))
        expected = render_report_text(header, report_body_from_role_outputs(outputs))
        assert actual == expected, f"{name}/report.md differs from saved role outputs."

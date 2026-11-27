#!/usr/bin/env python3
"""Copy each saved run (including its original report.md) into a separate dated
folder and rerun only the deterministic Verifier there. Compare code marks with
the original saved verifier output. Original folders are read-only."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--replay-root", type=Path, required=True)
    p.add_argument("pairs", nargs="+", help="RUN_FOLDER=ORIGINAL_VERIFIER_OUTPUT_JSON")
    a = p.parse_args()
    repo = a.repo.resolve()
    sys.path[:0] = [str(repo), str(repo / "week02"), str(repo / "equity_research_crewai" / "src")]
    from equity_research_crewai.verifier import verify_saved_run

    rows, ok = [], True
    for pair in a.pairs:
        folder, original_json = pair.split("=", 1)
        src = (repo / folder).resolve()
        ticker = json.loads((src / "manifest.json").read_text(encoding="utf-8"))["main_ticker"]
        stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        dest = a.replay_root.resolve() / f"{ticker}_{stamp}_reverify"
        shutil.copytree(src, dest)
        verified, marks, _, _ = verify_saved_run(dest, None, output_name="verified_report_replay.md")
        new = json.loads((dest / "verifier_output_replay.json").read_text(encoding="utf-8"))["code_marks"]
        old = json.loads((src / original_json).read_text(encoding="utf-8"))["code_marks"]
        diffs = [i for i, (x, y) in enumerate(zip(old, new)) if x != y]
        row = {
            "ticker": ticker,
            "original_folder": folder,
            "replay_folder": str(dest),
            "report_sha256_original": sha256(src / "report.md"),
            "report_sha256_replay_folder": sha256(dest / "report.md"),
            "original_verifier_output": original_json,
            "original_verifier_output_sha256": sha256(src / original_json),
            "replay_verifier_output_sha256": sha256(dest / "verifier_output_replay.json"),
            "replay_verified_report_sha256": sha256(verified),
            "mark_count_original": len(old),
            "mark_count_replay": len(new),
            "code_marks_identical": old == new,
            "differing_mark_indexes": diffs,
            "differences": [{"index": i, "claim": old[i]["claim"], "original_mark": old[i]["mark"],
                             "replay_mark": new[i]["mark"],
                             "original_filing_says": old[i]["filing_says"][:200],
                             "replay_filing_says": new[i]["filing_says"][:200]} for i in diffs],
        }
        ok &= row["code_marks_identical"]
        rows.append(row)
    print(json.dumps(rows, indent=2, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Check or restore report provenance from saved model role outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from week02.desk_app import render_report_text, report_body_from_role_outputs
except ModuleNotFoundError:  # Support: python week02/report_provenance.py RUN_FOLDER
    from desk_app import render_report_text, report_body_from_role_outputs


def expected_report(run_folder: Path) -> str:
    current = (run_folder / "report.md").read_text(encoding="utf-8")
    header_lines = current.splitlines()[:2]
    if len(header_lines) != 2 or not header_lines[0].startswith("# ") or not header_lines[1].startswith("# Run time:"):
        raise RuntimeError(f"{run_folder}/report.md does not have the required two-line header.")
    outputs = json.loads((run_folder / "role_outputs.json").read_text(encoding="utf-8"))
    return render_report_text("\n".join(header_lines), report_body_from_role_outputs(outputs))


def restore_report(run_folder: Path) -> bool:
    report_path = run_folder / "report.md"
    current = report_path.read_text(encoding="utf-8")
    expected = expected_report(run_folder)
    if current == expected:
        return False
    notes_path = run_folder / "student_notes.md"
    if not notes_path.exists():
        notes_path.write_text(
            "# Student analysis notes — not desk output\n\n"
            "This file archives the manually edited report that previously occupied `report.md`. "
            "It is not model output. It is not the report used for the provenance audit.\n\n"
            + current,
            encoding="utf-8",
        )
    report_path.write_text(expected, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_folders", nargs="+", type=Path)
    parser.add_argument("--restore", action="store_true", help="Archive edited text and restore report.md")
    args = parser.parse_args()
    failed = False
    for folder in args.run_folders:
        report_path = folder / "report.md"
        if not report_path.exists() or not (folder / "role_outputs.json").exists():
            raise RuntimeError(f"{folder} must contain report.md and role_outputs.json.")
        matches = report_path.read_text(encoding="utf-8") == expected_report(folder)
        if matches:
            print(f"PASS {folder}: report matches saved role outputs")
        elif args.restore:
            restore_report(folder)
            print(f"RESTORED {folder}: edited text archived in student_notes.md")
        else:
            print(f"FAIL {folder}: report differs from saved role outputs")
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())

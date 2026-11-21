"""Reduce an SEC Form 10 index to filing-text spinoff candidates."""

from __future__ import annotations

import argparse
import html
import json
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from .sec_spinoff_discovery import SecClient, _sec_user_agent_from_env_file


SPIN_PATTERN = re.compile(r"\b(?:spin[ -]?off|separation)\b", re.IGNORECASE)
DISTRIBUTION_PATTERN = re.compile(
    r"\bdistribution\b.{0,120}\b(?:shares|common stock|stockholders?|shareholders?)\b",
    re.IGNORECASE,
)
PARENT_PATTERN = re.compile(r"\bparent(?: company)?\b", re.IGNORECASE)


def filing_text(raw: str) -> str:
    """Return normalized searchable text from an EDGAR complete-submission file."""

    without_tags = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


def evidence_snippets(text: str, *, limit: int = 5, radius: int = 220) -> tuple[str, ...]:
    """Return bounded text around spinoff and distribution terms."""

    matches = sorted(
        [*SPIN_PATTERN.finditer(text), *DISTRIBUTION_PATTERN.finditer(text)],
        key=lambda match: match.start(),
    )
    snippets: list[str] = []
    for match in matches:
        start = max(0, match.start() - radius)
        end = min(len(text), match.end() + radius)
        snippet = text[start:end].strip()
        if snippet not in snippets:
            snippets.append(snippet)
        if len(snippets) == limit:
            break
    return tuple(snippets)


def select_latest_form10_rows(filings: Sequence[Mapping[str, Any]]) -> tuple[Mapping[str, Any], ...]:
    """Select the latest Form 10 row for every registrant CIK."""

    by_cik: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in filings:
        if str(row.get("form", "")).startswith("10-"):
            by_cik[str(row["cik"])].append(row)
    return tuple(
        max(rows, key=lambda row: (str(row["filed_date"]), str(row["accession"])))
        for _cik, rows in sorted(by_cik.items())
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Screen latest Form 10 filing text for spinoff terms.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    return parser


def _payload(input_path: Path, registrants: Sequence[Mapping[str, Any]], total: int) -> dict[str, Any]:
    return {
        "source_index": str(input_path),
        "method": "latest Form 10 per CIK; filing-text term screen; every candidate requires filing review",
        "registrant_count": total,
        "reviewed_count": len(registrants),
        "candidate_count": sum(row.get("candidate") is True for row in registrants),
        "error_count": sum(bool(row.get("error")) for row in registrants),
        "registrants": list(registrants),
    }


def _save(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    args = build_parser().parse_args()
    source = json.loads(args.input.read_text(encoding="utf-8"))
    rows = select_latest_form10_rows(source["filings"])
    client = SecClient(_sec_user_agent_from_env_file(args.env_file))
    screened: list[dict[str, Any]] = []
    if args.output.exists():
        prior = json.loads(args.output.read_text(encoding="utf-8"))
        screened = list(prior.get("registrants", []))
    completed = {str(row["cik"]) for row in screened if not row.get("error")}
    for number, row in enumerate(rows, start=1):
        if str(row["cik"]) in completed:
            continue
        raw: str | None = None
        error: Exception | None = None
        for attempt in range(1, 4):
            try:
                raw = client.get_text(str(row["filing_url"]))
                error = None
                break
            except Exception as exc:  # keep a reviewable unresolved row after bounded retries
                error = exc
                if attempt < 3:
                    time.sleep(attempt)
        screened = [item for item in screened if str(item["cik"]) != str(row["cik"])]
        if raw is None:
            screened.append(
                {
                    **row,
                    "spin_term_count": None,
                    "distribution_term_count": None,
                    "parent_term_count": None,
                    "candidate": None,
                    "snippets": [],
                    "error": f"{type(error).__name__}: {error}",
                }
            )
            print(f"Unresolved after 3 attempts: {row['cik']} {row['company_name']}", flush=True)
            _save(args.output, _payload(args.input, screened, len(rows)))
            continue
        text = filing_text(raw)
        spin_matches = len(SPIN_PATTERN.findall(text))
        distribution_matches = len(DISTRIBUTION_PATTERN.findall(text))
        parent_matches = len(PARENT_PATTERN.findall(text))
        screened.append(
            {
                **row,
                "spin_term_count": spin_matches,
                "distribution_term_count": distribution_matches,
                "parent_term_count": parent_matches,
                "candidate": spin_matches > 0 or (distribution_matches > 0 and parent_matches > 0),
                "snippets": evidence_snippets(text),
                "error": None,
            }
        )
        if number % 25 == 0:
            print(f"Reviewed {number} of {len(rows)} latest Form 10 filings.", flush=True)
            _save(args.output, _payload(args.input, screened, len(rows)))
    payload = _payload(args.input, screened, len(rows))
    _save(args.output, payload)
    print(f"Saved {payload['candidate_count']} text-screen candidates from {len(rows)} registrants.")


if __name__ == "__main__":
    main()

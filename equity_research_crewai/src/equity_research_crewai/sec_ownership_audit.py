"""Audit one issuer's Form 4 and 4/A filings through a stated run date."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

from .sec_form4_audit import _recent_rows, parse_form4
from .sec_spinoff_discovery import SEC_DATA, SecClient, _sec_user_agent_from_env_file


def audit_issuer(
    *,
    cik: str,
    start_date: date,
    through_date: date,
    client: SecClient,
) -> dict[str, Any]:
    """Return filing-level ownership evidence without interpreting missing filings."""

    if through_date < start_date:
        raise ValueError("Through date must be on or after start date.")
    clean_cik = str(cik).zfill(10)
    payload = client.get_json(f"{SEC_DATA}/submissions/CIK{clean_cik}.json")
    forms = [
        row
        for row in _recent_rows(payload)
        if row["form"].upper() in {"4", "4/A"}
        and start_date <= date.fromisoformat(row["filingDate"]) <= through_date
    ]
    reviewed: list[dict[str, Any]] = []
    errors: list[str] = []
    for row in forms:
        accession = row["accessionNumber"]
        accession_compact = accession.replace("-", "")
        primary_document = PurePosixPath(row["primaryDocument"]).name
        url = (
            f"https://www.sec.gov/Archives/edgar/data/{int(clean_cik)}/"
            f"{accession_compact}/{primary_document}"
        )
        try:
            transactions = [dict(item) for item in parse_form4(client.get_text(url))]
        except Exception as exc:  # Preserve the filing and the failed check.
            errors.append(f"{accession}: {type(exc).__name__}: {exc}")
            transactions = []
        reviewed.append(
            {
                "form": row["form"],
                "filing_date": row["filingDate"],
                "accession": accession,
                "url": url,
                "transactions": transactions,
            }
        )
    qualifying = [
        {**transaction, "accession": filing["accession"], "url": filing["url"]}
        for filing in reviewed
        for transaction in filing["transactions"]
        if transaction["transaction_code"] == "P"
        and (transaction["is_director"] or transaction["is_officer"])
    ]
    return {
        "source": "SEC submissions and primary Form 4/4-A transaction tables",
        "cik": clean_cik,
        "start_date": start_date.isoformat(),
        "through_date": through_date.isoformat(),
        "form4_filings_found": len(forms),
        "reviewed_filings": reviewed,
        "officer_or_director_code_p_purchases": qualifying,
        "errors": errors,
        "complete": not errors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit one issuer's Form 4 filings.")
    parser.add_argument("--cik", required=True)
    parser.add_argument("--start", required=True, type=date.fromisoformat)
    parser.add_argument("--through", required=True, type=date.fromisoformat)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    client = SecClient(_sec_user_agent_from_env_file(args.env_file))
    result = audit_issuer(
        cik=args.cik,
        start_date=args.start,
        through_date=args.through,
        client=client,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Reviewed {result['form4_filings_found']} Form 4/4-A filings.")
    print(f"Saved ownership audit to {args.output}.")


if __name__ == "__main__":
    main()

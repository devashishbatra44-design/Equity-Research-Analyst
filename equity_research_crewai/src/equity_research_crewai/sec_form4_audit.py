"""Audit frozen F3 against SEC Form 4 and 4/A transaction tables."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, timedelta
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Mapping

from .sec_spinoff_discovery import SEC_DATA, SecClient, _sec_user_agent_from_env_file


def _value(block: str, tag: str) -> str | None:
    match = re.search(
        rf"<{tag}>\s*(?:<value>)?\s*([^<]+?)\s*(?:</value>)?\s*</{tag}>",
        block,
        re.IGNORECASE,
    )
    return match.group(1).strip() if match else None


def parse_form4(text: str) -> tuple[dict[str, Any], ...]:
    """Return non-derivative transaction facts and reporting-owner roles."""

    relationship = re.search(
        r"<reportingOwnerRelationship>(.*?)</reportingOwnerRelationship>",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    relationship_text = relationship.group(1) if relationship else ""
    is_director = _value(relationship_text, "isDirector") == "1"
    is_officer = _value(relationship_text, "isOfficer") == "1"
    transactions: list[dict[str, Any]] = []
    for match in re.finditer(
        r"<nonDerivativeTransaction>(.*?)</nonDerivativeTransaction>",
        text,
        re.IGNORECASE | re.DOTALL,
    ):
        block = match.group(1)
        transaction_date = _value(block, "transactionDate")
        code = _value(block, "transactionCode")
        if transaction_date and code:
            transactions.append(
                {
                    "transaction_date": transaction_date,
                    "transaction_code": code.upper(),
                    "is_director": is_director,
                    "is_officer": is_officer,
                }
            )
    return tuple(transactions)


def _recent_rows(payload: Mapping[str, Any]) -> tuple[dict[str, str], ...]:
    recent = payload.get("filings", {}).get("recent", {})
    keys = ("form", "filingDate", "accessionNumber", "primaryDocument")
    columns = [recent.get(key, []) for key in keys]
    return tuple(dict(zip(keys, values)) for values in zip(*columns))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit F3 from SEC Form 4 transaction tables.")
    parser.add_argument("--registry", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    index_date = date.fromisoformat(registry["index_date"])
    client = SecClient(_sec_user_agent_from_env_file(args.env_file))
    results: list[dict[str, Any]] = []
    for entry in registry["included_distributions"]:
        cik = str(entry["child_cik"]).zfill(10)
        distributed = date.fromisoformat(entry["distribution_date"])
        cutoff = min(distributed + timedelta(days=90), index_date)
        last_filing_date = min(cutoff + timedelta(days=5), index_date)
        payload = client.get_json(f"{SEC_DATA}/submissions/CIK{cik}.json")
        forms = [
            row
            for row in _recent_rows(payload)
            if row["form"].upper() in {"4", "4/A"}
            and distributed <= date.fromisoformat(row["filingDate"]) <= last_filing_date
        ]
        reviewed: list[str] = []
        transactions: list[dict[str, Any]] = []
        errors: list[str] = []
        for row in forms:
            accession_compact = row["accessionNumber"].replace("-", "")
            raw_primary_document = PurePosixPath(row["primaryDocument"]).name
            url = (
                f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/"
                f"{accession_compact}/{raw_primary_document}"
            )
            try:
                parsed = parse_form4(client.get_text(url))
            except Exception as exc:
                errors.append(f"{row['accessionNumber']}: {type(exc).__name__}")
                continue
            reviewed.append(row["accessionNumber"])
            transactions.extend({**item, "accession": row["accessionNumber"], "url": url} for item in parsed)
        qualifying = [
            item
            for item in transactions
            if distributed < date.fromisoformat(item["transaction_date"]) <= cutoff
            and item["transaction_code"] == "P"
            and (item["is_director"] or item["is_officer"])
        ]
        results.append(
            {
                "child": entry["child"],
                "child_cik": cik,
                "distribution_date": distributed.isoformat(),
                "cutoff_date": cutoff.isoformat(),
                "form4_filings_found": len(forms),
                "reviewed_accessions": reviewed,
                "transaction_codes": sorted({item["transaction_code"] for item in transactions}),
                "qualifying_purchases": qualifying,
                "f3": None if errors else bool(qualifying),
                "errors": errors,
            }
        )
        print(f"Reviewed F3 for {entry['child']}: {len(forms)} Form 4/4-A filings.", flush=True)
    output = {
        "source": "SEC submissions and primary Form 4/4-A transaction tables",
        "index_date": index_date.isoformat(),
        "rule": "code P by an officer or director after distribution through the earlier of 90 days or index date",
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(results)} F3 audits to {args.output}.")


if __name__ == "__main__":
    main()

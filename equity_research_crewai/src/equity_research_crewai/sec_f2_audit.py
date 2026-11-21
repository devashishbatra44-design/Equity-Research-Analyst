"""Validate filing-based evidence for the frozen Week 4 F2 rule."""

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping

from .spinoff_seeker import no_debt_funded_cash_payment


def _decimal(value: object | None) -> Decimal | None:
    if value is None:
        return None
    amount = Decimal(str(value))
    if amount < 0:
        raise ValueError("A debt-funded parent payment must not be negative.")
    return amount


def classify_f2(row: Mapping[str, Any]) -> bool | None:
    """Classify exact, bounded, zero, or missing filing evidence."""

    exact = _decimal(row.get("payment_amount_usd"))
    minimum = _decimal(row.get("payment_minimum_usd"))
    maximum = _decimal(row.get("payment_maximum_usd"))
    populated = sum(value is not None for value in (exact, minimum, maximum))
    if exact is not None and (minimum is not None or maximum is not None):
        raise ValueError("Use either an exact amount or a range, not both.")
    if (minimum is None) != (maximum is None):
        raise ValueError("A payment range requires both minimum and maximum amounts.")
    if minimum is not None and maximum is not None:
        if minimum > maximum:
            raise ValueError("The payment minimum must not exceed the maximum.")
        if minimum == Decimal("0") and maximum > Decimal("0"):
            return None
        return no_debt_funded_cash_payment(minimum)
    if populated == 0:
        return None
    return no_debt_funded_cash_payment(exact)


def validate_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Validate row identity, SEC citations, amounts, and computed results."""

    rows = payload.get("results")
    if not isinstance(rows, list) or not rows:
        raise ValueError("F2 evidence requires a non-empty results list.")
    seen: set[str] = set()
    output_rows: list[dict[str, Any]] = []
    for raw in rows:
        if not isinstance(raw, Mapping):
            raise ValueError("Each F2 result must be a JSON object.")
        row = dict(raw)
        child = str(row.get("child", "")).strip()
        if not child or child in seen:
            raise ValueError(f"Missing or duplicate child name: {child!r}")
        seen.add(child)
        for key in ("child_cik", "parent", "parent_cik", "distribution_date", "currency", "filing_fact"):
            if not str(row.get(key, "")).strip():
                raise ValueError(f"{child} is missing {key}.")
        if row["currency"] != "USD":
            raise ValueError(f"{child} must state the payment currency as USD.")
        sources = row.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ValueError(f"{child} requires at least one SEC source.")
        for source in sources:
            if not isinstance(source, Mapping):
                raise ValueError(f"{child} has an invalid source object.")
            if not str(source.get("url", "")).startswith("https://www.sec.gov/Archives/"):
                raise ValueError(f"{child} source must be an SEC Archives URL.")
            if not str(source.get("section", "")).strip():
                raise ValueError(f"{child} source requires a filing section.")
        row["f2"] = classify_f2(row)
        output_rows.append(row)
    counts = {
        "true": sum(row["f2"] is True for row in output_rows),
        "false": sum(row["f2"] is False for row in output_rows),
        "missing": sum(row["f2"] is None for row in output_rows),
    }
    return {
        "source": "SEC primary filings; filing-stated separation financing",
        "rule": "true only when the filing evidence supports no debt-funded cash payment from child to parent",
        "counts": counts,
        "results": output_rows,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate filing-based F2 evidence.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = validate_evidence(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(result['results'])} F2 audits to {args.output}.")


if __name__ == "__main__":
    main()

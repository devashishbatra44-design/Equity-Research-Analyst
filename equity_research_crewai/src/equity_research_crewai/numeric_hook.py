"""Deterministic numeric claim verifier for saved Week 4 worksheets.

This module is intentionally not enabled as an agent hook. The student must
review it before any Stop-hook configuration is added.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence


REFUSAL = "REFUSE: saved worksheet numeric verification failed"
IGNORED_KINDS = {"date", "accession", "line_number"}
ALLOWED_KINDS = {"filing_fact", "arithmetic", "human_rate", "human_weight", "licensed_price"}


@dataclass(frozen=True)
class Verification:
    ok: bool
    errors: tuple[str, ...]


def decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Invalid decimal: {value!r}") from exc


def verify_claim(claim: Mapping[str, Any]) -> list[str]:
    claim_id = str(claim.get("id", "unnamed"))
    kind = str(claim.get("kind", ""))
    if kind in IGNORED_KINDS:
        return []
    if kind not in ALLOWED_KINDS:
        return [f"{claim_id}: unknown numeric kind {kind!r}"]
    required = {"value", "unit", "period", "source"}
    missing = sorted(field for field in required if claim.get(field) in (None, ""))
    errors = [f"{claim_id}: missing {field}" for field in missing]
    if kind == "filing_fact":
        for field in ("tag", "filing", "accession", "section", "saved_line", "source_file", "source_line"):
            if claim.get(field) in (None, ""):
                errors.append(f"{claim_id}: missing {field}")
    elif kind == "arithmetic":
        inputs = claim.get("inputs")
        operation = claim.get("operation")
        if not isinstance(inputs, Sequence) or isinstance(inputs, (str, bytes)):
            errors.append(f"{claim_id}: inputs must be a list")
        else:
            numbers = [decimal(value) for value in inputs]
            expected: Decimal | None = None
            if operation == "sum":
                expected = sum(numbers, Decimal("0"))
            elif operation == "a_plus_b_minus_c" and len(numbers) == 3:
                expected = numbers[0] + numbers[1] - numbers[2]
            elif operation == "divide" and len(numbers) == 2 and numbers[1] != 0:
                expected = numbers[0] / numbers[1]
            else:
                errors.append(f"{claim_id}: unsupported arithmetic operation or inputs")
            if expected is not None and decimal(claim.get("value")) != expected:
                errors.append(f"{claim_id}: printed arithmetic does not recompute")
    elif kind in {"human_rate", "human_weight"}:
        for field in ("config_file", "config_key"):
            if claim.get(field) in (None, ""):
                errors.append(f"{claim_id}: missing {field}")
        if decimal(claim.get("value")) != decimal(claim.get("frozen_value")):
            errors.append(f"{claim_id}: value differs from frozen human configuration")
    elif kind == "licensed_price":
        for field in ("instrument", "price_date", "reader_source", "reader_file"):
            if claim.get(field) in (None, ""):
                errors.append(f"{claim_id}: missing {field}")
    return errors


def verify_document(document: Mapping[str, Any]) -> Verification:
    claims = document.get("numeric_claims")
    if not isinstance(claims, list):
        return Verification(False, ("numeric_claims must be a list",))
    errors = [error for claim in claims for error in verify_claim(claim)]
    return Verification(not errors, tuple(errors))


def _within(base: Path, relative: str) -> Path:
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError(f"Referenced file leaves the worksheet folder: {relative}")
    return path


def _line(path: Path, number: int) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if number < 1 or number > len(lines):
        raise ValueError(f"Line {number} does not exist in {path.name}.")
    return lines[number - 1]


def _token_in_line(token: str, line: str) -> bool:
    return token.replace(",", "") in line.replace(",", "")


def _external_errors(document: Mapping[str, Any], base: Path) -> list[str]:
    claims = document.get("numeric_claims", [])
    errors: list[str] = []
    worksheet_name = document.get("worksheet_file")
    worksheet_lines: list[str] = []
    if worksheet_name:
        worksheet_path = _within(base, str(worksheet_name))
        worksheet_lines = worksheet_path.read_text(encoding="utf-8", errors="replace").splitlines()

    covered: set[tuple[int, str]] = set()
    for claim in claims:
        claim_id = str(claim.get("id", "unnamed"))
        token = str(claim.get("token", ""))
        worksheet_line = claim.get("worksheet_line")
        if worksheet_lines:
            if not isinstance(worksheet_line, int) or not token:
                errors.append(f"{claim_id}: worksheet_line and token are required")
            elif worksheet_line < 1 or worksheet_line > len(worksheet_lines):
                errors.append(f"{claim_id}: worksheet line does not exist")
            elif not _token_in_line(token, worksheet_lines[worksheet_line - 1]):
                errors.append(f"{claim_id}: token is absent from the saved worksheet line")
            else:
                covered.add((worksheet_line, token.replace(",", "")))

        kind = str(claim.get("kind", ""))
        if kind == "filing_fact" and claim.get("source_file") and claim.get("source_line"):
            try:
                source_line = _line(_within(base, str(claim["source_file"])), int(claim["source_line"]))
                if token and not _token_in_line(token, source_line):
                    errors.append(f"{claim_id}: value is absent from the cited saved filing line")
            except (OSError, ValueError) as exc:
                errors.append(f"{claim_id}: {exc}")
        elif kind in {"human_rate", "human_weight"} and claim.get("config_file"):
            try:
                config = json.loads(_within(base, str(claim["config_file"])).read_text(encoding="utf-8"))
                frozen = config[str(claim.get("config_key", ""))]
                if decimal(claim.get("value")) != decimal(frozen):
                    errors.append(f"{claim_id}: value differs from the external frozen human configuration")
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                errors.append(f"{claim_id}: invalid frozen configuration: {exc}")
        elif kind == "licensed_price" and claim.get("reader_file"):
            try:
                reader = json.loads(_within(base, str(claim["reader_file"])).read_text(encoding="utf-8"))
                matches = [
                    record
                    for record in reader.get("records", [])
                    if str(record.get("instrument", "")).upper() == str(claim.get("instrument", "")).upper()
                    and record.get("pricing_date") == claim.get("price_date")
                    and decimal(record.get("close")) == decimal(claim.get("value"))
                ]
                if not matches:
                    errors.append(f"{claim_id}: price does not match the saved closes-reader record")
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"{claim_id}: invalid closes-reader record: {exc}")

    if worksheet_lines:
        token_pattern = re.compile(
            r"\d{10}-\d{2}-\d{6}|\d{4}-\d{2}-\d{2}|(?<![A-Za-z])[-+]?\d[\d,]*(?:\.\d+)?%?(?![A-Za-z])"
        )
        for number, line in enumerate(worksheet_lines, start=1):
            for match in token_pattern.finditer(line):
                token = match.group(0).replace(",", "")
                if (number, token) not in covered:
                    errors.append(f"worksheet line {number}: unclassified numeric token {match.group(0)!r}")
    return errors


def verify_file(path: Path) -> Verification:
    with path.open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    core = verify_document(document)
    external = _external_errors(document, path.resolve().parent)
    errors = core.errors + tuple(external)
    return Verification(not errors, errors)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: numeric_hook SAVED_WORKSHEET.json")
    result = verify_file(Path(sys.argv[1]))
    if result.ok:
        return
    print(REFUSAL)
    for error in result.errors:
        print(f"- {error}")
    raise SystemExit(2)


if __name__ == "__main__":
    main()

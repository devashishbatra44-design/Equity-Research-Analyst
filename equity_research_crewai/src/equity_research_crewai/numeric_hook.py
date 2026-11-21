"""Deterministic numeric claim verifier for saved Week 4 worksheets.

The student reviewed this module before the project-local Stop hook was enabled.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping, Sequence


REFUSAL = "REFUSE: saved worksheet numeric verification failed"
IGNORED_KINDS = {"date", "accession", "line_number"}
ALLOWED_KINDS = {
    "filing_fact",
    "arithmetic",
    "human_rate",
    "human_weight",
    "licensed_price",
    "official_exchange_price",
    "market_metric",
    "analytical_score",
}


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
            elif operation == "identity" and len(numbers) == 1:
                expected = numbers[0]
            elif operation == "a_plus_b_minus_c" and len(numbers) == 3:
                expected = numbers[0] + numbers[1] - numbers[2]
            elif operation == "divide" and len(numbers) == 2 and numbers[1] != 0:
                expected = numbers[0] / numbers[1]
            elif operation == "multiply" and len(numbers) == 2:
                expected = numbers[0] * numbers[1]
            elif operation == "multiply_one_minus" and len(numbers) == 2:
                expected = numbers[0] * (Decimal("1") - numbers[1])
            elif operation == "multiply_divide" and len(numbers) == 3 and numbers[2] != 0:
                expected = numbers[0] * numbers[1] / numbers[2]
            elif operation == "percentage" and len(numbers) == 2 and numbers[1] != 0:
                expected = numbers[0] / numbers[1] * Decimal("100")
            elif operation == "absolute_difference" and len(numbers) == 2:
                expected = abs(numbers[0] - numbers[1])
            else:
                errors.append(f"{claim_id}: unsupported arithmetic operation or inputs")
            round_places = claim.get("round_places")
            if expected is not None and round_places is not None:
                places = int(round_places)
                expected = expected.quantize(Decimal("1").scaleb(-places), rounding=ROUND_HALF_UP)
            if expected is not None and decimal(claim.get("value")) != expected:
                errors.append(f"{claim_id}: printed arithmetic does not recompute")
    elif kind in {"human_rate", "human_weight"}:
        for field in ("config_file", "config_key"):
            if claim.get(field) in (None, ""):
                errors.append(f"{claim_id}: missing {field}")
        if decimal(claim.get("value")) != decimal(claim.get("frozen_value")):
            errors.append(f"{claim_id}: value differs from frozen human configuration")
    elif kind in {"licensed_price", "official_exchange_price"}:
        for field in ("instrument", "price_date", "reader_source", "reader_file"):
            if claim.get(field) in (None, ""):
                errors.append(f"{claim_id}: missing {field}")
    elif kind == "market_metric":
        for field in ("instrument", "metric", "reader_source", "reader_file"):
            if claim.get(field) in (None, ""):
                errors.append(f"{claim_id}: missing {field}")
    elif kind == "analytical_score":
        for field in (
            "criterion",
            "persona_file",
            "scale_min",
            "scale_max",
            "evidence_claim_ids",
            "used_in_composite",
        ):
            if claim.get(field) in (None, ""):
                errors.append(f"{claim_id}: missing {field}")
        try:
            score = decimal(claim.get("value"))
            scale_min = decimal(claim.get("scale_min"))
            scale_max = decimal(claim.get("scale_max"))
            if scale_min != Decimal("1") or scale_max != Decimal("5"):
                errors.append(f"{claim_id}: analytical score scale must be 1 through 5")
            if score != score.to_integral_value() or score < scale_min or score > scale_max:
                errors.append(f"{claim_id}: analytical score must be an integer from 1 through 5")
        except ValueError as exc:
            errors.append(f"{claim_id}: {exc}")
        evidence_claim_ids = claim.get("evidence_claim_ids")
        if not isinstance(evidence_claim_ids, list) or not evidence_claim_ids or not all(
            isinstance(item, str) and item.strip() for item in evidence_claim_ids
        ):
            errors.append(f"{claim_id}: evidence_claim_ids must be a nonempty list of claim IDs")
        if claim.get("used_in_composite") is not False:
            errors.append(f"{claim_id}: analytical score must not be used in a composite")
    return errors


def verify_document(document: Mapping[str, Any]) -> Verification:
    claims = document.get("numeric_claims")
    if not isinstance(claims, list):
        return Verification(False, ("numeric_claims must be a list",))
    errors = [error for claim in claims for error in verify_claim(claim)]
    claims_by_id = {str(claim.get("id", "unnamed")): claim for claim in claims}
    for claim in claims:
        if str(claim.get("kind", "")) != "analytical_score":
            continue
        claim_id = str(claim.get("id", "unnamed"))
        evidence_claim_ids = claim.get("evidence_claim_ids")
        if not isinstance(evidence_claim_ids, list):
            continue
        for evidence_id in evidence_claim_ids:
            evidence = claims_by_id.get(str(evidence_id))
            if evidence is None:
                errors.append(f"{claim_id}: evidence claim {evidence_id!r} does not exist")
            elif str(evidence.get("kind", "")) in IGNORED_KINDS | {"analytical_score"}:
                errors.append(f"{claim_id}: evidence claim {evidence_id!r} is not source evidence")
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
        elif kind in {"licensed_price", "official_exchange_price"} and claim.get("reader_file"):
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
        elif kind == "market_metric" and claim.get("reader_file"):
            try:
                reader = json.loads(_within(base, str(claim["reader_file"])).read_text(encoding="utf-8"))
                records = [
                    record
                    for record in reader.get("records", [])
                    if str(record.get("instrument", "")).upper() == str(claim.get("instrument", "")).upper()
                ]
                metric = str(claim.get("metric", ""))
                expected: Decimal | None = None
                if metric == "observation_count":
                    expected = Decimal(len(records))
                elif metric == "median_daily_dollar_volume":
                    values = sorted(decimal(record["close"]) * decimal(record["volume"]) for record in records)
                    if values:
                        middle = len(values) // 2
                        expected = (
                            values[middle]
                            if len(values) % 2
                            else (values[middle - 1] + values[middle]) / Decimal("2")
                        )
                if expected is None:
                    errors.append(f"{claim_id}: unsupported or empty market metric")
                elif decimal(claim.get("value")) != expected:
                    errors.append(f"{claim_id}: market metric does not match the saved reader records")
            except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                errors.append(f"{claim_id}: invalid market-reader record: {exc}")
        elif kind == "analytical_score" and claim.get("persona_file"):
            try:
                persona_text = _within(base, str(claim["persona_file"])).read_text(
                    encoding="utf-8", errors="replace"
                )
                criterion = str(claim.get("criterion", "")).strip()
                if not criterion or criterion.casefold() not in persona_text.casefold():
                    errors.append(f"{claim_id}: criterion is absent from the frozen persona")
            except (OSError, ValueError) as exc:
                errors.append(f"{claim_id}: invalid frozen persona: {exc}")

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
